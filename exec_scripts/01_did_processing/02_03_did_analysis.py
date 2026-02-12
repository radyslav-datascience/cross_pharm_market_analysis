# =============================================================================
# 02_03_DID_ANALYSIS - cross_pharm_market_analysis
# =============================================================================
# Файл: exec_scripts/01_did_processing/02_03_did_analysis.py
# Дата: 2026-01-28
# Опис: Difference-in-Differences аналіз per market (Phase 1, Step 3)
# =============================================================================
"""
Скрипт DiD аналізу для мульти-ринкового дослідження субституції.

Функціонал:
    1. Завантаження stock-out подій з етапу 02
    2. Визначення POST-періоду для кожної події
    3. Ідентифікація валідних substitutes (NFC filter + Phantom filter)
    4. Розрахунок MARKET_GROWTH, LIFT, SHARE_INTERNAL, SHARE_LOST
    5. NFC декомпозиція (SAME_NFC1 vs DIFF_NFC1)
    6. Класифікація препаратів (CRITICAL / SUBSTITUTABLE / MODERATE)
    7. Генерація статистики per INN та per DRUGS

Вхід:
    data/processed_data/01_per_market/{CLIENT_ID}/02_stockout_{CLIENT_ID}/
    └── stockout_events_{CLIENT_ID}.csv

    data/processed_data/01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
    └── inn_{INN_ID}_{CLIENT_ID}.csv

Вихід:
    data/processed_data/01_per_market/{CLIENT_ID}/03_did_analysis_{CLIENT_ID}/
    ├── did_results_{CLIENT_ID}.csv           # DiD результати per event
    ├── substitute_mapping_{CLIENT_ID}.csv    # Mapping target -> substitutes
    └── _stats/
        ├── did_summary_{CLIENT_ID}.csv       # Per INN статистика
        ├── drugs_summary_{CLIENT_ID}.csv     # Per DRUGS + класифікація
        └── did_metadata_{CLIENT_ID}.csv      # Параметри та метадані

Використання:
    # Обробка одного ринку:
    python exec_scripts/01_did_processing/02_03_did_analysis.py --market_id 28670

    # Обробка всіх ринків:
    python exec_scripts/01_did_processing/02_03_did_analysis.py --all
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np

# Додаємо project root до sys.path для імпортів
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Імпорти з project_core
from project_core.data_config.paths_config import (
    PROCESSED_DATA_PATH,
    load_target_pharmacies
)
from project_core.did_config.stockout_params import (
    MIN_POST_PERIOD_WEEKS,
    MAX_POST_GAP_WEEKS,
    MIN_MARKET_PRE,
    MIN_TOTAL_FOR_SHARE
)
from project_core.did_config.nfc_compatibility import (
    is_compatible,
    get_compatibility_group
)
from project_core.did_config.classification_thresholds import (
    CRITICAL_THRESHOLD,
    SUBSTITUTABLE_THRESHOLD,
    classify_drug
)
from project_core.utility_functions.did_utils import (
    define_post_period,
    calculate_market_growth,
    calculate_expected,
    calculate_lift,
    calculate_shares,
    nfc_decomposition,
    validate_did_invariants
)


# =============================================================================
# CONSTANTS
# =============================================================================

PER_MARKET_FOLDER = "01_per_market"


# =============================================================================
# PATH FUNCTIONS
# =============================================================================

def get_did_paths(client_id: int) -> Dict[str, Path]:
    """
    Отримати шляхи для DiD analysis етапу.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict з шляхами
    """
    market_folder = PROCESSED_DATA_PATH / PER_MARKET_FOLDER / str(client_id)
    did_folder = market_folder / f"03_did_analysis_{client_id}"
    stats_folder = did_folder / "_stats"
    stockout_folder = market_folder / f"02_stockout_{client_id}"
    aggregation_folder = market_folder / f"01_aggregation_{client_id}"

    return {
        'market_folder': market_folder,
        'aggregation_folder': aggregation_folder,
        'stockout_folder': stockout_folder,
        'did_folder': did_folder,
        'stats_folder': stats_folder
    }


def ensure_did_folders(client_id: int) -> Dict[str, Path]:
    """
    Створити необхідні папки для DiD analysis.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict з шляхами (папки створені)
    """
    paths = get_did_paths(client_id)

    for key in ['did_folder', 'stats_folder']:
        paths[key].mkdir(parents=True, exist_ok=True)

    return paths


# =============================================================================
# DATA LOADING
# =============================================================================

def load_stockout_events(client_id: int, paths: Dict[str, Path]) -> pd.DataFrame:
    """
    Завантажити stock-out події з етапу 02.

    Args:
        client_id: ID цільової аптеки
        paths: Словник шляхів

    Returns:
        pd.DataFrame: Stock-out події
    """
    events_file = paths['stockout_folder'] / f"stockout_events_{client_id}.csv"

    if not events_file.exists():
        raise FileNotFoundError(
            f"Stock-out файл не знайдено: {events_file}\n"
            f"Спочатку виконайте: python exec_scripts/01_did_processing/02_02_stockout_detection.py --market_id {client_id}"
        )

    df = pd.read_csv(events_file, parse_dates=['STOCKOUT_START', 'STOCKOUT_END', 'PRE_START', 'PRE_END'])
    return df


def load_inn_data(inn_id: int, client_id: int, paths: Dict[str, Path]) -> pd.DataFrame:
    """
    Завантажити агреговані дані для INN групи.

    Args:
        inn_id: ID INN групи
        client_id: ID цільової аптеки
        paths: Словник шляхів

    Returns:
        pd.DataFrame: Агреговані дані INN групи
    """
    inn_file = paths['aggregation_folder'] / f"inn_{inn_id}_{client_id}.csv"

    if not inn_file.exists():
        return pd.DataFrame()

    df = pd.read_csv(inn_file, parse_dates=['Date'])
    return df


# =============================================================================
# POST-PERIOD DEFINITION
# =============================================================================

def process_event_post_period(
    event: pd.Series,
    df_inn: pd.DataFrame,
    client_id: int,
    min_post_weeks: int = MIN_POST_PERIOD_WEEKS,
    max_gap_weeks: int = MAX_POST_GAP_WEEKS
) -> Dict[str, Any]:
    """
    Визначити POST-період для stock-out події.

    Args:
        event: Рядок з інформацією про подію
        df_inn: Агреговані дані INN групи
        client_id: ID цільової аптеки
        min_post_weeks: Мінімальна тривалість POST-періоду
        max_gap_weeks: Максимальний gap до відновлення

    Returns:
        Dict з POST-періодом та статусом
    """
    drug_id = event['DRUGS_ID']
    stockout_end = event['STOCKOUT_END']

    # Фільтруємо дані тільки TARGET аптеки
    df_target = df_inn[df_inn['PHARM_ID'] == client_id]
    df_drug = df_target[df_target['DRUGS_ID'] == drug_id]

    if len(df_drug) == 0:
        return {
            'POST_START': None,
            'POST_END': None,
            'POST_WEEKS': 0,
            'POST_STATUS': 'no_data',
            'POST_VALID': False
        }

    # Визначаємо POST-період
    post_start, post_end, post_weeks, status = define_post_period(
        df_drug=df_drug,
        stockout_end=stockout_end,
        min_post_weeks=min_post_weeks,
        max_gap_weeks=max_gap_weeks
    )

    is_valid = status == 'valid'

    return {
        'POST_START': post_start,
        'POST_END': post_end,
        'POST_WEEKS': post_weeks,
        'POST_STATUS': status,
        'POST_VALID': is_valid
    }


# =============================================================================
# SUBSTITUTE IDENTIFICATION
# =============================================================================

def find_valid_substitutes(
    event: pd.Series,
    df_inn: pd.DataFrame,
    client_id: int,
    drug_index: Optional[Dict[int, pd.DataFrame]] = None
) -> List[Dict[str, Any]]:
    """
    Знайти валідні substitutes для stock-out події.

    Фільтри:
    1. NFC Compatibility: форма випуску повинна бути сумісною
    2. Phantom Filter: substitute повинен мати дані під час stock-out

    Args:
        event: Інформація про подію
        df_inn: Агреговані дані INN групи
        client_id: ID цільової аптеки
        drug_index: Попередньо побудований індекс {DRUGS_ID: DataFrame}
                    для TARGET аптеки (опціонально, для оптимізації)

    Returns:
        List[Dict]: Список валідних substitutes
    """
    target_drug_id = event['DRUGS_ID']
    target_nfc1 = event['NFC1_ID']
    stockout_start = event['STOCKOUT_START']
    stockout_end = event['STOCKOUT_END']

    # Побудова індексу якщо не передано
    if drug_index is None:
        df_target = df_inn[df_inn['PHARM_ID'] == client_id]
        drug_index = {did: grp for did, grp in df_target.groupby('DRUGS_ID')}

    valid_substitutes = []

    for drug_id, df_sub in drug_index.items():
        if drug_id == target_drug_id:
            continue

        if len(df_sub) == 0:
            continue

        sub_nfc1 = df_sub['NFC1_ID'].iloc[0]
        sub_name = df_sub['DRUGS_NAME'].iloc[0]

        # ФІЛЬТР 1: NFC Compatibility
        if not is_compatible(target_nfc1, sub_nfc1):
            continue

        # ФІЛЬТР 2: Phantom Filter - повинні бути дані під час stock-out
        df_during = df_sub[
            (df_sub['Date'] >= stockout_start) &
            (df_sub['Date'] <= stockout_end)
        ]

        if len(df_during) == 0:
            continue

        # Substitute валідний
        valid_substitutes.append({
            'SUBSTITUTE_DRUGS_ID': drug_id,
            'SUBSTITUTE_DRUGS_NAME': sub_name,
            'SUBSTITUTE_NFC1_ID': sub_nfc1,
            'SAME_NFC1': target_nfc1 == sub_nfc1,
            'NFC_GROUP': get_compatibility_group(target_nfc1)
        })

    return valid_substitutes


# =============================================================================
# DiD CALCULATIONS
# =============================================================================

def calculate_did_for_event(
    event: pd.Series,
    df_inn: pd.DataFrame,
    client_id: int,
    valid_substitutes: List[Dict],
    drug_index: Optional[Dict[int, pd.DataFrame]] = None
) -> Dict[str, Any]:
    """
    Розрахувати DiD метрики для однієї stock-out події.

    Args:
        event: Інформація про подію (включаючи POST період)
        df_inn: Агреговані дані INN групи
        client_id: ID цільової аптеки
        valid_substitutes: Список валідних substitutes
        drug_index: Попередньо побудований індекс {DRUGS_ID: DataFrame}
                    для TARGET аптеки (опціонально, для оптимізації)

    Returns:
        Dict з DiD результатами
    """
    target_drug_id = event['DRUGS_ID']
    target_nfc1 = event['NFC1_ID']

    pre_start = event['PRE_START']
    pre_end = event['PRE_END']
    stockout_start = event['STOCKOUT_START']
    stockout_end = event['STOCKOUT_END']

    # Побудова індексу якщо не передано
    if drug_index is None:
        df_target = df_inn[df_inn['PHARM_ID'] == client_id]
        drug_index = {did: grp for did, grp in df_target.groupby('DRUGS_ID')}

    # === 1. MARKET_GROWTH ===
    # Ринкові продажі в PRE-періоді (весь ринок, не тільки TARGET)
    df_market_pre = df_inn[
        (df_inn['Date'] >= pre_start) &
        (df_inn['Date'] <= pre_end)
    ]
    market_pre = df_market_pre['MARKET_TOTAL_DRUGS_PACK'].sum()

    # Ринкові продажі під час stock-out (весь ринок)
    df_market_during = df_inn[
        (df_inn['Date'] >= stockout_start) &
        (df_inn['Date'] <= stockout_end)
    ]
    market_during = df_market_during['MARKET_TOTAL_DRUGS_PACK'].sum()

    market_growth = calculate_market_growth(market_pre, market_during, MIN_MARKET_PRE)

    # === 2. INTERNAL_LIFT (substitutes в TARGET аптеці) ===
    substitutes_lifts = []

    for sub in valid_substitutes:
        sub_drug_id = sub['SUBSTITUTE_DRUGS_ID']
        sub_nfc1 = sub['SUBSTITUTE_NFC1_ID']

        # Використовуємо pre-indexed lookup замість фільтрації
        df_sub = drug_index.get(sub_drug_id)
        if df_sub is None or len(df_sub) == 0:
            continue

        # Продажі substitute в PRE-періоді
        df_sub_pre = df_sub[
            (df_sub['Date'] >= pre_start) &
            (df_sub['Date'] <= pre_end)
        ]
        sales_pre = df_sub_pre['Q'].sum()

        # Продажі substitute під час stock-out
        df_sub_during = df_sub[
            (df_sub['Date'] >= stockout_start) &
            (df_sub['Date'] <= stockout_end)
        ]
        sales_during = df_sub_during['Q'].sum()

        # Очікувані та LIFT
        expected = calculate_expected(sales_pre, market_growth)
        lift = calculate_lift(sales_during, expected)

        substitutes_lifts.append({
            'drug_id': sub_drug_id,
            'nfc1_id': sub_nfc1,
            'sales_pre': sales_pre,
            'sales_during': sales_during,
            'expected': expected,
            'lift': lift
        })

    internal_lift = sum(s['lift'] for s in substitutes_lifts)
    substitutes_with_lift = sum(1 for s in substitutes_lifts if s['lift'] > 0)

    # === 3. LOST_SALES (target препарат у конкурентів) ===
    # Використовуємо pre-indexed lookup
    df_target_drug = drug_index.get(target_drug_id)

    if df_target_drug is not None and len(df_target_drug) > 0:
        # В PRE-періоді
        df_drug_pre = df_target_drug[
            (df_target_drug['Date'] >= pre_start) &
            (df_target_drug['Date'] <= pre_end)
        ]
        if len(df_drug_pre) > 0 and 'MARKET_TOTAL_DRUGS_PACK' in df_drug_pre.columns:
            market_total_pre = df_drug_pre['MARKET_TOTAL_DRUGS_PACK'].sum()
            target_pre = df_drug_pre['Q'].sum()
            comp_pre = max(0, market_total_pre - target_pre)
        else:
            comp_pre = 0

        # Під час stock-out
        df_drug_during = df_target_drug[
            (df_target_drug['Date'] >= stockout_start) &
            (df_target_drug['Date'] <= stockout_end)
        ]
        if len(df_drug_during) > 0 and 'MARKET_TOTAL_DRUGS_PACK' in df_drug_during.columns:
            comp_during = df_drug_during['MARKET_TOTAL_DRUGS_PACK'].sum()
        else:
            comp_during = 0
    else:
        comp_pre = 0
        comp_during = 0

    # LIFT конкурентів
    comp_expected = calculate_expected(comp_pre, market_growth)
    lost_sales = calculate_lift(comp_during, comp_expected)

    # === 4. SHARE CALCULATIONS ===
    total_effect = internal_lift + lost_sales
    share_internal, share_lost = calculate_shares(internal_lift, lost_sales, MIN_TOTAL_FOR_SHARE)

    # === 5. NFC DECOMPOSITION ===
    nfc_result = nfc_decomposition(substitutes_lifts, target_nfc1)

    # Збираємо результат
    result = {
        'MARKET_PRE': round(market_pre, 2),
        'MARKET_DURING': round(market_during, 2),
        'MARKET_GROWTH': round(market_growth, 6),
        'INTERNAL_LIFT': round(internal_lift, 4),
        'LOST_SALES': round(lost_sales, 4),
        'TOTAL_EFFECT': round(total_effect, 4),
        'SHARE_INTERNAL': round(share_internal, 6) if not np.isnan(share_internal) else np.nan,
        'SHARE_LOST': round(share_lost, 6) if not np.isnan(share_lost) else np.nan,
        'SUBSTITUTES_COUNT': len(valid_substitutes),
        'SUBSTITUTES_WITH_LIFT': substitutes_with_lift,
        'LIFT_SAME_NFC1': round(nfc_result['lift_same_nfc1'], 4),
        'LIFT_DIFF_NFC1': round(nfc_result['lift_diff_nfc1'], 4),
        'SHARE_SAME_NFC1': round(nfc_result['share_same_nfc1'], 6) if not np.isnan(nfc_result['share_same_nfc1']) else np.nan,
        'SHARE_DIFF_NFC1': round(nfc_result['share_diff_nfc1'], 6) if not np.isnan(nfc_result['share_diff_nfc1']) else np.nan
    }

    return result


# =============================================================================
# INN-GROUP PROCESSING (для ThreadPoolExecutor)
# =============================================================================

def _process_inn_group_did(
    inn_id: int,
    inn_events: pd.DataFrame,
    client_id: int,
    paths: Dict[str, Path]
) -> Dict[str, Any]:
    """
    Обробка однієї INN-групи для DiD аналізу.

    Ця функція виконується в окремому потоці (ThreadPoolExecutor).
    Не має shared state — повертає локальні результати для merge.

    Формули розрахунків НЕ змінені — викликаються ті самі
    find_valid_substitutes(), calculate_did_for_event() та ін.

    Args:
        inn_id: ID INN групи
        inn_events: DataFrame подій для цієї INN
        client_id: ID цільової аптеки
        paths: Словник шляхів

    Returns:
        Dict з ключами:
            - did_results: List[Dict] — DiD результати
            - substitute_mappings: List[Dict] — substitute mapping
            - validation_stats: Dict — статистика валідації
    """
    did_results = []
    substitute_mappings = []
    validation_stats = {
        'valid': 0,
        'no_post_period': 0,
        'no_substitutes': 0,
        'no_effect': 0
    }

    # Завантажуємо дані INN
    df_inn = load_inn_data(inn_id, client_id, paths)

    if df_inn.empty:
        return {
            'did_results': did_results,
            'substitute_mappings': substitute_mappings,
            'validation_stats': validation_stats
        }

    # Pre-index: побудова словника {DRUGS_ID: DataFrame} для TARGET аптеки
    df_target_inn = df_inn[df_inn['PHARM_ID'] == client_id]
    drug_index = {did: grp for did, grp in df_target_inn.groupby('DRUGS_ID')}

    # Обробка кожної події
    for idx, event in inn_events.iterrows():
        event_id = event['EVENT_ID']

        # 1. Визначення POST-періоду
        post_result = process_event_post_period(event, df_inn, client_id)

        if not post_result['POST_VALID']:
            validation_stats['no_post_period'] += 1
            continue

        # Додаємо POST до event
        event_with_post = event.copy()
        event_with_post['POST_START'] = post_result['POST_START']
        event_with_post['POST_END'] = post_result['POST_END']
        event_with_post['POST_WEEKS'] = post_result['POST_WEEKS']
        event_with_post['POST_STATUS'] = post_result['POST_STATUS']
        event_with_post['POST_VALID'] = post_result['POST_VALID']

        # 2. Пошук валідних substitutes (з pre-indexed drug_index)
        valid_substitutes = find_valid_substitutes(
            event_with_post, df_inn, client_id, drug_index=drug_index
        )

        if len(valid_substitutes) == 0:
            validation_stats['no_substitutes'] += 1

        # Зберігаємо substitute mapping
        for sub in valid_substitutes:
            substitute_mappings.append({
                'EVENT_ID': event_id,
                'CLIENT_ID': client_id,
                'INN_ID': inn_id,
                'INN_NAME': event['INN_NAME'],
                'TARGET_DRUGS_ID': event['DRUGS_ID'],
                'TARGET_DRUGS_NAME': event['DRUGS_NAME'],
                'TARGET_NFC1_ID': event['NFC1_ID'],
                **sub
            })

        # 3. DiD розрахунки (з pre-indexed drug_index)
        did_result = calculate_did_for_event(
            event_with_post, df_inn, client_id, valid_substitutes,
            drug_index=drug_index
        )

        # Перевірка чи є ефект
        if did_result['TOTAL_EFFECT'] < MIN_TOTAL_FOR_SHARE:
            validation_stats['no_effect'] += 1
            continue

        validation_stats['valid'] += 1

        # Збираємо повний результат
        full_result = {
            'EVENT_ID': event_id,
            'CLIENT_ID': client_id,
            'INN_ID': inn_id,
            'INN_NAME': event['INN_NAME'],
            'DRUGS_ID': event['DRUGS_ID'],
            'DRUGS_NAME': event['DRUGS_NAME'],
            'NFC1_ID': event['NFC1_ID'],
            'NFC_ID': event['NFC_ID'],
            'STOCKOUT_START': event['STOCKOUT_START'].strftime('%Y-%m-%d'),
            'STOCKOUT_END': event['STOCKOUT_END'].strftime('%Y-%m-%d'),
            'STOCKOUT_WEEKS': event['STOCKOUT_WEEKS'],
            'PRE_START': event['PRE_START'].strftime('%Y-%m-%d'),
            'PRE_END': event['PRE_END'].strftime('%Y-%m-%d'),
            'PRE_WEEKS': event['PRE_WEEKS'],
            'PRE_AVG_Q': event['PRE_AVG_Q'],
            'POST_START': post_result['POST_START'].strftime('%Y-%m-%d'),
            'POST_END': post_result['POST_END'].strftime('%Y-%m-%d'),
            'POST_WEEKS': post_result['POST_WEEKS'],
            'POST_STATUS': post_result['POST_STATUS'],
            **did_result
        }

        did_results.append(full_result)

    return {
        'did_results': did_results,
        'substitute_mappings': substitute_mappings,
        'validation_stats': validation_stats
    }


# =============================================================================
# PROCESS SINGLE MARKET
# =============================================================================

def process_market_did(client_id: int) -> Dict:
    """
    Повна обробка DiD аналізу для одного ринку.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict: Результати обробки
    """
    start_time = datetime.now()

    # Підготовка папок
    paths = ensure_did_folders(client_id)

    print(f"\n{'='*60}")
    print(f"DiD ANALYSIS: CLIENT_ID = {client_id}")
    print(f"{'='*60}")

    # Завантаження stock-out подій
    df_events = load_stockout_events(client_id, paths)

    if df_events.empty:
        print("Немає stock-out подій для аналізу")
        return {
            'client_id': client_id,
            'events_count': 0,
            'valid_events': 0,
            'files_created': []
        }

    print(f"Завантажено {len(df_events)} stock-out подій")

    # Групуємо по INN для оптимізації завантаження
    inn_groups = df_events.groupby('INN_ID')
    inn_group_list = [(inn_id, inn_events) for inn_id, inn_events in inn_groups]

    # Завантажуємо параметр INN-паралелізму
    from project_core.calculation_parameters_config.machine_parameters import OPTIMAL_THREADS
    n_threads = min(OPTIMAL_THREADS, len(inn_group_list))

    # Обробка INN-груп (паралельно якщо n_threads > 1, інакше послідовно)
    if n_threads > 1:
        # === ПАРАЛЕЛЬНА ОБРОБКА INN-ГРУП (ThreadPoolExecutor) ===
        all_did_results = []
        all_substitute_mappings = []
        validation_stats = {
            'valid': 0,
            'no_post_period': 0,
            'no_substitutes': 0,
            'no_effect': 0
        }

        with ThreadPoolExecutor(max_workers=n_threads) as pool:
            futures = {
                pool.submit(
                    _process_inn_group_did, inn_id, inn_events, client_id, paths
                ): inn_id
                for inn_id, inn_events in inn_group_list
            }

            for future in as_completed(futures):
                inn_result = future.result()
                all_did_results.extend(inn_result['did_results'])
                all_substitute_mappings.extend(inn_result['substitute_mappings'])
                for key in validation_stats:
                    validation_stats[key] += inn_result['validation_stats'][key]
    else:
        # === ПОСЛІДОВНА ОБРОБКА (fallback, n_threads == 1) ===
        all_did_results = []
        all_substitute_mappings = []
        validation_stats = {
            'valid': 0,
            'no_post_period': 0,
            'no_substitutes': 0,
            'no_effect': 0
        }

        for inn_id, inn_events in inn_group_list:
            inn_result = _process_inn_group_did(inn_id, inn_events, client_id, paths)
            all_did_results.extend(inn_result['did_results'])
            all_substitute_mappings.extend(inn_result['substitute_mappings'])
            for key in validation_stats:
                validation_stats[key] += inn_result['validation_stats'][key]

    # Збереження результатів
    results = {
        'client_id': client_id,
        'events_count': len(df_events),
        'valid_events': len(all_did_results),
        'validation_stats': validation_stats,
        'files_created': []
    }

    # Зберігаємо DiD результати
    if all_did_results:
        df_did = pd.DataFrame(all_did_results)
        did_file = paths['did_folder'] / f"did_results_{client_id}.csv"
        df_did.to_csv(did_file, index=False)
        results['files_created'].append(str(did_file))

        # Зберігаємо substitute mapping
        if all_substitute_mappings:
            df_subs = pd.DataFrame(all_substitute_mappings)
            subs_file = paths['did_folder'] / f"substitute_mapping_{client_id}.csv"
            df_subs.to_csv(subs_file, index=False)
            results['files_created'].append(str(subs_file))

        # Генеруємо статистику
        generate_did_statistics(df_did, client_id, paths)
        results['files_created'].append(str(paths['stats_folder'] / f"did_summary_{client_id}.csv"))
        results['files_created'].append(str(paths['stats_folder'] / f"drugs_summary_{client_id}.csv"))
        results['files_created'].append(str(paths['stats_folder'] / f"did_metadata_{client_id}.csv"))
    else:
        # Створюємо пусті файли
        empty_columns = [
            'EVENT_ID', 'CLIENT_ID', 'INN_ID', 'INN_NAME', 'DRUGS_ID', 'DRUGS_NAME',
            'NFC1_ID', 'NFC_ID', 'STOCKOUT_START', 'STOCKOUT_END', 'STOCKOUT_WEEKS',
            'PRE_START', 'PRE_END', 'PRE_WEEKS', 'PRE_AVG_Q',
            'POST_START', 'POST_END', 'POST_WEEKS', 'POST_STATUS',
            'MARKET_PRE', 'MARKET_DURING', 'MARKET_GROWTH',
            'INTERNAL_LIFT', 'LOST_SALES', 'TOTAL_EFFECT',
            'SHARE_INTERNAL', 'SHARE_LOST',
            'SUBSTITUTES_COUNT', 'SUBSTITUTES_WITH_LIFT',
            'LIFT_SAME_NFC1', 'LIFT_DIFF_NFC1', 'SHARE_SAME_NFC1', 'SHARE_DIFF_NFC1'
        ]
        empty_df = pd.DataFrame(columns=empty_columns)
        did_file = paths['did_folder'] / f"did_results_{client_id}.csv"
        empty_df.to_csv(did_file, index=False)
        results['files_created'].append(str(did_file))

    # Час виконання
    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_seconds'] = round(elapsed, 2)

    # Вивід результатів
    print(f"\nПараметри:")
    print(f"  MIN_POST_PERIOD_WEEKS: {MIN_POST_PERIOD_WEEKS}")
    print(f"  MAX_POST_GAP_WEEKS: {MAX_POST_GAP_WEEKS}")
    print(f"  CRITICAL_THRESHOLD: {CRITICAL_THRESHOLD:.0%}")
    print(f"  SUBSTITUTABLE_THRESHOLD: {SUBSTITUTABLE_THRESHOLD:.0%}")

    print(f"\nРезультати:")
    print(f"  Stock-out подій: {len(df_events)}")
    print(f"  Валідних DiD подій: {len(all_did_results)}")

    if len(df_events) > 0:
        valid_pct = len(all_did_results) / len(df_events) * 100
        print(f"  Validation rate: {valid_pct:.1f}%")

        print(f"\nПричини відхилення:")
        print(f"  no_post_period: {validation_stats['no_post_period']}")
        print(f"  no_substitutes: {validation_stats['no_substitutes']}")
        print(f"  no_effect: {validation_stats['no_effect']}")

    if all_did_results:
        df_did = pd.DataFrame(all_did_results)
        avg_share_internal = df_did['SHARE_INTERNAL'].dropna().mean()
        avg_share_lost = df_did['SHARE_LOST'].dropna().mean()
        print(f"\nСередні значення:")
        print(f"  AVG SHARE_INTERNAL: {avg_share_internal:.1%}")
        print(f"  AVG SHARE_LOST: {avg_share_lost:.1%}")

    print(f"\nЧас: {elapsed:.1f} сек")

    return results


# =============================================================================
# STATISTICS GENERATION
# =============================================================================

def generate_did_statistics(
    df_did: pd.DataFrame,
    client_id: int,
    paths: Dict[str, Path]
) -> None:
    """
    Генерувати статистику DiD аналізу.

    Args:
        df_did: Результати DiD
        client_id: ID цільової аптеки
        paths: Словник шляхів
    """
    # === 1. Per INN Summary ===
    inn_summary = df_did.groupby(['INN_ID', 'INN_NAME']).agg({
        'EVENT_ID': 'count',
        'DRUGS_ID': 'nunique',
        'SHARE_INTERNAL': 'mean',
        'SHARE_LOST': 'mean',
        'SHARE_SAME_NFC1': 'mean',
        'INTERNAL_LIFT': 'sum',
        'LOST_SALES': 'sum'
    }).reset_index()

    inn_summary.columns = [
        'INN_ID', 'INN_NAME', 'EVENTS', 'DRUGS',
        'AVG_SHARE_INTERNAL', 'AVG_SHARE_LOST', 'AVG_SHARE_SAME_NFC1',
        'TOTAL_INTERNAL_LIFT', 'TOTAL_LOST_SALES'
    ]

    inn_summary_file = paths['stats_folder'] / f"did_summary_{client_id}.csv"
    inn_summary.to_csv(inn_summary_file, index=False)

    # === 2. Per DRUGS Summary with Classification ===
    drugs_summary = df_did.groupby(['DRUGS_ID', 'DRUGS_NAME', 'INN_ID', 'INN_NAME', 'NFC1_ID']).agg({
        'EVENT_ID': 'count',
        'SHARE_INTERNAL': 'mean',
        'SHARE_LOST': 'mean',
        'SHARE_SAME_NFC1': 'mean',
        'SHARE_DIFF_NFC1': 'mean',
        'INTERNAL_LIFT': 'sum',
        'LOST_SALES': 'sum',
        'TOTAL_EFFECT': 'sum',
        'STOCKOUT_WEEKS': 'mean'
    }).reset_index()

    drugs_summary.columns = [
        'DRUGS_ID', 'DRUGS_NAME', 'INN_ID', 'INN_NAME', 'NFC1_ID',
        'EVENTS_COUNT', 'SHARE_INTERNAL', 'SHARE_LOST',
        'SHARE_SAME_NFC1', 'SHARE_DIFF_NFC1',
        'INTERNAL_LIFT', 'LOST_SALES', 'TOTAL_EFFECT',
        'AVG_STOCKOUT_WEEKS'
    ]

    # Класифікація
    drugs_summary['CLASSIFICATION'] = drugs_summary.apply(
        lambda row: classify_drug(row['SHARE_INTERNAL'], row['SHARE_LOST']),
        axis=1
    )

    drugs_summary_file = paths['stats_folder'] / f"drugs_summary_{client_id}.csv"
    drugs_summary.to_csv(drugs_summary_file, index=False)

    # === 3. Metadata ===
    classification_counts = drugs_summary['CLASSIFICATION'].value_counts().to_dict()

    metadata = {
        'PARAMETER': [
            'CLIENT_ID',
            'GENERATION_TIMESTAMP',
            'MIN_POST_PERIOD_WEEKS',
            'MAX_POST_GAP_WEEKS',
            'CRITICAL_THRESHOLD',
            'SUBSTITUTABLE_THRESHOLD',
            'TOTAL_EVENTS',
            'TOTAL_UNIQUE_DRUGS',
            'TOTAL_INN_GROUPS',
            'AVG_SHARE_INTERNAL',
            'AVG_SHARE_LOST',
            'CRITICAL_DRUGS',
            'SUBSTITUTABLE_DRUGS',
            'MODERATE_DRUGS',
            'UNKNOWN_DRUGS'
        ],
        'VALUE': [
            client_id,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            MIN_POST_PERIOD_WEEKS,
            MAX_POST_GAP_WEEKS,
            CRITICAL_THRESHOLD,
            SUBSTITUTABLE_THRESHOLD,
            len(df_did),
            df_did['DRUGS_ID'].nunique(),
            df_did['INN_ID'].nunique(),
            round(df_did['SHARE_INTERNAL'].dropna().mean(), 4),
            round(df_did['SHARE_LOST'].dropna().mean(), 4),
            classification_counts.get('CRITICAL', 0),
            classification_counts.get('SUBSTITUTABLE', 0),
            classification_counts.get('MODERATE', 0),
            classification_counts.get('UNKNOWN', 0)
        ]
    }

    df_metadata = pd.DataFrame(metadata)
    metadata_file = paths['stats_folder'] / f"did_metadata_{client_id}.csv"
    df_metadata.to_csv(metadata_file, index=False)

    print(f"\nКласифікація препаратів:")
    print(f"  CRITICAL: {classification_counts.get('CRITICAL', 0)}")
    print(f"  SUBSTITUTABLE: {classification_counts.get('SUBSTITUTABLE', 0)}")
    print(f"  MODERATE: {classification_counts.get('MODERATE', 0)}")


# =============================================================================
# PROCESS ALL MARKETS
# =============================================================================

def process_all_markets() -> List[Dict]:
    """
    Обробити всі ринки.

    Returns:
        List[Dict]: Результати по кожному ринку
    """
    try:
        target_pharmacies = load_target_pharmacies()
    except FileNotFoundError as e:
        print(f"ПОМИЛКА: {e}")
        print("Спочатку виконайте preprocessing: python exec_scripts/01_did_processing/01_preproc.py")
        return []

    print(f"\n{'#'*60}")
    print(f"DiD ANALYSIS: {len(target_pharmacies)} ринків")
    print(f"{'#'*60}")

    all_results = []

    for i, client_id in enumerate(target_pharmacies):
        print(f"\n[{i+1}/{len(target_pharmacies)}] Ринок {client_id}")

        try:
            result = process_market_did(client_id)
            all_results.append(result)
        except Exception as e:
            print(f"ПОМИЛКА при обробці ринку {client_id}: {e}")
            all_results.append({
                'client_id': client_id,
                'error': str(e)
            })

    # Підсумок
    print(f"\n{'#'*60}")
    print(f"ПІДСУМОК DiD ANALYSIS")
    print(f"{'#'*60}")

    successful = [r for r in all_results if 'error' not in r]
    failed = [r for r in all_results if 'error' in r]

    print(f"Успішно: {len(successful)}/{len(target_pharmacies)}")
    print(f"З помилками: {len(failed)}")

    if successful:
        total_events = sum(r.get('events_count', 0) for r in successful)
        total_valid = sum(r.get('valid_events', 0) for r in successful)
        total_time = sum(r.get('elapsed_seconds', 0) for r in successful)

        print(f"\nЗагалом:")
        print(f"  Stock-out подій: {total_events:,}")
        print(f"  Валідних DiD подій: {total_valid:,}")
        if total_events > 0:
            print(f"  Validation rate: {total_valid / total_events * 100:.1f}%")
        print(f"  Час: {total_time:.1f} сек")

    if failed:
        print("\nПомилки:")
        for r in failed:
            print(f"  {r['client_id']}: {r['error']}")

    return all_results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='DiD Analysis per market (Phase 1, Step 3)'
    )

    parser.add_argument(
        '--market_id', '-m',
        type=int,
        help='ID ринку (CLIENT_ID) для обробки'
    )

    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Обробити всі ринки'
    )

    args = parser.parse_args()

    if args.all:
        process_all_markets()
    elif args.market_id:
        process_market_did(args.market_id)
    else:
        parser.print_help()
        print("\nПриклади:")
        print("  python exec_scripts/01_did_processing/02_03_did_analysis.py --market_id 28670")
        print("  python exec_scripts/01_did_processing/02_03_did_analysis.py --all")


if __name__ == "__main__":
    main()
