# =============================================================================
# DiD UTILITIES - cross_pharm_market_analysis
# =============================================================================
# Файл: project_core/utility_functions/did_utils.py
# Дата: 2026-01-28
# Опис: Утиліти для Difference-in-Differences аналізу
# =============================================================================

"""
DiD утиліти для проекту cross_pharm_market_analysis.

Функції:
    - define_post_period(): Визначення POST-періоду для stock-out події
    - calculate_market_growth(): Розрахунок MARKET_GROWTH
    - calculate_expected(): Розрахунок очікуваних продажів
    - calculate_lift(): Розрахунок LIFT (додаткові продажі)
    - calculate_shares(): Розрахунок SHARE_INTERNAL, SHARE_LOST
    - nfc_decomposition(): Декомпозиція по NFC1
    - validate_did_invariants(): Валідація результатів

Використання:
    from project_core.utility_functions.did_utils import (
        calculate_market_growth,
        calculate_lift,
        calculate_shares
    )
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any


# =============================================================================
# POST-PERIOD DEFINITION
# =============================================================================

def define_post_period(
    df_drug: pd.DataFrame,
    stockout_end: datetime,
    min_post_weeks: int = 4,
    max_gap_weeks: int = 2,
    date_col: str = 'Date',
    quantity_col: str = 'Q'
) -> Tuple[Optional[datetime], Optional[datetime], int, str]:
    """
    Визначення POST-періоду для stock-out події.

    POST-період починається коли продажі відновлюються після stock-out
    і триває мінімум min_post_weeks тижнів.

    Args:
        df_drug: Датафрейм препарату
        stockout_end: Дата закінчення stock-out
        min_post_weeks: Мінімальна тривалість POST-періоду
        max_gap_weeks: Максимальний gap до відновлення продажів
        date_col: Назва колонки з датою
        quantity_col: Назва колонки з кількістю

    Returns:
        Tuple: (post_start, post_end, post_weeks, status)
        - post_start: Дата початку POST-періоду (або None)
        - post_end: Дата кінця POST-періоду (або None)
        - post_weeks: Кількість тижнів POST-періоду
        - status: 'valid', 'no_recovery', 'insufficient_data', 'gap_too_large'
    """
    # Дані після stock-out
    df_after = df_drug[df_drug[date_col] > stockout_end].sort_values(date_col)

    if len(df_after) == 0:
        return None, None, 0, 'no_recovery'

    # Знаходимо перший тиждень з продажами після stock-out
    df_with_sales = df_after[df_after[quantity_col] > 0]

    if len(df_with_sales) == 0:
        return None, None, 0, 'no_recovery'

    first_sale_date = df_with_sales[date_col].min()

    # Перевіряємо gap між stock-out та відновленням
    gap_weeks = (first_sale_date - stockout_end).days // 7
    if gap_weeks > max_gap_weeks:
        return None, None, 0, 'gap_too_large'

    # POST-період починається з першого продажу
    post_start = first_sale_date

    # Шукаємо кінець POST-періоду (мінімум min_post_weeks тижнів)
    min_post_end = post_start + timedelta(weeks=min_post_weeks - 1)

    # Дані в POST-періоді
    df_post = df_after[df_after[date_col] >= post_start]

    if len(df_post) < min_post_weeks:
        return None, None, len(df_post), 'insufficient_data'

    # POST-період = перші min_post_weeks тижнів з продажами
    post_end = df_post[date_col].iloc[min_post_weeks - 1]
    post_weeks = min_post_weeks

    return post_start, post_end, post_weeks, 'valid'


def validate_post_period(
    df_drug: pd.DataFrame,
    post_start: datetime,
    post_end: datetime,
    date_col: str = 'Date',
    quantity_col: str = 'Q',
    min_sales_weeks_ratio: float = 0.5
) -> Tuple[bool, str]:
    """
    Валідація POST-періоду.

    Перевіряє що в POST-періоді є достатньо тижнів з продажами.

    Args:
        df_drug: Датафрейм препарату
        post_start: Початок POST-періоду
        post_end: Кінець POST-періоду
        date_col: Назва колонки з датою
        quantity_col: Назва колонки з кількістю
        min_sales_weeks_ratio: Мінімальна частка тижнів з продажами

    Returns:
        Tuple: (is_valid, reason)
    """
    df_post = df_drug[
        (df_drug[date_col] >= post_start) &
        (df_drug[date_col] <= post_end)
    ]

    if len(df_post) == 0:
        return False, 'no_data_in_post'

    weeks_with_sales = (df_post[quantity_col] > 0).sum()
    sales_ratio = weeks_with_sales / len(df_post)

    if sales_ratio < min_sales_weeks_ratio:
        return False, f'low_sales_ratio_{sales_ratio:.2f}'

    return True, 'valid'


# =============================================================================
# MARKET GROWTH CALCULATION
# =============================================================================

def calculate_market_growth(
    market_pre: float,
    market_during: float,
    min_market_pre: float = 1.0
) -> float:
    """
    Розрахунок MARKET_GROWTH для коригування на тренд ринку.

    MARKET_GROWTH = MARKET_DURING / MARKET_PRE

    Args:
        market_pre: Продажі ринку в PRE-періоді
        market_during: Продажі ринку під час stock-out
        min_market_pre: Мінімальне значення PRE для уникнення ділення на 0

    Returns:
        float: Коефіцієнт росту ринку (>=0)
    """
    if market_pre < min_market_pre:
        return 1.0  # Нейтральний коефіцієнт якщо немає даних PRE

    growth = market_during / market_pre
    return max(0.0, growth)  # Не може бути від'ємним


def calculate_market_totals_for_period(
    df: pd.DataFrame,
    start_date: datetime,
    end_date: datetime,
    date_col: str = 'Date',
    market_col: str = 'MARKET_TOTAL_DRUGS_PACK'
) -> float:
    """
    Розрахунок сумарних продажів ринку за період.

    Args:
        df: Датафрейм з даними
        start_date: Початок періоду
        end_date: Кінець періоду
        date_col: Назва колонки з датою
        market_col: Назва колонки з ринковими продажами

    Returns:
        float: Сума продажів ринку за період
    """
    df_period = df[
        (df[date_col] >= start_date) &
        (df[date_col] <= end_date)
    ]

    return df_period[market_col].sum()


# =============================================================================
# LIFT CALCULATION
# =============================================================================

def calculate_expected(
    sales_pre: float,
    market_growth: float
) -> float:
    """
    Розрахунок очікуваних продажів без stock-out.

    EXPECTED = SALES_PRE * MARKET_GROWTH

    Args:
        sales_pre: Продажі в PRE-періоді
        market_growth: Коефіцієнт росту ринку

    Returns:
        float: Очікувані продажі (>=0)
    """
    return max(0.0, sales_pre * market_growth)


def calculate_lift(
    actual: float,
    expected: float
) -> float:
    """
    Розрахунок LIFT - додаткових продажів через stock-out.

    LIFT = max(0, ACTUAL - EXPECTED)

    Args:
        actual: Фактичні продажі
        expected: Очікувані продажі

    Returns:
        float: LIFT (>=0, від'ємні значення обмежуються до 0)
    """
    return max(0.0, actual - expected)


def calculate_substitute_lift(
    df_substitute: pd.DataFrame,
    pre_start: datetime,
    pre_end: datetime,
    during_start: datetime,
    during_end: datetime,
    market_growth: float,
    date_col: str = 'Date',
    quantity_col: str = 'Q'
) -> Dict[str, float]:
    """
    Розрахунок LIFT для одного substitute.

    Args:
        df_substitute: Дані substitute препарату
        pre_start, pre_end: PRE-період
        during_start, during_end: Період stock-out
        market_growth: Коефіцієнт росту ринку
        date_col, quantity_col: Назви колонок

    Returns:
        Dict з ключами: sales_pre, sales_during, expected, lift
    """
    # Продажі в PRE-періоді
    df_pre = df_substitute[
        (df_substitute[date_col] >= pre_start) &
        (df_substitute[date_col] <= pre_end)
    ]
    sales_pre = df_pre[quantity_col].sum()

    # Продажі під час stock-out
    df_during = df_substitute[
        (df_substitute[date_col] >= during_start) &
        (df_substitute[date_col] <= during_end)
    ]
    sales_during = df_during[quantity_col].sum()

    # Очікувані та LIFT
    expected = calculate_expected(sales_pre, market_growth)
    lift = calculate_lift(sales_during, expected)

    return {
        'sales_pre': sales_pre,
        'sales_during': sales_during,
        'expected': expected,
        'lift': lift
    }


# =============================================================================
# SHARE CALCULATION
# =============================================================================

def calculate_shares(
    internal_lift: float,
    lost_sales: float,
    min_total: float = 0.001
) -> Tuple[float, float]:
    """
    Розрахунок SHARE_INTERNAL та SHARE_LOST.

    SHARE_INTERNAL = INTERNAL_LIFT / TOTAL
    SHARE_LOST = LOST_SALES / TOTAL

    Інваріант: SHARE_INTERNAL + SHARE_LOST = 1.0

    Args:
        internal_lift: Сума LIFT по substitutes (в нашій аптеці)
        lost_sales: LIFT конкурентів
        min_total: Мінімальний TOTAL для уникнення ділення на 0

    Returns:
        Tuple: (share_internal, share_lost)
    """
    total = internal_lift + lost_sales

    if total < min_total:
        # Якщо немає ефекту, повертаємо NaN
        return np.nan, np.nan

    share_internal = internal_lift / total
    share_lost = lost_sales / total

    return share_internal, share_lost


def calculate_lost_sales(
    df_competitors: pd.DataFrame,
    drug_id: int,
    pre_start: datetime,
    pre_end: datetime,
    during_start: datetime,
    during_end: datetime,
    market_growth: float,
    date_col: str = 'Date',
    drug_col: str = 'DRUGS_ID',
    quantity_col: str = 'MARKET_TOTAL_DRUGS_PACK'
) -> float:
    """
    Розрахунок LOST_SALES - продажі target препарату у конкурентів.

    Args:
        df_competitors: Датафрейм з ринковими даними
        drug_id: ID target препарату
        pre_start, pre_end: PRE-період
        during_start, during_end: Період stock-out
        market_growth: Коефіцієнт росту ринку
        date_col, drug_col, quantity_col: Назви колонок

    Returns:
        float: LOST_SALES (LIFT конкурентів)
    """
    df_drug = df_competitors[df_competitors[drug_col] == drug_id]

    # PRE-період
    df_pre = df_drug[
        (df_drug[date_col] >= pre_start) &
        (df_drug[date_col] <= pre_end)
    ]
    comp_pre = df_pre[quantity_col].sum()

    # Період stock-out
    df_during = df_drug[
        (df_drug[date_col] >= during_start) &
        (df_drug[date_col] <= during_end)
    ]
    comp_during = df_during[quantity_col].sum()

    # LIFT конкурентів
    expected = calculate_expected(comp_pre, market_growth)
    lost_sales = calculate_lift(comp_during, expected)

    return lost_sales


# =============================================================================
# NFC DECOMPOSITION
# =============================================================================

def nfc_decomposition(
    substitutes_lifts: List[Dict[str, Any]],
    target_nfc1: str
) -> Dict[str, float]:
    """
    Декомпозиція INTERNAL_LIFT по NFC1 категоріях.

    Розділяє substitutes на:
    - SAME_NFC1: та сама форма випуску що й target
    - DIFF_NFC1: інша форма випуску

    Args:
        substitutes_lifts: Список словників з полями:
            - nfc1_id: NFC1 категорія substitute
            - lift: LIFT substitute
        target_nfc1: NFC1 категорія target препарату

    Returns:
        Dict з ключами:
            - lift_same_nfc1: Сума LIFT тієї ж форми
            - lift_diff_nfc1: Сума LIFT іншої форми
            - share_same_nfc1: Частка тієї ж форми
            - share_diff_nfc1: Частка іншої форми
            - internal_lift: Загальний INTERNAL_LIFT
    """
    lift_same = 0.0
    lift_diff = 0.0

    for sub in substitutes_lifts:
        lift = sub.get('lift', 0.0)
        nfc1 = sub.get('nfc1_id', '')

        if nfc1 == target_nfc1:
            lift_same += lift
        else:
            lift_diff += lift

    internal_lift = lift_same + lift_diff

    # Розрахунок часток
    if internal_lift > 0:
        share_same = lift_same / internal_lift
        share_diff = lift_diff / internal_lift
    else:
        share_same = np.nan
        share_diff = np.nan

    return {
        'lift_same_nfc1': lift_same,
        'lift_diff_nfc1': lift_diff,
        'share_same_nfc1': share_same,
        'share_diff_nfc1': share_diff,
        'internal_lift': internal_lift
    }


# =============================================================================
# VALIDATION
# =============================================================================

def validate_did_invariants(
    result: Dict[str, float],
    tolerance: float = 0.001
) -> List[str]:
    """
    Валідація інваріантів DiD результатів.

    Перевіряє:
    1. SHARE_INTERNAL + SHARE_LOST = 1.0
    2. SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 = 1.0
    3. LIFT_SAME + LIFT_DIFF = INTERNAL_LIFT
    4. Всі SHARE в діапазоні [0, 1]

    Args:
        result: Словник з результатами DiD
        tolerance: Допустима похибка

    Returns:
        List[str]: Список помилок (порожній якщо все OK)
    """
    errors = []

    # Перевірка 1: SHARE_INTERNAL + SHARE_LOST = 1.0
    share_internal = result.get('share_internal', np.nan)
    share_lost = result.get('share_lost', np.nan)

    if not np.isnan(share_internal) and not np.isnan(share_lost):
        share_sum = share_internal + share_lost
        if abs(share_sum - 1.0) > tolerance:
            errors.append(f"SHARE_INTERNAL + SHARE_LOST = {share_sum:.4f} != 1.0")

    # Перевірка 2: SHARE_SAME_NFC1 + SHARE_DIFF_NFC1 = 1.0
    share_same = result.get('share_same_nfc1', np.nan)
    share_diff = result.get('share_diff_nfc1', np.nan)

    if not np.isnan(share_same) and not np.isnan(share_diff):
        nfc_sum = share_same + share_diff
        if abs(nfc_sum - 1.0) > tolerance:
            errors.append(f"SHARE_SAME + SHARE_DIFF = {nfc_sum:.4f} != 1.0")

    # Перевірка 3: LIFT_SAME + LIFT_DIFF = INTERNAL_LIFT
    lift_same = result.get('lift_same_nfc1', 0.0)
    lift_diff = result.get('lift_diff_nfc1', 0.0)
    internal_lift = result.get('internal_lift', 0.0)

    lift_sum = lift_same + lift_diff
    if abs(lift_sum - internal_lift) > tolerance:
        errors.append(f"LIFT_SAME + LIFT_DIFF = {lift_sum:.4f} != INTERNAL_LIFT {internal_lift:.4f}")

    # Перевірка 4: SHARE в [0, 1]
    share_fields = ['share_internal', 'share_lost', 'share_same_nfc1', 'share_diff_nfc1']
    for field in share_fields:
        value = result.get(field, np.nan)
        if not np.isnan(value) and not (0 <= value <= 1):
            errors.append(f"{field} = {value:.4f} not in [0, 1]")

    return errors


def validate_did_result(result: Dict[str, float]) -> bool:
    """
    Швидка валідація DiD результату.

    Args:
        result: Словник з результатами DiD

    Returns:
        bool: True якщо результат валідний
    """
    errors = validate_did_invariants(result)
    return len(errors) == 0


# =============================================================================
# AGGREGATION HELPERS
# =============================================================================

def aggregate_by_drug(
    events_results: List[Dict[str, Any]],
    drug_col: str = 'drugs_id'
) -> pd.DataFrame:
    """
    Агрегація результатів DiD по препаратах.

    Для кожного препарату розраховує середні значення по всіх stock-out подіях.

    Args:
        events_results: Список результатів по подіях
        drug_col: Назва колонки з ID препарату

    Returns:
        pd.DataFrame: Агреговані результати по препаратах
    """
    df = pd.DataFrame(events_results)

    if len(df) == 0:
        return pd.DataFrame()

    agg_dict = {
        'share_internal': 'mean',
        'share_lost': 'mean',
        'share_same_nfc1': 'mean',
        'share_diff_nfc1': 'mean',
        'internal_lift': 'sum',
        'lost_sales': 'sum',
        'event_id': 'count'  # Кількість подій
    }

    # Фільтруємо тільки існуючі колонки
    agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}

    result = df.groupby(drug_col).agg(agg_dict).reset_index()
    result = result.rename(columns={'event_id': 'events_count'})

    return result


# =============================================================================
# CROSS-MARKET AGGREGATION
# =============================================================================

def aggregate_cross_market(
    market_results: List[Dict[str, Any]],
    drug_col: str = 'drugs_id'
) -> pd.DataFrame:
    """
    Агрегація результатів по препаратах across markets.

    Для кожного препарату розраховує:
    - mean, std, CI по SHARE_INTERNAL
    - кількість ринків

    Args:
        market_results: Список результатів з різних ринків
        drug_col: Назва колонки з ID препарату

    Returns:
        pd.DataFrame: Крос-ринкова агрегація
    """
    from scipy import stats

    df = pd.DataFrame(market_results)

    if len(df) == 0:
        return pd.DataFrame()

    def calculate_ci(series, confidence=0.95):
        """Розрахунок confidence interval."""
        n = len(series)
        if n < 2:
            return np.nan, np.nan

        mean = series.mean()
        se = series.std() / np.sqrt(n)
        h = se * stats.t.ppf((1 + confidence) / 2, n - 1)

        return mean - h, mean + h

    # Агрегація по препаратах
    agg_results = []

    for drug_id, group in df.groupby(drug_col):
        share_internal_values = group['share_internal'].dropna()

        if len(share_internal_values) == 0:
            continue

        ci_lower, ci_upper = calculate_ci(share_internal_values)

        agg_results.append({
            drug_col: drug_id,
            'markets_count': len(share_internal_values),
            'mean_share_internal': share_internal_values.mean(),
            'std_share_internal': share_internal_values.std(),
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'min_share_internal': share_internal_values.min(),
            'max_share_internal': share_internal_values.max()
        })

    return pd.DataFrame(agg_results)


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("DiD UTILITIES - cross_pharm_market_analysis")
    print("=" * 60)

    # Тест calculate_market_growth
    print("\n1. Test calculate_market_growth:")
    growth = calculate_market_growth(100, 120)
    print(f"   market_pre=100, market_during=120 -> growth={growth}")

    # Тест calculate_lift
    print("\n2. Test calculate_lift:")
    lift = calculate_lift(150, 100)
    print(f"   actual=150, expected=100 -> lift={lift}")

    # Тест calculate_shares
    print("\n3. Test calculate_shares:")
    share_int, share_lost = calculate_shares(70, 30)
    print(f"   internal=70, lost=30 -> share_int={share_int}, share_lost={share_lost}")

    # Тест nfc_decomposition
    print("\n4. Test nfc_decomposition:")
    subs = [
        {'nfc1_id': 'ORAL', 'lift': 50},
        {'nfc1_id': 'ORAL', 'lift': 30},
        {'nfc1_id': 'INJECT', 'lift': 20}
    ]
    decomp = nfc_decomposition(subs, 'ORAL')
    print(f"   target_nfc1='ORAL' -> {decomp}")

    # Тест validate_did_invariants
    print("\n5. Test validate_did_invariants:")
    result = {
        'share_internal': 0.7,
        'share_lost': 0.3,
        'share_same_nfc1': 0.8,
        'share_diff_nfc1': 0.2,
        'lift_same_nfc1': 80,
        'lift_diff_nfc1': 20,
        'internal_lift': 100
    }
    errors = validate_did_invariants(result)
    print(f"   Errors: {errors if errors else 'None (OK)'}")

    print("\n" + "=" * 60)
    print("Всі функції готові до використання!")
