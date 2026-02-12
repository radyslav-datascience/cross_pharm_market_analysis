# =============================================================================
# PREPROCESSING SCRIPT - cross_pharm_market_analysis
# =============================================================================
# Файл: exec_scripts/01_did_processing/01_preproc.py
# Дата: 2026-01-31
# Опис: Первинна обробка вхідних даних - збір списків та статистики по ринках
# =============================================================================

"""
Preprocessing скрипт для мульти-ринкового аналізу.

Функціонал:
    1. Сканування raw файлів Rd2_{CLIENT_ID}.csv
    2. Збір унікальних значень (INN, NFC, препарати)
    3. Генерація статистики per market
    4. Збереження результатів для подальших етапів

Вхід:
    data/raw/Rd2_*.csv - файли локальних ринків

Вихід (data/processed_data/00_preproc_results/):
    - target_pharmacies_list.csv - список ID цільових аптек
    - inn_list.csv - унікальні INN_ID + INN_NAME
    - nfc1_list.csv - унікальні NFC1_ID
    - nfc2_list.csv - унікальні NFC2_ID
    - drugs_list.csv - унікальні DRUGS_ID + DRUGS_NAME
    - markets_statistics.csv - статистика по кожному локальному ринку

Використання:
    python exec_scripts/01_did_processing/01_preproc.py

Див. документацію:
    docs/01_did_processing/01_0_PREPROCESSING.md
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict

import pandas as pd

# Додаємо project root до sys.path для імпортів
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Імпорти з project_core
from project_core.data_config.paths_config import (
    RAW_DATA_PATH,
    PREPROC_RESULTS_PATH,
    RAW_FILE_PATTERN,
    CSV_SEPARATOR
)
from project_core.utility_functions.etl_utils import parse_period_id


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_date(dt: datetime) -> str:
    """Форматування дати в DD.MM.YYYY."""
    return dt.strftime("%d.%m.%Y")


def calculate_weeks(start_date: datetime, end_date: datetime) -> int:
    """Розрахунок кількості повних тижнів між датами."""
    delta = end_date - start_date
    return delta.days // 7


# =============================================================================
# PROCESSING FUNCTIONS
# =============================================================================

def process_single_file(file_path: Path) -> Dict:
    """
    Обробка одного CSV файлу - збір статистики та унікальних значень.

    Args:
        file_path: Шлях до CSV файлу

    Returns:
        dict: Словник зі статистикою та унікальними значеннями
    """
    print(f"  Обробка: {file_path.name}")

    # Завантаження даних
    df = pd.read_csv(file_path, sep=CSV_SEPARATOR)

    # Отримання CLIENT_ID (цільова аптека)
    client_id = df['CLIENT_ID'].iloc[0]

    # Парсинг дат з PERIOD_ID (використовуємо функцію з project_core)
    period_ids = df['PERIOD_ID'].unique()
    dates = [parse_period_id(pid) for pid in period_ids]
    data_start = min(dates)
    data_end = max(dates)

    # Статистика
    all_org_ids = df['ORG_ID'].unique()
    competitors_count = len(all_org_ids) - 1  # Мінус цільова аптека

    drugs_count = df['DRUGS_ID'].nunique()
    inn_count = df['INN_ID'].nunique()
    records_count = len(df)

    days_range = (data_end - data_start).days
    weeks_range = calculate_weeks(data_start, data_end)

    # Унікальні значення для агрегації
    inn_data = df[['INN_ID', 'INN']].drop_duplicates()
    nfc1_data = df[['NFC Code (1)']].drop_duplicates()
    nfc2_data = df[['NFC Code (2)']].drop_duplicates()
    drugs_data = df[['DRUGS_ID', 'Full medication name']].drop_duplicates()

    return {
        'statistics': {
            'CLIENT_ID': client_id,
            'FILE_NAME': file_path.name,
            'COMPETITORS_COUNT': competitors_count,
            'DATA_START': format_date(data_start),
            'DATA_END': format_date(data_end),
            'DAYS_RANGE': days_range,
            'WEEKS_RANGE': weeks_range,
            'DRUGS_COUNT': drugs_count,
            'INN_COUNT': inn_count,
            'RECORDS_COUNT': records_count
        },
        'inn': inn_data,
        'nfc1': nfc1_data,
        'nfc2': nfc2_data,
        'drugs': drugs_data,
        'client_id': client_id
    }


def run_preprocessing() -> pd.DataFrame:
    """
    Основна функція preprocessing.

    Сканує всі CSV файли, збирає статистику та унікальні значення,
    зберігає результати.

    Returns:
        pd.DataFrame: Статистика по ринках

    Raises:
        FileNotFoundError: Якщо папка raw або файли не знайдені
    """
    print("=" * 60)
    print("PREPROCESSING - cross_pharm_market_analysis")
    print("=" * 60)

    # Перевірка існування папки raw
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"Папка {RAW_DATA_PATH} не існує!")

    # Створення вихідної папки
    PREPROC_RESULTS_PATH.mkdir(parents=True, exist_ok=True)

    # Пошук файлів (використовуємо Path.glob замість glob модуля)
    files = sorted(RAW_DATA_PATH.glob(RAW_FILE_PATTERN))

    if not files:
        raise FileNotFoundError(
            f"Файли {RAW_FILE_PATTERN} не знайдено в {RAW_DATA_PATH}"
        )

    print(f"\nЗнайдено файлів: {len(files)}")
    print("-" * 60)

    # Обробка файлів
    all_statistics = []
    all_client_ids = []
    all_inn = []
    all_nfc1 = []
    all_nfc2 = []
    all_drugs = []

    for file_path in files:
        result = process_single_file(file_path)

        all_statistics.append(result['statistics'])
        all_client_ids.append(result['client_id'])
        all_inn.append(result['inn'])
        all_nfc1.append(result['nfc1'])
        all_nfc2.append(result['nfc2'])
        all_drugs.append(result['drugs'])

    print("-" * 60)
    print("\nАгрегація результатів...")

    # 1. target_pharmacies_list.csv
    df_pharmacies = pd.DataFrame({'CLIENT_ID': all_client_ids})
    df_pharmacies = df_pharmacies.drop_duplicates().sort_values('CLIENT_ID')
    pharmacies_path = PREPROC_RESULTS_PATH / "target_pharmacies_list.csv"
    df_pharmacies.to_csv(pharmacies_path, index=False)
    print(f"  Збережено: {pharmacies_path.name} ({len(df_pharmacies)} записів)")

    # 2. inn_list.csv
    df_inn = pd.concat(all_inn, ignore_index=True).drop_duplicates()
    df_inn = df_inn.rename(columns={'INN': 'INN_NAME'})
    df_inn = df_inn.sort_values('INN_ID')
    inn_path = PREPROC_RESULTS_PATH / "inn_list.csv"
    df_inn.to_csv(inn_path, index=False)
    print(f"  Збережено: {inn_path.name} ({len(df_inn)} записів)")

    # 3. nfc1_list.csv
    df_nfc1 = pd.concat(all_nfc1, ignore_index=True).drop_duplicates()
    df_nfc1 = df_nfc1.rename(columns={'NFC Code (1)': 'NFC1_ID'})
    df_nfc1 = df_nfc1.sort_values('NFC1_ID')
    nfc1_path = PREPROC_RESULTS_PATH / "nfc1_list.csv"
    df_nfc1.to_csv(nfc1_path, index=False)
    print(f"  Збережено: {nfc1_path.name} ({len(df_nfc1)} записів)")

    # 4. nfc2_list.csv
    df_nfc2 = pd.concat(all_nfc2, ignore_index=True).drop_duplicates()
    df_nfc2 = df_nfc2.rename(columns={'NFC Code (2)': 'NFC2_ID'})
    df_nfc2 = df_nfc2.sort_values('NFC2_ID')
    nfc2_path = PREPROC_RESULTS_PATH / "nfc2_list.csv"
    df_nfc2.to_csv(nfc2_path, index=False)
    print(f"  Збережено: {nfc2_path.name} ({len(df_nfc2)} записів)")

    # 5. drugs_list.csv
    df_drugs = pd.concat(all_drugs, ignore_index=True).drop_duplicates()
    df_drugs = df_drugs.rename(columns={'Full medication name': 'DRUGS_NAME'})
    df_drugs = df_drugs.sort_values('DRUGS_ID')
    drugs_path = PREPROC_RESULTS_PATH / "drugs_list.csv"
    df_drugs.to_csv(drugs_path, index=False)
    print(f"  Збережено: {drugs_path.name} ({len(df_drugs)} записів)")

    # 6. markets_statistics.csv
    df_stats = pd.DataFrame(all_statistics)
    stats_path = PREPROC_RESULTS_PATH / "markets_statistics.csv"
    df_stats.to_csv(stats_path, index=False)
    print(f"  Збережено: {stats_path.name} ({len(df_stats)} записів)")

    # Підсумок
    print("\n" + "=" * 60)
    print("PREPROCESSING ЗАВЕРШЕНО")
    print("=" * 60)
    print(f"\nОброблено ринків: {len(files)}")
    print(f"Цільових аптек: {len(df_pharmacies)}")
    print(f"Унікальних INN: {len(df_inn)}")
    print(f"Унікальних NFC1: {len(df_nfc1)}")
    print(f"Унікальних NFC2: {len(df_nfc2)}")
    print(f"Унікальних препаратів: {len(df_drugs)}")
    print(f"\nРезультати збережено в: {PREPROC_RESULTS_PATH}")

    return df_stats


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Головна функція CLI."""
    try:
        run_preprocessing()
    except FileNotFoundError as e:
        print(f"ПОМИЛКА: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"НЕОЧІКУВАНА ПОМИЛКА: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
