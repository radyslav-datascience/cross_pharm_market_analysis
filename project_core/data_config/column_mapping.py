# =============================================================================
# COLUMN MAPPING - cross_pharm_market_analysis
# =============================================================================
# Файл: project_core/data_config/column_mapping.py
# Дата: 2026-01-28
# Опис: Маппінг та стандартизація колонок CSV файлів
# =============================================================================

"""
Конфігурація маппінгу колонок для проекту cross_pharm_market_analysis.

Визначає:
    - Перейменування колонок з raw даних
    - Стандартні назви колонок
    - Типи даних колонок

Використання:
    from project_core.data_config.column_mapping import (
        COLUMN_RENAME_MAP,
        REQUIRED_COLUMNS,
        get_standard_columns
    )
"""

from typing import Dict, List


# =============================================================================
# COLUMN RENAMING
# =============================================================================

# Перейменування колонок з raw файлів
COLUMN_RENAME_MAP: Dict[str, str] = {
    'ORG_ID': 'PHARM_ID',                      # ID аптеки-продавця
    'INN': 'INN_NAME',                         # Назва INN групи
    'Full medication name': 'DRUGS_NAME',      # Повна назва препарату
    'NFC Code (1)': 'NFC1_ID',                 # Форма випуску (рівень 1)
    'NFC Code (2)': 'NFC_ID'                   # Форма випуску (рівень 2)
}


# =============================================================================
# STANDARD COLUMN NAMES
# =============================================================================

# Колонки що мають бути в raw файлах
RAW_REQUIRED_COLUMNS: List[str] = [
    'CLIENT_ID',        # ID цільової аптеки (з якої зроблено вибірку)
    'ORG_ID',           # ID аптеки-продавця
    'PERIOD_ID',        # Період (формат YYYYNNNNN)
    'DRUGS_ID',         # ID препарату (Morion)
    'INN_ID',           # ID INN групи
    'INN',              # Назва INN групи
    'Q',                # Кількість упаковок
    'V',                # Виручка
    'Full medication name',  # Назва препарату
    'NFC Code (1)',     # Форма випуску (рівень 1)
    'NFC Code (2)'      # Форма випуску (рівень 2)
]

# Колонки після перейменування
STANDARD_COLUMNS: List[str] = [
    'CLIENT_ID',
    'PHARM_ID',         # Renamed from ORG_ID
    'PERIOD_ID',
    'DRUGS_ID',
    'INN_ID',
    'INN_NAME',         # Renamed from INN
    'Q',
    'V',
    'DRUGS_NAME',       # Renamed from Full medication name
    'NFC1_ID',          # Renamed from NFC Code (1)
    'NFC_ID'            # Renamed from NFC Code (2)
]

# Колонки для агрегації
AGGREGATION_COLUMNS: List[str] = [
    'PHARM_ID',
    'DRUGS_ID',
    'Date',             # Додається при парсингу PERIOD_ID
    'Q',
    'V',
    'DRUGS_NAME',
    'INN_ID',
    'INN_NAME',
    'NFC1_ID',
    'NFC_ID'
]

# ID колонки (для групування)
ID_COLUMNS: List[str] = [
    'CLIENT_ID',
    'PHARM_ID',
    'DRUGS_ID',
    'INN_ID'
]

# Числові колонки
NUMERIC_COLUMNS: List[str] = [
    'Q',
    'V'
]

# Категоріальні колонки (для forward fill)
CATEGORICAL_COLUMNS: List[str] = [
    'DRUGS_NAME',
    'INN_NAME',
    'NFC1_ID',
    'NFC_ID'
]


# =============================================================================
# COLUMN DATA TYPES
# =============================================================================

# Очікувані типи даних
COLUMN_DTYPES: Dict[str, str] = {
    'CLIENT_ID': 'int64',
    'PHARM_ID': 'int64',
    'PERIOD_ID': 'int64',
    'DRUGS_ID': 'int64',
    'INN_ID': 'int64',
    'Q': 'float64',
    'V': 'float64',
    'INN_NAME': 'str',
    'DRUGS_NAME': 'str',
    'NFC1_ID': 'str',
    'NFC_ID': 'str'
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_standard_columns() -> List[str]:
    """
    Отримати список стандартних колонок.

    Returns:
        List[str]: Стандартні колонки
    """
    return STANDARD_COLUMNS.copy()


def get_rename_map() -> Dict[str, str]:
    """
    Отримати маппінг для перейменування колонок.

    Returns:
        Dict[str, str]: {old_name: new_name}
    """
    return COLUMN_RENAME_MAP.copy()


def validate_raw_columns(columns: List[str]) -> List[str]:
    """
    Перевірити наявність необхідних колонок у raw файлі.

    Args:
        columns: Список колонок датафрейму

    Returns:
        List[str]: Список відсутніх колонок (порожній якщо все OK)
    """
    missing = []
    for col in RAW_REQUIRED_COLUMNS:
        if col not in columns:
            missing.append(col)
    return missing


def validate_standard_columns(columns: List[str]) -> List[str]:
    """
    Перевірити наявність стандартних колонок після перейменування.

    Args:
        columns: Список колонок датафрейму

    Returns:
        List[str]: Список відсутніх колонок
    """
    missing = []
    for col in STANDARD_COLUMNS:
        if col not in columns:
            missing.append(col)
    return missing


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("COLUMN MAPPING - cross_pharm_market_analysis")
    print("=" * 60)

    print("\nCOLUMN_RENAME_MAP:")
    for old, new in COLUMN_RENAME_MAP.items():
        print(f"  {old} → {new}")

    print(f"\nRAW_REQUIRED_COLUMNS ({len(RAW_REQUIRED_COLUMNS)}):")
    for col in RAW_REQUIRED_COLUMNS:
        print(f"  - {col}")

    print(f"\nSTANDARD_COLUMNS ({len(STANDARD_COLUMNS)}):")
    for col in STANDARD_COLUMNS:
        print(f"  - {col}")

    print(f"\nNUMERIC_COLUMNS: {NUMERIC_COLUMNS}")
    print(f"ID_COLUMNS: {ID_COLUMNS}")
