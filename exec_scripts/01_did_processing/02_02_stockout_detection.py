# =============================================================================
# 02_02_STOCKOUT_DETECTION - cross_pharm_market_analysis
# =============================================================================
# Файл: exec_scripts/01_did_processing/02_02_stockout_detection.py
# Дата: 2026-01-28
# Опис: Детекція stock-out подій per market (Phase 1, Step 2)
# =============================================================================
"""
Скрипт детекції stock-out подій для мульти-ринкового аналізу.

Функціонал:
    1. Завантаження агрегованих даних з етапу 01
    2. Ідентифікація stock-out періодів (Q=0 протягом ≥MIN_STOCKOUT_WEEKS)
    3. 3-рівнева валідація подій:
       - Market Activity: ринок INN активний під час stock-out
       - PRE-period Sales: були продажі до stock-out
       - Competitors Availability: конкуренти продавали препарат
    4. Розрахунок PRE_AVG_Q (baseline для DiD)
    5. Збереження валідованих подій та статистики

Вхід:
    data/processed_data/01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
    └── inn_{INN_ID}_{CLIENT_ID}.csv

Вихід:
    data/processed_data/01_per_market/{CLIENT_ID}/02_stockout_{CLIENT_ID}/
    ├── stockout_events_{CLIENT_ID}.csv    # Всі валідовані події
    └── _stats/
        └── stockout_summary_{CLIENT_ID}.csv  # Статистика

Використання:
    # Обробка одного ринку:
    python exec_scripts/01_did_processing/02_02_stockout_detection.py --market_id 28670

    # Обробка всіх ринків:
    python exec_scripts/01_did_processing/02_02_stockout_detection.py --all
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

import pandas as pd
import numpy as np

# Додаємо project root до sys.path для імпортів
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Імпорти з project_core
from project_core.data_config.paths_config import (
    PROCESSED_DATA_PATH,
    load_target_pharmacies,
    get_market_paths
)
from project_core.did_config.stockout_params import (
    MIN_STOCKOUT_WEEKS,
    MIN_PRE_PERIOD_WEEKS
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Структура папок
PER_MARKET_FOLDER = "01_per_market"


# =============================================================================
# PATH FUNCTIONS
# =============================================================================

def get_stockout_paths(client_id: int) -> Dict[str, Path]:
    """
    Отримати шляхи для stockout detection етапу.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict з шляхами
    """
    market_folder = PROCESSED_DATA_PATH / PER_MARKET_FOLDER / str(client_id)
    stockout_folder = market_folder / f"02_stockout_{client_id}"
    stats_folder = stockout_folder / "_stats"
    aggregation_folder = market_folder / f"01_aggregation_{client_id}"

    return {
        'market_folder': market_folder,
        'aggregation_folder': aggregation_folder,
        'stockout_folder': stockout_folder,
        'stats_folder': stats_folder
    }


def ensure_stockout_folders(client_id: int) -> Dict[str, Path]:
    """
    Створити необхідні папки для stockout detection.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict з шляхами (папки створені)
    """
    paths = get_stockout_paths(client_id)

    for key in ['stockout_folder', 'stats_folder']:
        paths[key].mkdir(parents=True, exist_ok=True)

    return paths


# =============================================================================
# STOCKOUT IDENTIFICATION
# =============================================================================

def identify_stockout_periods(
    df_drug: pd.DataFrame,
    min_stockout_weeks: int = MIN_STOCKOUT_WEEKS
) -> List[Dict]:
    """
    Ідентифікувати періоди stock-out для одного препарату.

    Stock-out = тиждень без продажів (Q == 0).
    Період stock-out = послідовні тижні з Q=0.

    Args:
        df_drug: Дані одного препарату (DRUGS_ID) з колонками: Date, Q
        min_stockout_weeks: Мінімальна тривалість stock-out для реєстрації

    Returns:
        List[Dict]: Список stock-out періодів з start, end, weeks
    """
    if len(df_drug) == 0:
        return []

    # Сортуємо по датах
    df_sorted = df_drug.sort_values('Date').copy()

    stockout_periods = []
    current_stockout_start = None
    current_stockout_weeks = 0

    for _, row in df_sorted.iterrows():
        week = row['Date']
        has_sales = row['Q'] > 0

        if not has_sales:
            # Stock-out тиждень
            if current_stockout_start is None:
                current_stockout_start = week
            current_stockout_weeks += 1
        else:
            # Продажі були - закриваємо поточний stock-out період
            if current_stockout_start is not None and current_stockout_weeks >= min_stockout_weeks:
                stockout_periods.append({
                    'start': current_stockout_start,
                    'end': week - timedelta(days=7),
                    'weeks': current_stockout_weeks
                })
            current_stockout_start = None
            current_stockout_weeks = 0

    # Останній період (якщо закінчується stock-out)
    if current_stockout_start is not None and current_stockout_weeks >= min_stockout_weeks:
        last_week = df_sorted['Date'].max()
        stockout_periods.append({
            'start': current_stockout_start,
            'end': last_week,
            'weeks': current_stockout_weeks
        })

    return stockout_periods


# =============================================================================
# STOCKOUT VALIDATION
# =============================================================================

def validate_stockout_event(
    df_drug: pd.DataFrame,
    df_inn: pd.DataFrame,
    stockout_start: pd.Timestamp,
    stockout_end: pd.Timestamp,
    pre_start: pd.Timestamp,
    pre_end: pd.Timestamp,
    min_pre_weeks: int = MIN_PRE_PERIOD_WEEKS
) -> Tuple[bool, str, Dict]:
    """
    3-рівнева валідація stock-out події.

    Перевірки:
    1. Market Activity — ринок INN групи активний під час stock-out
       (на рівні всієї INN для консистентності з MARKET_GROWTH в DiD)
    2. PRE-period Sales — були продажі TARGET до stock-out
       (на рівні конкретного препарату)
    3. Competitors Availability — конкуренти продавали препарат під час stock-out
       (на рівні конкретного препарату)

    Args:
        df_drug: Дані одного препарату (TARGET pharmacy)
        df_inn: Дані всієї INN групи (для Level 1 перевірки)
        stockout_start: Початок stock-out
        stockout_end: Кінець stock-out
        pre_start: Початок PRE-періоду
        pre_end: Кінець PRE-періоду
        min_pre_weeks: Мінімальна кількість тижнів у PRE-періоді

    Returns:
        Tuple[is_valid, reason, details]
    """
    details = {}

    # === РІВЕНЬ 1: Market Activity (INN group level) ===
    # Чи був ринок INN групи активний під час stock-out?
    # Перевіряємо на рівні всієї INN для консистентності з MARKET_GROWTH в Step 3
    # (якщо INN група неактивна — це не stock-out, це відсутність попиту)
    df_inn_during = df_inn[
        (df_inn['Date'] >= stockout_start) &
        (df_inn['Date'] <= stockout_end)
    ]

    # Сума продажів по всій INN групі на ринку
    market_during_inn = df_inn_during['MARKET_TOTAL_DRUGS_PACK'].sum()
    details['market_during_inn'] = market_during_inn

    if market_during_inn == 0:
        return False, 'no_market_activity', details

    # === РІВЕНЬ 2: PRE-period Sales (drug level) ===
    # Чи були продажі цього конкретного препарату до stock-out?
    # Перевіряємо на рівні препарату (суворіша перевірка для якості даних)
    df_pre = df_drug[
        (df_drug['Date'] >= pre_start) &
        (df_drug['Date'] <= pre_end)
    ]

    pre_sales = df_pre['Q'].sum()
    pre_weeks = len(df_pre)
    details['pre_sales'] = pre_sales
    details['pre_weeks'] = pre_weeks

    if pre_weeks < min_pre_weeks or pre_sales == 0:
        return False, 'no_pre_sales', details

    # === РІВЕНЬ 3: Competitors Availability (drug level) ===
    # Чи продавали конкуренти цей конкретний препарат під час stock-out?
    # Перевіряємо на рівні препарату (конкуренти мають альтернативу саме цього ліку)
    df_drug_during = df_drug[
        (df_drug['Date'] >= stockout_start) &
        (df_drug['Date'] <= stockout_end)
    ]
    competitors_sales = df_drug_during['MARKET_TOTAL_DRUGS_PACK'].sum()
    details['competitors_sales'] = competitors_sales

    if competitors_sales == 0:
        return False, 'no_competitors', details

    # Всі перевірки пройдено
    details['pre_avg_q'] = pre_sales / pre_weeks if pre_weeks > 0 else 0
    return True, 'valid', details


# =============================================================================
# PROCESS SINGLE MARKET
# =============================================================================

def process_market_stockout(client_id: int) -> Dict:
    """
    Повна обробка stock-out для одного ринку.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict: Результати обробки
    """
    start_time = datetime.now()

    # Підготовка папок
    paths = ensure_stockout_folders(client_id)

    print(f"\n{'='*60}")
    print(f"STOCKOUT DETECTION: CLIENT_ID = {client_id}")
    print(f"{'='*60}")

    # Завантаження агрегованих файлів
    aggregation_folder = paths['aggregation_folder']

    if not aggregation_folder.exists():
        raise FileNotFoundError(
            f"Aggregation папка не знайдена: {aggregation_folder}\n"
            f"Спочатку виконайте: python exec_scripts/01_did_processing/02_01_data_aggregation.py --market_id {client_id}"
        )

    # Знаходимо всі inn_*.csv файли
    inn_files = list(aggregation_folder.glob(f"inn_*_{client_id}.csv"))

    if not inn_files:
        raise FileNotFoundError(f"Не знайдено агрегованих файлів у {aggregation_folder}")

    print(f"Знайдено {len(inn_files)} INN файлів")

    # Результати
    all_events = []
    validation_stats = {
        'valid': 0,
        'no_market_activity': 0,
        'no_pre_sales': 0,
        'no_competitors': 0
    }
    inn_stats = []
    event_counter = 1

    # Обробка кожного INN файлу
    for inn_file in sorted(inn_files):
        # Парсимо INN_ID з назви файлу
        inn_id = int(inn_file.stem.split('_')[1])

        # Завантаження даних
        df = pd.read_csv(inn_file, parse_dates=['Date'])

        if df.empty:
            continue

        inn_name = df['INN_NAME'].iloc[0] if 'INN_NAME' in df.columns else ''

        # Дані вже тільки TARGET (PHARM_ID == CLIENT_ID) після aggregation
        # Отримуємо унікальні препарати
        drugs_ids = df['DRUGS_ID'].unique()

        raw_events_count = 0
        valid_events_count = 0

        for drug_id in drugs_ids:
            df_drug = df[df['DRUGS_ID'] == drug_id].copy()

            if len(df_drug) == 0:
                continue

            # Метадані препарату
            drug_name = df_drug['DRUGS_NAME'].iloc[0]
            nfc1_id = df_drug['NFC1_ID'].iloc[0] if 'NFC1_ID' in df_drug.columns else ''
            nfc_id = df_drug['NFC_ID'].iloc[0] if 'NFC_ID' in df_drug.columns else ''

            # Ідентифікуємо stock-out періоди
            stockout_periods = identify_stockout_periods(df_drug, MIN_STOCKOUT_WEEKS)

            for period in stockout_periods:
                raw_events_count += 1

                # Визначаємо PRE-період
                pre_end = period['start'] - timedelta(days=7)
                pre_start = pre_end - timedelta(weeks=MIN_PRE_PERIOD_WEEKS - 1)

                # Валідація
                is_valid, reason, details = validate_stockout_event(
                    df_drug=df_drug,
                    df_inn=df,  # Повні дані INN групи для Level 1 валідації
                    stockout_start=period['start'],
                    stockout_end=period['end'],
                    pre_start=pre_start,
                    pre_end=pre_end,
                    min_pre_weeks=MIN_PRE_PERIOD_WEEKS
                )

                validation_stats[reason] += 1

                if is_valid:
                    valid_events_count += 1

                    all_events.append({
                        'EVENT_ID': f"{client_id}_{inn_id}_{event_counter:04d}",
                        'CLIENT_ID': client_id,
                        'INN_ID': inn_id,
                        'INN_NAME': inn_name,
                        'DRUGS_ID': drug_id,
                        'DRUGS_NAME': drug_name,
                        'NFC1_ID': nfc1_id,
                        'NFC_ID': nfc_id,
                        'STOCKOUT_START': period['start'].strftime('%Y-%m-%d'),
                        'STOCKOUT_END': period['end'].strftime('%Y-%m-%d'),
                        'STOCKOUT_WEEKS': period['weeks'],
                        'PRE_START': pre_start.strftime('%Y-%m-%d'),
                        'PRE_END': pre_end.strftime('%Y-%m-%d'),
                        'PRE_WEEKS': details['pre_weeks'],
                        'PRE_AVG_Q': round(details['pre_avg_q'], 4),
                        'MARKET_DURING_Q': round(details['market_during_inn'], 2)
                    })
                    event_counter += 1

        # Статистика per INN
        if raw_events_count > 0:
            inn_stats.append({
                'INN_ID': inn_id,
                'INN_NAME': inn_name,
                'DRUGS_COUNT': len(drugs_ids),
                'RAW_EVENTS': raw_events_count,
                'VALID_EVENTS': valid_events_count,
                'VALIDATION_RATE': round(valid_events_count / raw_events_count * 100, 1) if raw_events_count > 0 else 0
            })

    # Зберігаємо результати
    results = {
        'client_id': client_id,
        'inn_count': len(inn_files),
        'raw_events': sum(validation_stats.values()),
        'valid_events': len(all_events),
        'validation_stats': validation_stats,
        'files_created': []
    }

    # Зберігаємо валідовані події
    if all_events:
        df_events = pd.DataFrame(all_events)
        events_file = paths['stockout_folder'] / f"stockout_events_{client_id}.csv"
        df_events.to_csv(events_file, index=False)
        results['files_created'].append(str(events_file))
    else:
        # Створюємо пустий файл з правильними колонками
        empty_df = pd.DataFrame(columns=[
            'EVENT_ID', 'CLIENT_ID', 'INN_ID', 'INN_NAME', 'DRUGS_ID', 'DRUGS_NAME',
            'NFC1_ID', 'NFC_ID', 'STOCKOUT_START', 'STOCKOUT_END', 'STOCKOUT_WEEKS',
            'PRE_START', 'PRE_END', 'PRE_WEEKS', 'PRE_AVG_Q', 'MARKET_DURING_Q'
        ])
        events_file = paths['stockout_folder'] / f"stockout_events_{client_id}.csv"
        empty_df.to_csv(events_file, index=False)
        results['files_created'].append(str(events_file))

    # Зберігаємо статистику
    summary_data = {
        'CLIENT_ID': client_id,
        'INN_COUNT': len(inn_files),
        'TOTAL_RAW_EVENTS': sum(validation_stats.values()),
        'VALID_EVENTS': len(all_events),
        'REJECTED_NO_MARKET': validation_stats['no_market_activity'],
        'REJECTED_NO_PRE_SALES': validation_stats['no_pre_sales'],
        'REJECTED_NO_COMPETITORS': validation_stats['no_competitors'],
        'VALIDATION_RATE': round(len(all_events) / sum(validation_stats.values()) * 100, 1) if sum(validation_stats.values()) > 0 else 0,
        'UNIQUE_DRUGS': len(set(e['DRUGS_ID'] for e in all_events)) if all_events else 0,
        'AVG_STOCKOUT_WEEKS': round(np.mean([e['STOCKOUT_WEEKS'] for e in all_events]), 1) if all_events else 0,
        'TIMESTAMP': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    df_summary = pd.DataFrame([summary_data])
    summary_file = paths['stats_folder'] / f"stockout_summary_{client_id}.csv"
    df_summary.to_csv(summary_file, index=False)
    results['files_created'].append(str(summary_file))

    # Зберігаємо статистику per INN
    if inn_stats:
        df_inn_stats = pd.DataFrame(inn_stats)
        inn_stats_file = paths['stats_folder'] / f"stockout_per_inn_{client_id}.csv"
        df_inn_stats.to_csv(inn_stats_file, index=False)
        results['files_created'].append(str(inn_stats_file))

    # Час виконання
    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_seconds'] = round(elapsed, 2)

    # Вивід результатів
    print(f"\nПараметри:")
    print(f"  MIN_STOCKOUT_WEEKS: {MIN_STOCKOUT_WEEKS}")
    print(f"  MIN_PRE_PERIOD_WEEKS: {MIN_PRE_PERIOD_WEEKS}")

    print(f"\nРезультати:")
    print(f"  INN груп оброблено: {len(inn_files)}")
    print(f"  Сирих подій: {sum(validation_stats.values())}")
    print(f"  Валідних подій: {len(all_events)}")

    if sum(validation_stats.values()) > 0:
        valid_pct = len(all_events) / sum(validation_stats.values()) * 100
        print(f"  Validation rate: {valid_pct:.1f}%")

        print(f"\nПричини відхилення:")
        print(f"  no_market_activity: {validation_stats['no_market_activity']}")
        print(f"  no_pre_sales: {validation_stats['no_pre_sales']}")
        print(f"  no_competitors: {validation_stats['no_competitors']}")

    if all_events:
        avg_weeks = np.mean([e['STOCKOUT_WEEKS'] for e in all_events])
        print(f"\nСередня тривалість stock-out: {avg_weeks:.1f} тижнів")

    print(f"\nЧас: {elapsed:.1f} сек")

    return results


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
    print(f"STOCKOUT DETECTION: {len(target_pharmacies)} ринків")
    print(f"{'#'*60}")

    all_results = []

    for i, client_id in enumerate(target_pharmacies):
        print(f"\n[{i+1}/{len(target_pharmacies)}] Ринок {client_id}")

        try:
            result = process_market_stockout(client_id)
            all_results.append(result)
        except Exception as e:
            print(f"ПОМИЛКА при обробці ринку {client_id}: {e}")
            all_results.append({
                'client_id': client_id,
                'error': str(e)
            })

    # Підсумок
    print(f"\n{'#'*60}")
    print(f"ПІДСУМОК STOCKOUT DETECTION")
    print(f"{'#'*60}")

    successful = [r for r in all_results if 'error' not in r]
    failed = [r for r in all_results if 'error' in r]

    print(f"Успішно: {len(successful)}/{len(target_pharmacies)}")
    print(f"З помилками: {len(failed)}")

    if successful:
        total_raw = sum(r.get('raw_events', 0) for r in successful)
        total_valid = sum(r.get('valid_events', 0) for r in successful)
        total_time = sum(r.get('elapsed_seconds', 0) for r in successful)

        print(f"\nЗагалом:")
        print(f"  Сирих подій: {total_raw:,}")
        print(f"  Валідних подій: {total_valid:,}")
        if total_raw > 0:
            print(f"  Validation rate: {total_valid / total_raw * 100:.1f}%")
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
        description='Stockout detection per market (Phase 1, Step 2)'
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
        process_market_stockout(args.market_id)
    else:
        parser.print_help()
        print("\nПриклади:")
        print("  python exec_scripts/01_did_processing/02_02_stockout_detection.py --market_id 28670")
        print("  python exec_scripts/01_did_processing/02_02_stockout_detection.py --all")


if __name__ == "__main__":
    main()
