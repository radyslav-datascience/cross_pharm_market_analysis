# =============================================================================
# PATHS CONFIGURATION - cross_pharm_market_analysis
# =============================================================================
# Файл: project_core/data_config/paths_config.py
# Дата: 2026-01-28
# Опис: Централізована конфігурація шляхів для мульти-ринкового аналізу
# =============================================================================

"""
Конфігурація шляхів для проекту cross_pharm_market_analysis.

Особливості:
    - Використовує pathlib для крос-платформної сумісності
    - Підтримує динамічні шляхи для per-market обробки
    - Завантажує списки з preprocessing результатів

Використання:
    from project_core.data_config.paths_config import (
        PROJECT_ROOT,
        RAW_DATA_PATH,
        get_market_path,
        load_target_pharmacies
    )
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional


# =============================================================================
# BASE PATHS
# =============================================================================

# Визначення кореневої папки проекту
# Працює незалежно від того, звідки імпортується модуль
_CURRENT_FILE = Path(__file__).resolve()
PROJECT_CORE_PATH = _CURRENT_FILE.parent.parent  # project_core/
PROJECT_ROOT = PROJECT_CORE_PATH.parent          # cross_pharm_market_analysis/

# Основні папки
DATA_PATH = PROJECT_ROOT / "data"
RAW_DATA_PATH = DATA_PATH / "raw"
PROCESSED_DATA_PATH = DATA_PATH / "processed_data"
RESULTS_PATH = PROJECT_ROOT / "results"
EXEC_SCRIPTS_PATH = PROJECT_ROOT / "exec_scripts"

# =============================================================================
# PREPROCESSING RESULTS
# =============================================================================

PREPROC_RESULTS_PATH = PROCESSED_DATA_PATH / "00_preproc_results"

# Файли preprocessing
PREPROC_FILES = {
    'target_pharmacies': PREPROC_RESULTS_PATH / "target_pharmacies_list.csv",
    'inn_list': PREPROC_RESULTS_PATH / "inn_list.csv",
    'nfc1_list': PREPROC_RESULTS_PATH / "nfc1_list.csv",
    'nfc2_list': PREPROC_RESULTS_PATH / "nfc2_list.csv",
    'drugs_list': PREPROC_RESULTS_PATH / "drugs_list.csv",
    'markets_statistics': PREPROC_RESULTS_PATH / "markets_statistics.csv"
}

# =============================================================================
# PER-MARKET PROCESSING PATHS
# =============================================================================

# Основні папки обробки (узгоджена структура)
PER_MARKET_FOLDER = "01_per_market"
CROSS_MARKET_FOLDER = "02_cross_market"


def get_market_folder(client_id: int) -> Path:
    """
    Отримати папку для конкретного ринку.

    Args:
        client_id: ID цільової аптеки (CLIENT_ID)

    Returns:
        Path: Шлях до папки ринку
    """
    return PROCESSED_DATA_PATH / PER_MARKET_FOLDER / str(client_id)


def get_market_raw_file(client_id: int) -> Path:
    """
    Отримати шлях до raw файлу ринку.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Path: Шлях до Rd2_{client_id}.csv
    """
    return RAW_DATA_PATH / f"Rd2_{client_id}.csv"


def get_market_paths(client_id: int) -> Dict[str, Path]:
    """
    Отримати всі шляхи для обробки конкретного ринку.

    Структура папок (узгоджена):
        01_per_market/{CLIENT_ID}/
        ├── 01_aggregation_{CLIENT_ID}/
        ├── 02_stockout_{CLIENT_ID}/
        ├── 03_did_analysis_{CLIENT_ID}/
        └── 04_substitute_shares_{CLIENT_ID}/

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict: Словник з шляхами для етапів обробки
    """
    market_folder = get_market_folder(client_id)

    return {
        'raw_file': get_market_raw_file(client_id),
        'market_folder': market_folder,

        # Етап 1: Агрегація
        'aggregation': market_folder / f"01_aggregation_{client_id}",

        # Етап 2: Stock-out detection
        'stockout': market_folder / f"02_stockout_{client_id}",

        # Етап 3: DiD analysis
        'did_analysis': market_folder / f"03_did_analysis_{client_id}",

        # Етап 4: Substitute shares
        'substitute_shares': market_folder / f"04_substitute_shares_{client_id}"
    }


# =============================================================================
# CROSS-MARKET AGGREGATION PATHS
# =============================================================================

CROSS_MARKET_PATH = PROCESSED_DATA_PATH / CROSS_MARKET_FOLDER

CROSS_MARKET_PATHS = {
    'collected_results': CROSS_MARKET_PATH / "01_collected_results",
    'coverage_analysis': CROSS_MARKET_PATH / "02_coverage_analysis",
    'statistical_analysis': CROSS_MARKET_PATH / "03_statistical_analysis",
    'final_classification': CROSS_MARKET_PATH / "04_final_classification"
}

# =============================================================================
# RESULTS PATHS
# =============================================================================

RESULTS_PATHS = {
    'excel_reports': RESULTS_PATH / "excel_reports",
    'graphs': RESULTS_PATH / "graphs",
    'summary': RESULTS_PATH / "summary"
}

# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

def load_target_pharmacies() -> List[int]:
    """
    Завантажити список цільових аптек з preprocessing результатів.

    Returns:
        List[int]: Список CLIENT_ID

    Raises:
        FileNotFoundError: Якщо файл не знайдено
    """
    file_path = PREPROC_FILES['target_pharmacies']

    if not file_path.exists():
        raise FileNotFoundError(
            f"Файл {file_path} не знайдено. "
            f"Спочатку виконайте preprocessing: python exec_scripts/01_did_processing/01_preproc.py"
        )

    df = pd.read_csv(file_path)
    return df['CLIENT_ID'].tolist()


def load_inn_list() -> Dict[int, str]:
    """
    Завантажити список INN груп з preprocessing результатів.

    Returns:
        Dict[int, str]: Словник {INN_ID: INN_NAME}

    Raises:
        FileNotFoundError: Якщо файл не знайдено
    """
    file_path = PREPROC_FILES['inn_list']

    if not file_path.exists():
        raise FileNotFoundError(
            f"Файл {file_path} не знайдено. "
            f"Спочатку виконайте preprocessing: python exec_scripts/01_did_processing/01_preproc.py"
        )

    df = pd.read_csv(file_path)
    return dict(zip(df['INN_ID'], df['INN_NAME']))


def load_markets_statistics() -> pd.DataFrame:
    """
    Завантажити статистику по ринках.

    Returns:
        pd.DataFrame: Статистика по всіх ринках

    Raises:
        FileNotFoundError: Якщо файл не знайдено
    """
    file_path = PREPROC_FILES['markets_statistics']

    if not file_path.exists():
        raise FileNotFoundError(
            f"Файл {file_path} не знайдено. "
            f"Спочатку виконайте preprocessing: python exec_scripts/01_did_processing/01_preproc.py"
        )

    return pd.read_csv(file_path)


def ensure_market_folders(client_id: int) -> Dict[str, Path]:
    """
    Створити всі необхідні папки для обробки ринку.

    Args:
        client_id: ID цільової аптеки

    Returns:
        Dict: Словник з шляхами (папки вже створені)
    """
    paths = get_market_paths(client_id)

    for key, path in paths.items():
        if key != 'raw_file':  # raw_file — це файл, не папка
            path.mkdir(parents=True, exist_ok=True)

    return paths


# =============================================================================
# FILE PATTERNS
# =============================================================================

RAW_FILE_PATTERN = "Rd2_*.csv"
CSV_SEPARATOR = ";"


# =============================================================================
# VALIDATION
# =============================================================================

def validate_paths() -> bool:
    """
    Валідація що всі базові шляхи існують.

    Returns:
        bool: True якщо валідація пройшла
    """
    required_paths = [
        PROJECT_ROOT,
        DATA_PATH,
        RAW_DATA_PATH
    ]

    for path in required_paths:
        if not path.exists():
            print(f"ПОМИЛКА: Шлях не існує: {path}")
            return False

    return True


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PATHS CONFIGURATION - cross_pharm_market_analysis")
    print("=" * 60)

    print(f"\nPROJECT_ROOT: {PROJECT_ROOT}")
    print(f"RAW_DATA_PATH: {RAW_DATA_PATH}")
    print(f"PROCESSED_DATA_PATH: {PROCESSED_DATA_PATH}")

    print(f"\nPREPROC_RESULTS_PATH: {PREPROC_RESULTS_PATH}")

    print("\nValidation:", "PASSED" if validate_paths() else "FAILED")

    # Спроба завантажити дані
    try:
        pharmacies = load_target_pharmacies()
        print(f"\nЦільові аптеки ({len(pharmacies)}): {pharmacies[:5]}...")

        inn_groups = load_inn_list()
        print(f"INN груп: {len(inn_groups)}")

        # Приклад шляхів для першого ринку
        if pharmacies:
            paths = get_market_paths(pharmacies[0])
            print(f"\nШляхи для ринку {pharmacies[0]}:")
            for key, path in paths.items():
                print(f"  {key}: {path}")

    except FileNotFoundError as e:
        print(f"\n{e}")
