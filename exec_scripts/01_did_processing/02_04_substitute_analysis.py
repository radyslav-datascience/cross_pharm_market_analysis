# =============================================================================
# 02_04_SUBSTITUTE_ANALYSIS - cross_pharm_market_analysis
# =============================================================================
# Файл: exec_scripts/01_did_processing/02_04_substitute_analysis.py
# Дата: 2026-01-28
# Опис: Аналіз SUBSTITUTE_SHARE per market (Phase 1, Step 4)
# =============================================================================
"""
Скрипт аналізу частки substitutes для мульти-ринкового дослідження субституції.

Функціонал:
    1. Завантаження DiD результатів з етапу 03
    2. Для кожної події з INTERNAL_LIFT > 0:
       - Отримання substitutes з mapping
       - Розрахунок LIFT per substitute
    3. Агрегація по (STOCKOUT_DRUG_ID, SUBSTITUTE_DRUG_ID)
    4. Фільтрація: TOTAL_LIFT > 0 (Zero-LIFT Filter)
    5. Розрахунок SUBSTITUTE_SHARE = TOTAL_LIFT / INTERNAL_LIFT × 100%
    6. Генерація статистики

Бізнес-питання:
    Коли препарат X відсутній — який саме substitute забирає найбільше попиту?

Вхід:
    data/processed_data/01_per_market/{CLIENT_ID}/03_did_analysis_{CLIENT_ID}/
    ├── did_results_{CLIENT_ID}.csv
    └── substitute_mapping_{CLIENT_ID}.csv

    data/processed_data/01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
    └── inn_{INN_ID}_{CLIENT_ID}.csv

Вихід:
    data/processed_data/01_per_market/{CLIENT_ID}/04_substitute_shares_{CLIENT_ID}/
    ├── substitute_shares_{CLIENT_ID}.csv   # LIFT та SHARE per substitute
    └── _stats/
        ├── substitute_summary_{CLIENT_ID}.csv  # Зведена статистика
        └── substitute_metadata_{CLIENT_ID}.csv # Параметри та метадані

Використання:
    # Обробка одного ринку:
    python exec_scripts/01_did_processing/02_04_substitute_analysis.py --market_id 28670

    # Обробка всіх ринків:
    python exec_scripts/01_did_processing/02_04_substitute_analysis.py --all
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

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
from project_core.utility_functions.did_utils import (
    calculate_substitute_lift
)


# =============================================================================
# CONSTANTS
# =============================================================================

PER_MARKET_FOLDER = "01_per_market"

# Мінімальний TOTAL_LIFT для включення substitute в результат
# Бізнес-логіка: substitutes з LIFT=0 не мають цінності для аналізу
MIN_TOTAL_LIFT = 0.0


# =============================================================================
# PATH FUNCTIONS
# =============================================================================

def get_substitute_paths(client_id: int) -> Dict[str, Path]:
    """
    Отримати шляхи для Substitute analysis етапу.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict з шляхами
    """
    market_folder = PROCESSED_DATA_PATH / PER_MARKET_FOLDER / str(client_id)
    substitute_folder = market_folder / f"04_substitute_shares_{client_id}"
    stats_folder = substitute_folder / "_stats"
    did_folder = market_folder / f"03_did_analysis_{client_id}"
    aggregation_folder = market_folder / f"01_aggregation_{client_id}"

    return {
        'market_folder': market_folder,
        'aggregation_folder': aggregation_folder,
        'did_folder': did_folder,
        'substitute_folder': substitute_folder,
        'stats_folder': stats_folder
    }


def ensure_substitute_folders(client_id: int) -> Dict[str, Path]:
    """
    Створити необхідні папки для Substitute analysis.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict з шляхами (папки створені)
    """
    paths = get_substitute_paths(client_id)

    for key in ['substitute_folder', 'stats_folder']:
        paths[key].mkdir(parents=True, exist_ok=True)

    return paths


# =============================================================================
# DATA LOADING
# =============================================================================

def load_did_results(client_id: int, paths: Dict[str, Path]) -> pd.DataFrame:
    """
    Завантажити DiD результати з етапу 03.

    Args:
        client_id: ID цільової аптеки
        paths: Словник шляхів

    Returns:
        DataFrame з DiD результатами
    """
    did_file = paths['did_folder'] / f"did_results_{client_id}.csv"

    if not did_file.exists():
        raise FileNotFoundError(f"DiD результати не знайдені: {did_file}")

    df = pd.read_csv(did_file)

    # Конвертуємо дати
    date_cols = ['STOCKOUT_START', 'STOCKOUT_END', 'PRE_START', 'PRE_END']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    return df


def load_substitute_mapping(client_id: int, paths: Dict[str, Path]) -> pd.DataFrame:
    """
    Завантажити substitute mapping з етапу 03.

    Args:
        client_id: ID цільової аптеки
        paths: Словник шляхів

    Returns:
        DataFrame з substitute mapping
    """
    mapping_file = paths['did_folder'] / f"substitute_mapping_{client_id}.csv"

    if not mapping_file.exists():
        raise FileNotFoundError(f"Substitute mapping не знайдений: {mapping_file}")

    return pd.read_csv(mapping_file)


def load_aggregation_data(client_id: int, inn_id: int, paths: Dict[str, Path]) -> pd.DataFrame:
    """
    Завантажити агреговані дані для INN групи.

    Args:
        client_id: ID цільової аптеки
        inn_id: ID INN групи
        paths: Словник шляхів

    Returns:
        DataFrame з агрегованими даними
    """
    agg_file = paths['aggregation_folder'] / f"inn_{inn_id}_{client_id}.csv"

    if not agg_file.exists():
        return pd.DataFrame()

    df = pd.read_csv(agg_file)

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])

    return df


# =============================================================================
# SUBSTITUTE LIFT CALCULATION
# =============================================================================

def calculate_lifts_for_event(
    event: pd.Series,
    event_subs: pd.DataFrame,
    df_agg: pd.DataFrame,
    drug_index: Optional[Dict[int, pd.DataFrame]] = None
) -> List[Dict[str, Any]]:
    """
    Розрахунок LIFT для кожного substitute в одній stock-out події.

    Args:
        event: Рядок з did_results (одна подія)
        event_subs: Substitute mapping для цієї конкретної події
        df_agg: Агреговані дані INN групи
        drug_index: Попередньо побудований індекс {DRUGS_ID: DataFrame}
                    (опціонально, для оптимізації)

    Returns:
        List of dicts з LIFT per substitute
    """
    inn_id = event['INN_ID']
    inn_name = event['INN_NAME']
    stockout_drug_id = event['DRUGS_ID']
    stockout_drug_name = event['DRUGS_NAME']
    stockout_nfc1 = event['NFC1_ID']
    market_growth = event['MARKET_GROWTH']

    pre_start = event['PRE_START']
    pre_end = event['PRE_END']
    stockout_start = event['STOCKOUT_START']
    stockout_end = event['STOCKOUT_END']

    if len(event_subs) == 0:
        return []

    # Побудова індексу якщо не передано
    if drug_index is None:
        drug_index = {did: grp for did, grp in df_agg.groupby('DRUGS_ID')}

    results = []

    for _, sub in event_subs.iterrows():
        sub_drug_id = sub['SUBSTITUTE_DRUGS_ID']
        sub_drug_name = sub['SUBSTITUTE_DRUGS_NAME']
        sub_nfc1 = sub['SUBSTITUTE_NFC1_ID']
        same_nfc1 = sub['SAME_NFC1']

        # Використовуємо pre-indexed lookup замість фільтрації
        df_sub = drug_index.get(sub_drug_id)

        if df_sub is None or len(df_sub) == 0:
            continue

        # Розрахунок LIFT
        try:
            lift_result = calculate_substitute_lift(
                df_substitute=df_sub,
                pre_start=pre_start,
                pre_end=pre_end,
                during_start=stockout_start,
                during_end=stockout_end,
                market_growth=market_growth,
                date_col='Date',
                quantity_col='Q'
            )
            lift = lift_result['lift']
        except (KeyError, ValueError, TypeError) as e:
            # Очікувані помилки при відсутності даних - встановлюємо LIFT=0
            lift = 0.0
        except Exception as e:
            # Неочікувані помилки - логуємо для дебагу
            print(f"    УВАГА: Помилка розрахунку LIFT для substitute {sub_drug_id}: {type(e).__name__}: {e}")
            lift = 0.0

        results.append({
            'EVENT_ID': event['EVENT_ID'],
            'INN_ID': inn_id,
            'INN_NAME': inn_name,
            'STOCKOUT_DRUG_ID': stockout_drug_id,
            'STOCKOUT_DRUG_NAME': stockout_drug_name,
            'STOCKOUT_NFC1_ID': stockout_nfc1,
            'SUBSTITUTE_DRUG_ID': sub_drug_id,
            'SUBSTITUTE_DRUG_NAME': sub_drug_name,
            'SUBSTITUTE_NFC1_ID': sub_nfc1,
            'SAME_NFC1': same_nfc1,
            'LIFT': lift
        })

    return results


# =============================================================================
# AGGREGATION AND SHARE CALCULATION
# =============================================================================

def aggregate_and_calculate_shares(
    df_event_lifts: pd.DataFrame,
    client_id: int
) -> pd.DataFrame:
    """
    Агрегація LIFT по (STOCKOUT_DRUG_ID, SUBSTITUTE_DRUG_ID) та розрахунок SHARE.

    Args:
        df_event_lifts: DataFrame з LIFT per event per substitute
        client_id: ID цільової аптеки

    Returns:
        DataFrame з агрегованими результатами та SUBSTITUTE_SHARE
    """
    if len(df_event_lifts) == 0:
        return pd.DataFrame()

    # Агрегація по (INN, STOCKOUT_DRUG_ID, SUBSTITUTE_DRUG_ID)
    df_agg = df_event_lifts.groupby(
        ['INN_ID', 'INN_NAME',
         'STOCKOUT_DRUG_ID', 'STOCKOUT_DRUG_NAME', 'STOCKOUT_NFC1_ID',
         'SUBSTITUTE_DRUG_ID', 'SUBSTITUTE_DRUG_NAME', 'SUBSTITUTE_NFC1_ID', 'SAME_NFC1']
    ).agg({
        'LIFT': 'sum',
        'EVENT_ID': 'count'
    }).reset_index()

    df_agg = df_agg.rename(columns={
        'LIFT': 'TOTAL_LIFT',
        'EVENT_ID': 'EVENTS_COUNT'
    })

    # Zero-LIFT Filter: залишаємо тільки substitutes з TOTAL_LIFT > 0
    count_before = len(df_agg)
    df_agg = df_agg[df_agg['TOTAL_LIFT'] > MIN_TOTAL_LIFT].copy()
    count_filtered = count_before - len(df_agg)

    if len(df_agg) == 0:
        return pd.DataFrame()

    # Розрахунок INTERNAL_LIFT для кожного stockout drug
    internal_lift = df_agg.groupby('STOCKOUT_DRUG_ID')['TOTAL_LIFT'].sum().reset_index()
    internal_lift = internal_lift.rename(columns={'TOTAL_LIFT': 'INTERNAL_LIFT'})

    df_agg = df_agg.merge(internal_lift, on='STOCKOUT_DRUG_ID', how='left')

    # Розрахунок SUBSTITUTE_SHARE
    df_agg['SUBSTITUTE_SHARE'] = np.where(
        df_agg['INTERNAL_LIFT'] > 0,
        df_agg['TOTAL_LIFT'] / df_agg['INTERNAL_LIFT'] * 100,
        0.0
    )

    # Розділення LIFT по NFC1
    df_agg['LIFT_SAME_NFC1'] = np.where(df_agg['SAME_NFC1'], df_agg['TOTAL_LIFT'], 0.0)
    df_agg['LIFT_DIFF_NFC1'] = np.where(~df_agg['SAME_NFC1'], df_agg['TOTAL_LIFT'], 0.0)

    # Додаємо CLIENT_ID
    df_agg['CLIENT_ID'] = client_id

    # Сортування по SHARE (desc) в межах кожного stockout drug
    df_agg = df_agg.sort_values(
        ['STOCKOUT_DRUG_ID', 'SUBSTITUTE_SHARE'],
        ascending=[True, False]
    )

    # Впорядкування колонок (відповідно до оригіналу та документації)
    columns_order = [
        'CLIENT_ID',
        'INN_ID', 'INN_NAME',
        'STOCKOUT_DRUG_ID', 'STOCKOUT_DRUG_NAME', 'STOCKOUT_NFC1_ID',
        'SUBSTITUTE_DRUG_ID', 'SUBSTITUTE_DRUG_NAME', 'SUBSTITUTE_NFC1_ID',
        'SAME_NFC1', 'TOTAL_LIFT', 'LIFT_SAME_NFC1', 'LIFT_DIFF_NFC1',
        'INTERNAL_LIFT', 'SUBSTITUTE_SHARE', 'EVENTS_COUNT'
    ]

    # Залишаємо тільки існуючі колонки
    columns_order = [c for c in columns_order if c in df_agg.columns]
    df_agg = df_agg[columns_order]

    return df_agg, count_filtered


# =============================================================================
# STATISTICS GENERATION
# =============================================================================

def generate_substitute_summary(
    df_shares: pd.DataFrame,
    client_id: int
) -> pd.DataFrame:
    """
    Генерація зведеної статистики по substitute shares.

    Args:
        df_shares: DataFrame з substitute shares
        client_id: ID цільової аптеки

    Returns:
        DataFrame зі зведеною статистикою
    """
    if len(df_shares) == 0:
        return pd.DataFrame()

    summary_rows = []

    # Загальна статистика
    summary_rows.append({
        'METRIC': 'UNIQUE_STOCKOUT_DRUGS',
        'VALUE': df_shares['STOCKOUT_DRUG_ID'].nunique()
    })
    summary_rows.append({
        'METRIC': 'UNIQUE_SUBSTITUTES',
        'VALUE': df_shares['SUBSTITUTE_DRUG_ID'].nunique()
    })
    summary_rows.append({
        'METRIC': 'TOTAL_PAIRS',
        'VALUE': len(df_shares)
    })
    summary_rows.append({
        'METRIC': 'TOTAL_LIFT',
        'VALUE': df_shares['TOTAL_LIFT'].sum()
    })
    summary_rows.append({
        'METRIC': 'AVG_SUBSTITUTE_SHARE',
        'VALUE': df_shares['SUBSTITUTE_SHARE'].mean()
    })
    summary_rows.append({
        'METRIC': 'MEDIAN_SUBSTITUTE_SHARE',
        'VALUE': df_shares['SUBSTITUTE_SHARE'].median()
    })

    # Статистика по NFC1
    lift_same = df_shares['LIFT_SAME_NFC1'].sum()
    lift_diff = df_shares['LIFT_DIFF_NFC1'].sum()
    total_lift = lift_same + lift_diff

    summary_rows.append({
        'METRIC': 'LIFT_SAME_NFC1',
        'VALUE': lift_same
    })
    summary_rows.append({
        'METRIC': 'LIFT_DIFF_NFC1',
        'VALUE': lift_diff
    })
    summary_rows.append({
        'METRIC': 'SHARE_SAME_NFC1_PERCENT',
        'VALUE': (lift_same / total_lift * 100) if total_lift > 0 else 0
    })

    # Розподіл по категоріях SHARE
    shares = df_shares['SUBSTITUTE_SHARE']
    summary_rows.append({
        'METRIC': 'COUNT_SHARE_100',
        'VALUE': (shares == 100.0).sum()
    })
    summary_rows.append({
        'METRIC': 'COUNT_SHARE_50_99',
        'VALUE': ((shares >= 50) & (shares < 100)).sum()
    })
    summary_rows.append({
        'METRIC': 'COUNT_SHARE_25_49',
        'VALUE': ((shares >= 25) & (shares < 50)).sum()
    })
    summary_rows.append({
        'METRIC': 'COUNT_SHARE_10_24',
        'VALUE': ((shares >= 10) & (shares < 25)).sum()
    })
    summary_rows.append({
        'METRIC': 'COUNT_SHARE_BELOW_10',
        'VALUE': (shares < 10).sum()
    })

    df_summary = pd.DataFrame(summary_rows)
    df_summary['CLIENT_ID'] = client_id

    return df_summary[['CLIENT_ID', 'METRIC', 'VALUE']]


def generate_metadata(
    client_id: int,
    events_processed: int,
    events_with_lift: int,
    pairs_count: int,
    filtered_count: int,
    processing_time: float
) -> pd.DataFrame:
    """
    Генерація метаданих обробки.

    Args:
        client_id: ID цільової аптеки
        events_processed: Кількість оброблених подій
        events_with_lift: Кількість подій з INTERNAL_LIFT > 0
        pairs_count: Кількість пар (stockout, substitute)
        filtered_count: Кількість відфільтрованих пар (LIFT=0)
        processing_time: Час обробки в секундах

    Returns:
        DataFrame з метаданими
    """
    metadata = {
        'CLIENT_ID': [client_id],
        'PROCESSING_DATE': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        'EVENTS_PROCESSED': [events_processed],
        'EVENTS_WITH_LIFT': [events_with_lift],
        'PAIRS_TOTAL': [pairs_count + filtered_count],
        'PAIRS_AFTER_FILTER': [pairs_count],
        'PAIRS_FILTERED_ZERO_LIFT': [filtered_count],
        'PROCESSING_TIME_SEC': [round(processing_time, 2)],
        'MIN_TOTAL_LIFT_THRESHOLD': [MIN_TOTAL_LIFT]
    }

    return pd.DataFrame(metadata)


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_market(client_id: int) -> Dict[str, Any]:
    """
    Обробка одного ринку (цільової аптеки).

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict з результатами та статистикою
    """
    start_time = datetime.now()

    print(f"\n{'='*60}")
    print(f"MARKET {client_id}: SUBSTITUTE ANALYSIS")
    print(f"{'='*60}")

    # Створюємо папки
    paths = ensure_substitute_folders(client_id)

    # === 1. Завантаження даних ===
    print("\n[1/4] Завантаження даних...")

    try:
        df_did = load_did_results(client_id, paths)
        print(f"  DiD результатів: {len(df_did):,}")
    except FileNotFoundError as e:
        print(f"  ПОМИЛКА: {e}")
        return {'status': 'error', 'error': str(e)}

    try:
        df_mapping = load_substitute_mapping(client_id, paths)
        print(f"  Substitute mapping: {len(df_mapping):,}")
    except FileNotFoundError as e:
        print(f"  ПОМИЛКА: {e}")
        return {'status': 'error', 'error': str(e)}

    # Фільтруємо події з INTERNAL_LIFT > 0
    df_did_valid = df_did[df_did['INTERNAL_LIFT'] > 0].copy()
    print(f"  Подій з INTERNAL_LIFT > 0: {len(df_did_valid):,}")

    if len(df_did_valid) == 0:
        print("  УВАГА: Немає подій з INTERNAL_LIFT > 0")
        return {'status': 'no_data', 'events': 0}

    # === 2. Розрахунок LIFT per substitute per event ===
    print("\n[2/4] Розрахунок LIFT per substitute...")

    all_event_lifts = []
    inn_cache = {}  # Кеш агрегованих даних по INN
    drug_index_cache = {}  # Кеш pre-indexed drug lookups по INN

    # Pre-index df_mapping по EVENT_ID для O(1) lookup
    mapping_by_event = {eid: grp for eid, grp in df_mapping.groupby('EVENT_ID')}

    for idx, event in df_did_valid.iterrows():
        inn_id = event['INN_ID']
        event_id = event['EVENT_ID']

        # Завантажуємо агреговані дані (з кешу якщо є)
        if inn_id not in inn_cache:
            inn_cache[inn_id] = load_aggregation_data(client_id, inn_id, paths)
            # Pre-index по DRUGS_ID для цього INN
            df_cached = inn_cache[inn_id]
            if len(df_cached) > 0:
                drug_index_cache[inn_id] = {did: grp for did, grp in df_cached.groupby('DRUGS_ID')}
            else:
                drug_index_cache[inn_id] = {}

        df_agg = inn_cache[inn_id]

        if len(df_agg) == 0:
            continue

        # Отримуємо substitutes для цієї події через pre-indexed lookup
        event_subs = mapping_by_event.get(event_id)
        if event_subs is None or len(event_subs) == 0:
            continue

        # Розраховуємо LIFT для кожного substitute (з pre-indexed drug lookup)
        event_lifts = calculate_lifts_for_event(
            event, event_subs, df_agg,
            drug_index=drug_index_cache.get(inn_id)
        )
        all_event_lifts.extend(event_lifts)

    print(f"  Розраховано LIFT записів: {len(all_event_lifts):,}")

    if len(all_event_lifts) == 0:
        print("  УВАГА: Немає LIFT записів")
        return {'status': 'no_lifts', 'events': len(df_did_valid)}

    df_event_lifts = pd.DataFrame(all_event_lifts)

    # === 3. Агрегація та розрахунок SHARE ===
    print("\n[3/4] Агрегація та розрахунок SUBSTITUTE_SHARE...")

    df_shares, filtered_count = aggregate_and_calculate_shares(df_event_lifts, client_id)

    if filtered_count > 0:
        print(f"  Відфільтровано пар з LIFT=0: {filtered_count}")

    print(f"  Фінальних пар (stockout, substitute): {len(df_shares):,}")

    if len(df_shares) == 0:
        print("  УВАГА: Всі пари мають LIFT=0")
        return {'status': 'all_zero_lift', 'events': len(df_did_valid)}

    # Валідація: сума SHARE = 100%
    share_sums = df_shares.groupby('STOCKOUT_DRUG_ID')['SUBSTITUTE_SHARE'].sum()
    deviations = share_sums[abs(share_sums - 100.0) > 0.1]
    if len(deviations) > 0:
        print(f"  УВАГА: {len(deviations)} stockout drugs з сумою SHARE != 100%")
    else:
        print(f"  Валідація: Всі суми SHARE = 100%")

    # === 4. Збереження результатів ===
    print("\n[4/4] Збереження результатів...")

    # Substitute shares
    shares_file = paths['substitute_folder'] / f"substitute_shares_{client_id}.csv"
    df_shares.to_csv(shares_file, index=False)
    print(f"  {shares_file.name}: {len(df_shares):,} записів")

    # Summary statistics
    df_summary = generate_substitute_summary(df_shares, client_id)
    summary_file = paths['stats_folder'] / f"substitute_summary_{client_id}.csv"
    df_summary.to_csv(summary_file, index=False)
    print(f"  {summary_file.name}")

    # Metadata
    processing_time = (datetime.now() - start_time).total_seconds()
    df_metadata = generate_metadata(
        client_id=client_id,
        events_processed=len(df_did_valid),
        events_with_lift=df_shares['STOCKOUT_DRUG_ID'].nunique(),
        pairs_count=len(df_shares),
        filtered_count=filtered_count,
        processing_time=processing_time
    )
    metadata_file = paths['stats_folder'] / f"substitute_metadata_{client_id}.csv"
    df_metadata.to_csv(metadata_file, index=False)
    print(f"  {metadata_file.name}")

    # Статистика
    print(f"\n{'='*60}")
    print(f"РЕЗУЛЬТАТИ MARKET {client_id}:")
    print(f"{'='*60}")
    print(f"  Оброблено подій: {len(df_did_valid):,}")
    print(f"  Унікальних stockout препаратів: {df_shares['STOCKOUT_DRUG_ID'].nunique()}")
    print(f"  Унікальних substitutes: {df_shares['SUBSTITUTE_DRUG_ID'].nunique()}")
    print(f"  Пар (stockout, substitute): {len(df_shares):,}")
    print(f"  Загальний LIFT: {df_shares['TOTAL_LIFT'].sum():,.2f}")

    lift_same = df_shares['LIFT_SAME_NFC1'].sum()
    lift_diff = df_shares['LIFT_DIFF_NFC1'].sum()
    total_lift = lift_same + lift_diff
    same_pct = (lift_same / total_lift * 100) if total_lift > 0 else 0

    print(f"  LIFT SAME_NFC1: {lift_same:,.2f} ({same_pct:.1f}%)")
    print(f"  LIFT DIFF_NFC1: {lift_diff:,.2f} ({100-same_pct:.1f}%)")
    print(f"  Час обробки: {processing_time:.1f} сек")

    return {
        'status': 'success',
        'client_id': client_id,
        'events_processed': len(df_did_valid),
        'stockout_drugs': df_shares['STOCKOUT_DRUG_ID'].nunique(),
        'substitutes': df_shares['SUBSTITUTE_DRUG_ID'].nunique(),
        'pairs_count': len(df_shares),
        'total_lift': df_shares['TOTAL_LIFT'].sum(),
        'same_nfc1_percent': same_pct,
        'processing_time': processing_time
    }


def process_all_markets() -> None:
    """
    Обробка всіх ринків (цільових аптек).
    """
    print("="*70)
    print("SUBSTITUTE ANALYSIS - ALL MARKETS")
    print("="*70)

    # Завантажуємо список цільових аптек
    try:
        target_pharmacies = load_target_pharmacies()
        print(f"\nЦільових аптек: {len(target_pharmacies)}")
    except FileNotFoundError as e:
        print(f"ПОМИЛКА: {e}")
        return

    results = []
    successful = 0
    failed = 0

    for i, client_id in enumerate(target_pharmacies):
        print(f"\n[{i+1}/{len(target_pharmacies)}] Ринок {client_id}")
        result = process_market(client_id)
        results.append(result)

        if result['status'] == 'success':
            successful += 1
        else:
            failed += 1

    # Підсумок
    print("\n" + "="*70)
    print("ПІДСУМОК SUBSTITUTE ANALYSIS")
    print("="*70)
    print(f"Успішно: {successful}/{len(target_pharmacies)}")
    print(f"З помилками: {failed}")

    if successful > 0:
        success_results = [r for r in results if r['status'] == 'success']
        total_pairs = sum(r['pairs_count'] for r in success_results)
        total_lift = sum(r['total_lift'] for r in success_results)
        avg_same_nfc1 = np.mean([r['same_nfc1_percent'] for r in success_results])

        print(f"\nЗагалом:")
        print(f"  Пар (stockout, substitute): {total_pairs:,}")
        print(f"  Загальний LIFT: {total_lift:,.2f}")
        print(f"  Середній % SAME_NFC1: {avg_same_nfc1:.1f}%")


# =============================================================================
# CLI
# =============================================================================

def main():
    """Головна функція CLI."""
    parser = argparse.ArgumentParser(
        description='Substitute Analysis для мульти-ринкового дослідження'
    )
    parser.add_argument(
        '--market_id',
        type=int,
        help='ID цільової аптеки для обробки'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Обробити всі ринки'
    )

    args = parser.parse_args()

    if args.all:
        process_all_markets()
    elif args.market_id:
        process_market(args.market_id)
    else:
        parser.print_help()
        print("\nПриклади використання:")
        print("  python exec_scripts/01_did_processing/02_04_substitute_analysis.py --market_id 28670")
        print("  python exec_scripts/01_did_processing/02_04_substitute_analysis.py --all")


if __name__ == "__main__":
    main()
