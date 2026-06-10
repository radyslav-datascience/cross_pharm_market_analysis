# =============================================================================
# 02_01_DATA_AGGREGATION - cross_pharm_market_analysis
# =============================================================================
# Файл: exec_scripts/01_did_processing/02_01_data_aggregation.py
# Дата: 2026-01-28
# Опис: Агрегація даних per market (Phase 1, Step 1)
# =============================================================================
"""
Скрипт агрегації даних для мульти-ринкового аналізу.

Функціонал:
    1. Завантаження raw даних з Rd2_{CLIENT_ID}.csv
    2. Перейменування та конвертація колонок
    3. Парсинг PERIOD_ID → Date (вирівняно по понеділках)
    4. Обробка кожного INN окремо:
       - Gap filling для часових рядів
       - Тижнева агрегація
    5. Збереження результатів та статистики

Вхід:
    data/raw/Rd2_{CLIENT_ID}.csv

Вихід:
    data/processed_data/01_per_market/{CLIENT_ID}/01_aggregation_{CLIENT_ID}/
    ├── inn_{INN_ID}_{CLIENT_ID}.csv       # Агреговані дані per INN
    └── stats_inn_{CLIENT_ID}/
        ├── summary_{CLIENT_ID}.csv        # Зведена статистика per DRUGS_ID
        └── inn_summary_{CLIENT_ID}.csv    # Агрегована статистика per INN

Використання:
    # Обробка одного ринку:
    python exec_scripts/01_did_processing/02_01_data_aggregation.py --market_id 28670

    # Обробка всіх ринків:
    python exec_scripts/01_did_processing/02_01_data_aggregation.py --all
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import pandas as pd
import numpy as np

# Додаємо project root до sys.path для імпортів
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Імпорти з project_core
from project_core.data_config.paths_config import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    get_market_raw_file,
    load_target_pharmacies,
    CSV_SEPARATOR
)
from project_core.data_config.column_mapping import (
    COLUMN_RENAME_MAP,
    NUMERIC_COLUMNS,
    CATEGORICAL_COLUMNS
)
from project_core.utility_functions.etl_utils import (
    load_raw_data,
    convert_numeric_columns,
    rename_columns,
    add_date_column,
    fill_gaps,
    aggregate_weekly
)
from project_core.did_config.stockout_params import (
    MIN_NOTSOLD_PERCENT,
    MAX_NOTSOLD_PERCENT
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Структура папок згідно узгодженої схеми
PER_MARKET_FOLDER = "01_per_market"


# =============================================================================
# PATH FUNCTIONS
# =============================================================================

def get_aggregation_paths(client_id: int) -> Dict[str, Path]:
    """
    Отримати шляхи для aggregation етапу конкретного ринку.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict з шляхами
    """
    market_folder = PROCESSED_DATA_PATH / PER_MARKET_FOLDER / str(client_id)
    aggregation_folder = market_folder / f"01_aggregation_{client_id}"
    stats_folder = aggregation_folder / f"stats_inn_{client_id}"

    return {
        'market_folder': market_folder,
        'aggregation_folder': aggregation_folder,
        'stats_folder': stats_folder
    }


def ensure_aggregation_folders(client_id: int) -> Dict[str, Path]:
    """
    Створити необхідні папки для aggregation.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict з шляхами (папки створені)
    """
    paths = get_aggregation_paths(client_id)

    for key, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)

    return paths


# =============================================================================
# DATA PROCESSING
# =============================================================================

def load_and_prepare_data(client_id: int) -> pd.DataFrame:
    """
    Завантажити та підготувати raw дані.

    Args:
        client_id: ID цільової аптеки

    Returns:
        pd.DataFrame: Підготовлений датафрейм
    """
    raw_file = get_market_raw_file(client_id)

    if not raw_file.exists():
        raise FileNotFoundError(f"Raw файл не знайдено: {raw_file}")

    print(f"\n{'='*60}")
    print(f"ЗАВАНТАЖЕННЯ ДАНИХ: CLIENT_ID = {client_id}")
    print(f"{'='*60}")

    # 1. Завантажити raw дані
    df = load_raw_data(raw_file, sep=CSV_SEPARATOR)

    # 2. Перейменувати колонки
    df = rename_columns(df, COLUMN_RENAME_MAP)

    # 3. Конвертувати числові колонки (Q, V)
    df = convert_numeric_columns(df, NUMERIC_COLUMNS)

    # 4. Додати колонку Date з PERIOD_ID
    df = add_date_column(df, period_col='PERIOD_ID', date_col='Date', align_monday=True)

    print(f"\nПідготовлено: {len(df):,} рядків, {df['INN_ID'].nunique()} INN груп")

    return df


def calculate_notsold_percent(
    df_target: pd.DataFrame,
    group_cols: List[str] = ['PHARM_ID', 'DRUGS_ID'],
    quantity_col: str = 'Q'
) -> pd.DataFrame:
    """
    Розрахунок NOTSOLD_PERCENT для кожної групи (як в оригіналі).

    NOTSOLD_PERCENT = (тижні з Q=0) / (всього тижнів)

    Args:
        df_target: Датафрейм цільової аптеки (після GAP FILLING!)
        group_cols: Колонки для групування
        quantity_col: Колонка з кількістю

    Returns:
        pd.DataFrame: Датафрейм з колонкою NOTSOLD_PERCENT
    """
    # Guard: пустий df_target → повертаємо пустий результат з правильними колонками
    if df_target.empty:
        return pd.DataFrame(columns=group_cols + ['NOTSOLD_PERCENT'])

    # Використовуємо .agg() замість .apply(pd.Series) — надійніше з pandas 2.x
    # (.apply на пустому DataFrame повертає колонки оригінального df замість заданих)
    notsold_stats = df_target.groupby(group_cols)[quantity_col].agg(
        total_weeks='count',
        zero_weeks=lambda x: (x == 0).sum()
    ).reset_index()

    notsold_stats['NOTSOLD_PERCENT'] = (
        notsold_stats['zero_weeks'] / notsold_stats['total_weeks']
    )

    return notsold_stats[group_cols + ['NOTSOLD_PERCENT']]


def calculate_market_totals(
    df_competitors: pd.DataFrame,
    date_col: str = 'Date',
    drug_col: str = 'DRUGS_ID',
    quantity_col: str = 'Q',
    value_col: str = 'V'
) -> pd.DataFrame:
    """
    Розрахунок ринкових показників по конкурентах (як в оригіналі).

    Args:
        df_competitors: Датафрейм конкурентів (PHARM_ID != TARGET)
        date_col: Колонка з датою
        drug_col: Колонка з ID препарату
        quantity_col: Колонка з кількістю
        value_col: Колонка з виручкою

    Returns:
        pd.DataFrame: Агреговані ринкові показники per Date+DRUGS_ID
    """
    if df_competitors.empty:
        # Повертаємо пустий DataFrame з правильними типами
        empty_df = pd.DataFrame({
            date_col: pd.Series(dtype='datetime64[ns]'),
            drug_col: pd.Series(dtype='int64'),
            'MARKET_TOTAL_DRUGS_PACK': pd.Series(dtype='float64'),
            'MARKET_TOTAL_DRUGS_REVENUE': pd.Series(dtype='float64')
        })
        return empty_df

    market_totals = df_competitors.groupby([date_col, drug_col]).agg({
        quantity_col: 'sum',
        value_col: 'sum'
    }).reset_index()

    market_totals.columns = [date_col, drug_col, 'MARKET_TOTAL_DRUGS_PACK', 'MARKET_TOTAL_DRUGS_REVENUE']

    return market_totals


def process_single_inn(
    df_inn: pd.DataFrame,
    inn_id: int,
    client_id: int
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Обробити один INN: gap filling + aggregation + NOTSOLD + MARKET_TOTALS + statistics.

    Як в оригінальному проекті (01_05_market_preparation.ipynb):
    1. Gap filling
    2. Weekly aggregation
    3. Розрахунок NOTSOLD_PERCENT для TARGET
    4. Розрахунок MARKET_TOTALS з COMPETITORS
    5. Об'єднання: TARGET + NOTSOLD + MARKET_TOTALS

    Args:
        df_inn: Датафрейм одного INN
        inn_id: ID INN групи
        client_id: ID цільової аптеки

    Returns:
        Tuple[final_df, stats_df]: Фінальні дані (тільки TARGET) та статистика
    """
    # Gap filling (додаємо INN_ID до categorical для forward fill)
    categorical_with_inn = CATEGORICAL_COLUMNS + ['INN_ID']
    df_filled = fill_gaps(
        df_inn,
        group_cols=['PHARM_ID', 'DRUGS_ID'],
        date_col='Date',
        value_cols=['Q', 'V'],
        categorical_cols=categorical_with_inn,
        show_progress=False
    )

    # Weekly aggregation (вже по тижнях після gap filling)
    df_aggregated = aggregate_weekly(
        df_filled,
        group_cols=['PHARM_ID', 'DRUGS_ID', 'Date'],
        sum_cols=['Q', 'V'],
        first_cols=['DRUGS_NAME', 'INN_NAME', 'INN_ID', 'NFC1_ID', 'NFC_ID']
    )

    # =========================================
    # Розділення на Target / Competitors
    # =========================================
    df_target = df_aggregated[df_aggregated['PHARM_ID'] == client_id].copy()
    df_competitors = df_aggregated[df_aggregated['PHARM_ID'] != client_id].copy()

    # =========================================
    # Розрахунок NOTSOLD_PERCENT (для TARGET)
    # =========================================
    notsold_stats = calculate_notsold_percent(
        df_target,
        group_cols=['PHARM_ID', 'DRUGS_ID'],
        quantity_col='Q'
    )

    # Додаємо NOTSOLD_PERCENT до target даних
    df_target = df_target.merge(
        notsold_stats[['PHARM_ID', 'DRUGS_ID', 'NOTSOLD_PERCENT']],
        on=['PHARM_ID', 'DRUGS_ID'],
        how='left'
    )

    # =========================================
    # Фільтрація за NOTSOLD_PERCENT (як в оригіналі)
    # =========================================
    # Препарати що проходять фільтр
    valid_drugs = notsold_stats[
        (notsold_stats['NOTSOLD_PERCENT'] >= MIN_NOTSOLD_PERCENT) &
        (notsold_stats['NOTSOLD_PERCENT'] <= MAX_NOTSOLD_PERCENT)
    ]['DRUGS_ID'].unique()

    # Фільтруємо target та competitors
    df_target = df_target[df_target['DRUGS_ID'].isin(valid_drugs)].copy()
    df_competitors = df_competitors[df_competitors['DRUGS_ID'].isin(valid_drugs)].copy()

    # =========================================
    # Розрахунок MARKET_TOTALS (з COMPETITORS)
    # =========================================
    market_totals = calculate_market_totals(
        df_competitors,
        date_col='Date',
        drug_col='DRUGS_ID',
        quantity_col='Q',
        value_col='V'
    )

    # =========================================
    # Об'єднання TARGET + MARKET_TOTALS
    # =========================================
    df_final = df_target.merge(
        market_totals,
        on=['Date', 'DRUGS_ID'],
        how='left'
    )

    # Заповнюємо NaN в MARKET_TOTALS нулями
    df_final['MARKET_TOTAL_DRUGS_PACK'] = df_final['MARKET_TOTAL_DRUGS_PACK'].fillna(0)
    df_final['MARKET_TOTAL_DRUGS_REVENUE'] = df_final['MARKET_TOTAL_DRUGS_REVENUE'].fillna(0)

    # Статистика
    stats = calculate_inn_statistics(df_target, inn_id, client_id)

    return df_final, stats


def calculate_inn_statistics(
    df_target: pd.DataFrame,
    inn_id: int,
    client_id: int
) -> pd.DataFrame:
    """
    Розрахувати статистику per INN для цільової аптеки.

    Статистика:
        - CLIENT_ID, INN_ID, INN_NAME
        - DRUGS_ID, DRUGS_NAME
        - DATE_START, DATE_END, DATE_DIFF (в днях)
        - WEEKS_TOTAL (всього тижнів в даних)
        - WEEKS_WITH_SALES (тижнів з продажами Q > 0)
        - SALES_RATIO (частка тижнів з продажами, 0-1)
        - TOTAL_Q (загальна кількість)

    Args:
        df_target: Датафрейм цільової аптеки (тижневі дані після gap filling)
        inn_id: ID INN групи
        client_id: ID цільової аптеки

    Returns:
        pd.DataFrame: Статистика (один рядок per DRUGS_ID)
    """
    if df_target.empty:
        return pd.DataFrame()

    stats_list = []

    for drugs_id, df_drug in df_target.groupby('DRUGS_ID'):
        date_start = df_drug['Date'].min()
        date_end = df_drug['Date'].max()
        date_diff = (date_end - date_start).days + 1

        # Статистика по тижнях (дані вже тижневі після gap filling)
        weeks_total = len(df_drug)
        weeks_with_sales = (df_drug['Q'] > 0).sum()
        sales_ratio = round(weeks_with_sales / weeks_total, 3) if weeks_total > 0 else 0

        stats_list.append({
            'CLIENT_ID': client_id,
            'INN_ID': inn_id,
            'INN_NAME': df_drug['INN_NAME'].iloc[0] if 'INN_NAME' in df_drug.columns else '',
            'DRUGS_ID': drugs_id,
            'DRUGS_NAME': df_drug['DRUGS_NAME'].iloc[0] if 'DRUGS_NAME' in df_drug.columns else '',
            'DATE_START': date_start.strftime('%Y-%m-%d'),
            'DATE_END': date_end.strftime('%Y-%m-%d'),
            'DATE_DIFF': date_diff,
            'WEEKS_TOTAL': weeks_total,
            'WEEKS_WITH_SALES': weeks_with_sales,
            'SALES_RATIO': sales_ratio,
            'TOTAL_Q': df_drug['Q'].sum()
        })

    return pd.DataFrame(stats_list)


def process_market(client_id: int) -> Dict:
    """
    Повна обробка одного ринку.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict: Результати обробки
    """
    start_time = datetime.now()

    # Підготовка папок
    paths = ensure_aggregation_folders(client_id)

    # Завантаження даних
    df = load_and_prepare_data(client_id)

    # Отримати список INN
    inn_ids = df['INN_ID'].unique()
    print(f"\nОбробка {len(inn_ids)} INN груп...")

    all_stats = []
    results = {
        'client_id': client_id,
        'inn_count': len(inn_ids),
        'inn_processed': 0,
        'total_rows': 0,
        'files_created': []
    }

    for i, inn_id in enumerate(inn_ids):
        # Фільтрація по INN
        df_inn = df[df['INN_ID'] == inn_id].copy()

        # Обробка INN
        df_aggregated, stats_df = process_single_inn(df_inn, inn_id, client_id)

        # Зберегти агреговані дані
        output_file = paths['aggregation_folder'] / f"inn_{inn_id}_{client_id}.csv"
        df_aggregated.to_csv(output_file, index=False)
        results['files_created'].append(str(output_file))
        results['total_rows'] += len(df_aggregated)

        # Збираємо статистику для summary (без збереження per-INN файлів)
        if not stats_df.empty:
            all_stats.append(stats_df)

        results['inn_processed'] += 1

        # Прогрес
        if (i + 1) % 50 == 0 or (i + 1) == len(inn_ids):
            print(f"  Оброблено {i + 1}/{len(inn_ids)} INN")

    # Зберегти зведену статистику
    if all_stats:
        summary_df = pd.concat(all_stats, ignore_index=True)
        summary_file = paths['stats_folder'] / f"summary_{client_id}.csv"
        summary_df.to_csv(summary_file, index=False)
        results['files_created'].append(str(summary_file))

        # Додаткова агрегована статистика per INN
        inn_summary = summary_df.groupby('INN_ID').agg({
            'INN_NAME': 'first',
            'DRUGS_ID': 'nunique',
            'DATE_START': 'min',
            'DATE_END': 'max',
            'WEEKS_TOTAL': 'sum',
            'WEEKS_WITH_SALES': 'sum',
            'TOTAL_Q': 'sum'
        }).reset_index()
        inn_summary['AVG_SALES_RATIO'] = round(
            inn_summary['WEEKS_WITH_SALES'] / inn_summary['WEEKS_TOTAL'], 3
        )
        inn_summary.columns = [
            'INN_ID', 'INN_NAME', 'DRUGS_COUNT', 'DATE_START', 'DATE_END',
            'WEEKS_TOTAL', 'WEEKS_WITH_SALES', 'TOTAL_Q', 'AVG_SALES_RATIO'
        ]

        inn_summary_file = paths['stats_folder'] / f"inn_summary_{client_id}.csv"
        inn_summary.to_csv(inn_summary_file, index=False)
        results['files_created'].append(str(inn_summary_file))

    # Час виконання
    elapsed = (datetime.now() - start_time).total_seconds()
    results['elapsed_seconds'] = round(elapsed, 2)

    print(f"\n{'='*60}")
    print(f"ЗАВЕРШЕНО: CLIENT_ID = {client_id}")
    print(f"{'='*60}")
    print(f"  INN оброблено: {results['inn_processed']}")
    print(f"  Рядків створено: {results['total_rows']:,}")
    print(f"  Файлів створено: {len(results['files_created'])}")
    print(f"  Час: {elapsed:.1f} сек")

    return results


def process_all_markets() -> List[Dict]:
    """
    Обробити всі ринки з preprocessing результатів.

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
    print(f"ОБРОБКА ВСІХ РИНКІВ: {len(target_pharmacies)} ринків")
    print(f"{'#'*60}")

    all_results = []

    for i, client_id in enumerate(target_pharmacies):
        print(f"\n[{i+1}/{len(target_pharmacies)}] Ринок {client_id}")

        try:
            result = process_market(client_id)
            all_results.append(result)
        except Exception as e:
            print(f"ПОМИЛКА при обробці ринку {client_id}: {e}")
            all_results.append({
                'client_id': client_id,
                'error': str(e)
            })

    # Підсумок
    print(f"\n{'#'*60}")
    print(f"ПІДСУМОК")
    print(f"{'#'*60}")

    successful = [r for r in all_results if 'error' not in r]
    failed = [r for r in all_results if 'error' in r]

    print(f"Успішно: {len(successful)}/{len(target_pharmacies)}")
    print(f"З помилками: {len(failed)}")

    if successful:
        total_rows = sum(r.get('total_rows', 0) for r in successful)
        total_time = sum(r.get('elapsed_seconds', 0) for r in successful)
        print(f"Загалом рядків: {total_rows:,}")
        print(f"Загалом часу: {total_time:.1f} сек")

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
        description='Агрегація даних per market (Phase 1, Step 1)'
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
        process_market(args.market_id)
    else:
        # За замовчуванням показати help
        parser.print_help()
        print("\nПриклади:")
        print("  python exec_scripts/01_did_processing/02_01_data_aggregation.py --market_id 28670")
        print("  python exec_scripts/01_did_processing/02_01_data_aggregation.py --all")


if __name__ == "__main__":
    main()
