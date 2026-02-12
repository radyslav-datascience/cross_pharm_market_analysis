# =============================================================================
# ETL UTILITIES - cross_pharm_market_analysis
# =============================================================================
# Файл: project_core/utility_functions/etl_utils.py
# Дата: 2026-01-28
# Опис: Утиліти для Extract-Transform-Load операцій
# =============================================================================

"""
ETL утиліти для проекту cross_pharm_market_analysis.

Функції:
    - load_raw_data(): Завантаження та базова трансформація
    - parse_period_id(): Парсинг PERIOD_ID → datetime
    - fill_gaps(): GAP FILLING для часових рядів
    - calculate_notsold(): Розрахунок NOTSOLD_PERCENT
    - convert_numeric_columns(): Конвертація Q, V у float

Використання:
    from project_core.utility_functions.etl_utils import (
        load_raw_data,
        parse_period_id,
        fill_gaps
    )
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from pathlib import Path


# =============================================================================
# DATA LOADING
# =============================================================================

def load_raw_data(
    file_path: str | Path,
    sep: str = ';'
) -> pd.DataFrame:
    """
    Завантаження сирих даних з CSV файлу.

    Args:
        file_path: Шлях до CSV файлу
        sep: Роздільник (за замовчуванням ';')

    Returns:
        pd.DataFrame: Завантажений датафрейм
    """
    df = pd.read_csv(file_path, sep=sep)
    print(f"Завантажено {len(df):,} рядків, {len(df.columns)} колонок")
    return df


def convert_numeric_columns(
    df: pd.DataFrame,
    columns: List[str] = ['Q', 'V']
) -> pd.DataFrame:
    """
    Конвертація колонок з рядків (з комою) у float.

    Args:
        df: Вхідний датафрейм
        columns: Список колонок для конвертації

    Returns:
        pd.DataFrame: Датафрейм з конвертованими колонками
    """
    df = df.copy()
    for col in columns:
        if col in df.columns:
            # Заміна коми на крапку та конвертація у float
            df[col] = df[col].astype(str).str.replace(',', '.').astype(float)
            print(f"  Конвертовано {col}: str → float")
    return df


def rename_columns(
    df: pd.DataFrame,
    rename_map: Dict[str, str]
) -> pd.DataFrame:
    """
    Перейменування колонок за маппінгом.

    Args:
        df: Вхідний датафрейм
        rename_map: Словник {old_name: new_name}

    Returns:
        pd.DataFrame: Датафрейм з перейменованими колонками
    """
    df = df.copy()
    # Перейменовуємо тільки колонки, які існують
    existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=existing_renames)
    print(f"  Перейменовано {len(existing_renames)} колонок")
    return df


# =============================================================================
# DATE PARSING
# =============================================================================

def align_to_monday(date: datetime) -> datetime:
    """
    Вирівнює дату до понеділка того тижня.

    Args:
        date: Вхідна дата

    Returns:
        datetime: Понеділок того самого тижня
    """
    # weekday(): понеділок=0, неділя=6
    days_since_monday = date.weekday()
    return date - timedelta(days=days_since_monday)


def parse_period_id(period_id: int) -> datetime:
    """
    Парсинг PERIOD_ID у datetime.

    Формат PERIOD_ID: YYYYNNNNN
    - YYYY = рік
    - NNNNN = week_day_code (ділимо на 7 → тиждень, залишок → день)

    Args:
        period_id: Період у форматі YYYYNNNNN (int або str)

    Returns:
        datetime: Дата

    Example:
        >>> parse_period_id(202400305)
        datetime(2024, 11, 1)
    """
    period_str = str(int(period_id))
    year = int(period_str[:4])
    week_day_code = int(period_str[4:])

    # Обчислити тиждень і день
    week = week_day_code // 7
    day_of_week = week_day_code % 7

    # Створити дату: перший день року + тижні + дні
    first_day = datetime(year, 1, 1)
    target_date = first_day + timedelta(weeks=week, days=day_of_week)

    return target_date


def parse_period_id_series(series: pd.Series) -> pd.Series:
    """
    Парсинг серії PERIOD_ID у datetime.

    Args:
        series: pd.Series з PERIOD_ID

    Returns:
        pd.Series: Серія datetime
    """
    return series.apply(parse_period_id)


def add_date_column(
    df: pd.DataFrame,
    period_col: str = 'PERIOD_ID',
    date_col: str = 'Date',
    align_monday: bool = True
) -> pd.DataFrame:
    """
    Додавання колонки Date на основі PERIOD_ID.

    Args:
        df: Вхідний датафрейм
        period_col: Назва колонки з PERIOD_ID
        date_col: Назва нової колонки для дати
        align_monday: Вирівнювати дати по понеділках (за замовчуванням True)

    Returns:
        pd.DataFrame: Датафрейм з новою колонкою Date
    """
    df = df.copy()
    df[date_col] = parse_period_id_series(df[period_col])

    if align_monday:
        df[date_col] = df[date_col].apply(align_to_monday)
        print(f"  Створено колонку {date_col} з {period_col} (вирівняно по понеділках)")
    else:
        print(f"  Створено колонку {date_col} з {period_col}")

    return df


# =============================================================================
# GAP FILLING (КРИТИЧНО ВАЖЛИВО!)
# =============================================================================

def fill_gaps_for_group(
    group: pd.DataFrame,
    date_col: str = 'Date',
    value_cols: List[str] = ['Q', 'V'],
    id_cols: List[str] = ['PHARM_ID', 'DRUGS_ID'],
    categorical_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Заповнення пропущених дат для однієї групи (PHARM_ID, DRUGS_ID).

    КРИТИЧНО: Без цього кроку stock-out events будуть невидимі!

    Args:
        group: Датафрейм однієї групи
        date_col: Назва колонки з датою
        value_cols: Колонки для заповнення нулями
        id_cols: Колонки-ідентифікатори
        categorical_cols: Категоріальні колонки для forward fill

    Returns:
        pd.DataFrame: Датафрейм з заповненими пропусками
    """
    if categorical_cols is None:
        categorical_cols = ['DRUGS_NAME', 'INN_NAME', 'INN_ID', 'NFC1_ID', 'NFC_ID']

    # Спочатку агрегуємо дублікати по даті (якщо є кілька записів на одну дату)
    existing_value_cols = [c for c in value_cols if c in group.columns]
    existing_cat_cols = [c for c in categorical_cols if c in group.columns]
    existing_id_cols = [c for c in id_cols if c in group.columns]

    agg_dict = {col: 'sum' for col in existing_value_cols}
    agg_dict.update({col: 'first' for col in existing_cat_cols})
    agg_dict.update({col: 'first' for col in existing_id_cols})

    if group[date_col].duplicated().any():
        group = group.groupby(date_col).agg(agg_dict).reset_index()

    # Визначаємо діапазон дат
    min_date = group[date_col].min()
    max_date = group[date_col].max()

    # Створюємо повний тижневий range з тим же днем тижня що і min_date
    # Використовуємо 7-денний інтервал замість W-MON
    full_date_range = pd.date_range(start=min_date, end=max_date, freq='7D')

    # Reindex на повний range
    group_indexed = group.set_index(date_col)
    group_reindexed = group_indexed.reindex(full_date_range)

    # Заповнюємо числові колонки нулями
    for col in existing_value_cols:
        group_reindexed[col] = group_reindexed[col].fillna(0)

    # Forward/backward fill для категоріальних колонок
    if existing_cat_cols:
        group_reindexed[existing_cat_cols] = group_reindexed[existing_cat_cols].ffill().bfill()

    # Відновлюємо ID колонки
    for col in existing_id_cols:
        if col in group.columns:
            group_reindexed[col] = group[col].iloc[0]

    # Повертаємо індекс як колонку
    result = group_reindexed.reset_index().rename(columns={'index': date_col})

    return result


def fill_gaps(
    df: pd.DataFrame,
    group_cols: List[str] = ['PHARM_ID', 'DRUGS_ID'],
    date_col: str = 'Date',
    value_cols: List[str] = ['Q', 'V'],
    categorical_cols: Optional[List[str]] = None,
    show_progress: bool = True
) -> pd.DataFrame:
    """
    GAP FILLING для всього датафрейму.

    Заповнює пропущені тижні нулями для кожної пари (PHARM_ID, DRUGS_ID).

    Args:
        df: Вхідний датафрейм
        group_cols: Колонки для групування
        date_col: Назва колонки з датою
        value_cols: Колонки для заповнення нулями
        categorical_cols: Категоріальні колонки для forward fill
        show_progress: Показувати прогрес

    Returns:
        pd.DataFrame: Датафрейм з заповненими пропусками
    """
    if categorical_cols is None:
        categorical_cols = ['DRUGS_NAME', 'INN_NAME', 'INN_ID', 'NFC1_ID', 'NFC_ID']

    result_frames = []
    groups = df.groupby(group_cols)
    total_groups = len(groups)

    if show_progress:
        print(f"GAP FILLING для {total_groups:,} груп...")

    for i, (group_keys, group_df) in enumerate(groups):
        filled = fill_gaps_for_group(
            group_df,
            date_col=date_col,
            value_cols=value_cols,
            id_cols=group_cols,
            categorical_cols=categorical_cols
        )
        result_frames.append(filled)

        # Прогрес кожні 1000 груп
        if show_progress and (i + 1) % 1000 == 0:
            print(f"  Оброблено {i + 1:,} / {total_groups:,} груп")

    result = pd.concat(result_frames, ignore_index=True)

    if show_progress:
        added_rows = len(result) - len(df)
        print(f"  Додано {added_rows:,} рядків (пропущені тижні)")

    return result


# =============================================================================
# NOTSOLD ANALYSIS
# =============================================================================

def calculate_notsold_percent(
    df: pd.DataFrame,
    group_cols: List[str] = ['PHARM_ID', 'DRUGS_ID'],
    quantity_col: str = 'Q'
) -> pd.DataFrame:
    """
    Розрахунок NOTSOLD_PERCENT для кожної групи.

    NOTSOLD_PERCENT = (тижні з Q=0) / (всього тижнів)

    Args:
        df: Вхідний датафрейм (після GAP FILLING!)
        group_cols: Колонки для групування
        quantity_col: Колонка з кількістю

    Returns:
        pd.DataFrame: Датафрейм з колонкою NOTSOLD_PERCENT
    """
    notsold_stats = df.groupby(group_cols).apply(
        lambda x: pd.Series({
            'total_weeks': len(x),
            'zero_weeks': (x[quantity_col] == 0).sum()
        })
    ).reset_index()

    notsold_stats['NOTSOLD_PERCENT'] = (
        notsold_stats['zero_weeks'] / notsold_stats['total_weeks']
    )

    print(f"Розраховано NOTSOLD_PERCENT для {len(notsold_stats):,} груп")
    print(f"  Середній NOTSOLD: {notsold_stats['NOTSOLD_PERCENT'].mean():.1%}")

    return notsold_stats


def filter_by_notsold(
    df: pd.DataFrame,
    notsold_stats: pd.DataFrame,
    min_notsold: float = 0.20,
    max_notsold: float = 0.95,
    group_cols: List[str] = ['PHARM_ID', 'DRUGS_ID']
) -> pd.DataFrame:
    """
    Фільтрація даних за NOTSOLD_PERCENT.

    Args:
        df: Вхідний датафрейм
        notsold_stats: Статистика NOTSOLD (з calculate_notsold_percent)
        min_notsold: Мінімальний поріг
        max_notsold: Максимальний поріг
        group_cols: Колонки для з'єднання

    Returns:
        pd.DataFrame: Відфільтрований датафрейм
    """
    # Фільтруємо статистику
    valid_groups = notsold_stats[
        (notsold_stats['NOTSOLD_PERCENT'] >= min_notsold) &
        (notsold_stats['NOTSOLD_PERCENT'] <= max_notsold)
    ][group_cols]

    # Залишаємо тільки валідні групи
    result = df.merge(valid_groups, on=group_cols, how='inner')

    filtered_out = len(df) - len(result)
    print(f"Відфільтровано за NOTSOLD [{min_notsold:.0%}-{max_notsold:.0%}]:")
    print(f"  До: {len(df):,} рядків")
    print(f"  Після: {len(result):,} рядків")
    print(f"  Видалено: {filtered_out:,} рядків")

    return result


# =============================================================================
# MARKET TOTALS
# =============================================================================

def calculate_market_totals(
    df_competitors: pd.DataFrame,
    date_col: str = 'Date',
    drug_col: str = 'DRUGS_ID',
    quantity_col: str = 'Q',
    value_col: str = 'V'
) -> pd.DataFrame:
    """
    Розрахунок ринкових показників по конкурентах.

    Args:
        df_competitors: Датафрейм конкурентів (PHARM_ID != TARGET)
        date_col: Колонка з датою
        drug_col: Колонка з ID препарату
        quantity_col: Колонка з кількістю
        value_col: Колонка з виручкою

    Returns:
        pd.DataFrame: Агреговані ринкові показники
    """
    market_totals = df_competitors.groupby([date_col, drug_col]).agg({
        quantity_col: 'sum',
        value_col: 'sum'
    }).reset_index()

    market_totals = market_totals.rename(columns={
        quantity_col: 'MARKET_TOTAL_DRUGS_PACK',
        value_col: 'MARKET_TOTAL_DRUGS_REVENUE'
    })

    print(f"Розраховано MARKET_TOTALS для {market_totals[drug_col].nunique()} препаратів")

    return market_totals


# =============================================================================
# WEEKLY AGGREGATION
# =============================================================================

def aggregate_weekly(
    df: pd.DataFrame,
    group_cols: List[str],
    sum_cols: List[str] = ['Q', 'V'],
    first_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Тижнева агрегація даних.

    Args:
        df: Вхідний датафрейм
        group_cols: Колонки для групування (включаючи Date)
        sum_cols: Колонки для сумування
        first_cols: Колонки для взяття першого значення

    Returns:
        pd.DataFrame: Агрегований датафрейм
    """
    if first_cols is None:
        first_cols = ['DRUGS_NAME', 'INN_NAME', 'NFC1_ID', 'NFC_ID']

    agg_dict = {}
    for col in sum_cols:
        if col in df.columns:
            agg_dict[col] = 'sum'
    for col in first_cols:
        if col in df.columns:
            agg_dict[col] = 'first'

    result = df.groupby(group_cols).agg(agg_dict).reset_index()

    print(f"Агреговано до {len(result):,} рядків")

    return result


# =============================================================================
# VALIDATION
# =============================================================================

def validate_gaps_filled(
    df: pd.DataFrame,
    group_cols: List[str] = ['PHARM_ID', 'DRUGS_ID'],
    date_col: str = 'Date'
) -> bool:
    """
    Валідація що GAP FILLING виконано коректно.

    Перевіряє що для кожної групи є неперервний ряд тижнів.

    Args:
        df: Датафрейм для перевірки
        group_cols: Колонки групування
        date_col: Колонка з датою

    Returns:
        bool: True якщо валідація пройшла
    """
    issues = []

    for group_keys, group_df in df.groupby(group_cols):
        dates = group_df[date_col].sort_values()
        expected_weeks = (dates.max() - dates.min()).days // 7 + 1
        actual_weeks = len(dates)

        if actual_weeks != expected_weeks:
            issues.append({
                'group': group_keys,
                'expected': expected_weeks,
                'actual': actual_weeks
            })

    if issues:
        print(f"УВАГА: Знайдено {len(issues)} груп з пропусками!")
        for issue in issues[:5]:
            print(f"  {issue}")
        return False
    else:
        print("Валідація GAP FILLING: OK")
        return True


def validate_dataset(df: pd.DataFrame) -> Dict[str, bool]:
    """
    Комплексна валідація датасету.

    Args:
        df: Датафрейм для перевірки

    Returns:
        Dict з результатами перевірок
    """
    checks = {
        'has_zeros': (df['Q'] == 0).any() if 'Q' in df.columns else False,
        'date_is_datetime': pd.api.types.is_datetime64_any_dtype(df['Date']) if 'Date' in df.columns else False,
        'q_is_numeric': pd.api.types.is_numeric_dtype(df['Q']) if 'Q' in df.columns else False,
        'v_is_numeric': pd.api.types.is_numeric_dtype(df['V']) if 'V' in df.columns else False,
        'no_nulls_in_ids': not df[['PHARM_ID', 'DRUGS_ID']].isnull().any().any() if all(c in df.columns for c in ['PHARM_ID', 'DRUGS_ID']) else False
    }

    print("Валідація датасету:")
    for check, passed in checks.items():
        status = "OK" if passed else "FAILED"
        print(f"  {check}: {status}")

    return checks


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("ETL UTILITIES - cross_pharm_market_analysis")
    print("=" * 60)

    # Тест parse_period_id
    print("\nТест parse_period_id:")
    test_cases = [2024031, 2024127, 2023521]
    for tc in test_cases:
        result = parse_period_id(tc)
        print(f"  {tc} → {result.strftime('%Y-%m-%d')} ({result.strftime('%A')})")

    print("\nВсі функції готові до використання!")
