# =============================================================================
# STOCK-OUT DETECTION PARAMETERS - cross_pharm_market_analysis
# =============================================================================
# Файл: project_core/did_config/stockout_params.py
# Дата: 2026-01-28
# Опис: Параметри для детекції та аналізу stock-out подій
# =============================================================================

"""
Параметри stock-out detection для проекту cross_pharm_market_analysis.

Визначає:
    - Мінімальні тривалості періодів (PRE, DURING, POST)
    - Пороги для фільтрації препаратів
    - Параметри DiD аналізу

Використання:
    from project_core.did_config.stockout_params import (
        MIN_STOCKOUT_WEEKS,
        MIN_PRE_PERIOD_WEEKS,
        MIN_NOTSOLD_PERCENT
    )
"""


# =============================================================================
# STOCK-OUT DETECTION
# =============================================================================

# Мінімальна тривалість stock-out події
MIN_STOCKOUT_WEEKS: int = 1  # Мінімум 1 тиждень без продажів

# Мінімальна тривалість PRE-періоду (для розрахунку baseline)
MIN_PRE_PERIOD_WEEKS: int = 4  # Мінімум 4 тижні до stock-out


# =============================================================================
# DiD ANALYSIS PARAMETERS
# =============================================================================

# POST-період
MIN_POST_PERIOD_WEEKS: int = 4  # Мінімум 4 тижні після stock-out для аналізу
MAX_POST_GAP_WEEKS: int = 2     # Максимальний gap до відновлення продажів

# Мінімальна частка тижнів з продажами в POST-періоді
MIN_SALES_WEEKS_RATIO: float = 0.5  # 50% тижнів повинні мати продажі


# =============================================================================
# DRUG FILTERING (NOTSOLD)
# =============================================================================

# Препарат повинен мати stock-out (тижні без продажів)
MIN_NOTSOLD_PERCENT: float = 0.20  # Мінімум 20% тижнів без продажів

# Але не бути повністю відсутнім
MAX_NOTSOLD_PERCENT: float = 0.95  # Максимум 95% тижнів без продажів

# Мінімальний період активності препарату
MIN_ACTIVE_PERIOD_DAYS: int = 60  # Мінімум 60 днів активних продажів


# =============================================================================
# PHARMACY COVERAGE
# =============================================================================

# Поріг для визначення "core" препаратів (базовий асортимент)
CORE_COVERAGE_THRESHOLD: float = 0.70  # 70% coverage


# =============================================================================
# MARKET GROWTH
# =============================================================================

# Мінімальні продажі в PRE-періоді для розрахунку MARKET_GROWTH
MIN_MARKET_PRE: float = 1.0

# Мінімальний TOTAL для розрахунку SHARE
MIN_TOTAL_FOR_SHARE: float = 0.001


# =============================================================================
# CROSS-MARKET ANALYSIS
# =============================================================================

# Мінімальний % ринків для надійної статистики
MIN_MARKET_COVERAGE_FOR_CI: float = 0.30  # 30% ринків

# Рівень довіри для confidence interval
CONFIDENCE_LEVEL: float = 0.95  # 95% CI


# =============================================================================
# VALIDATION
# =============================================================================

def validate_params() -> bool:
    """
    Валідація параметрів при імпорті.

    Returns:
        bool: True якщо валідація пройшла
    """
    assert MIN_STOCKOUT_WEEKS >= 1, \
        "MIN_STOCKOUT_WEEKS must be at least 1"

    assert MIN_PRE_PERIOD_WEEKS >= 1, \
        "MIN_PRE_PERIOD_WEEKS must be at least 1"

    assert MIN_POST_PERIOD_WEEKS >= 1, \
        "MIN_POST_PERIOD_WEEKS must be at least 1"

    assert 0 < MIN_NOTSOLD_PERCENT < MAX_NOTSOLD_PERCENT < 1, \
        "NOTSOLD thresholds must be 0 < MIN < MAX < 1"

    assert 0 < CORE_COVERAGE_THRESHOLD <= 1, \
        "CORE_COVERAGE_THRESHOLD must be in (0, 1]"

    assert 0 < MIN_SALES_WEEKS_RATIO <= 1, \
        "MIN_SALES_WEEKS_RATIO must be in (0, 1]"

    assert 0.5 <= CONFIDENCE_LEVEL < 1, \
        "CONFIDENCE_LEVEL must be in [0.5, 1)"

    return True


# Автоматична валідація при імпорті
if __name__ != "__main__":
    validate_params()


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("STOCK-OUT PARAMETERS - cross_pharm_market_analysis")
    print("=" * 60)

    print("\nStock-out Detection:")
    print(f"  MIN_STOCKOUT_WEEKS: {MIN_STOCKOUT_WEEKS}")
    print(f"  MIN_PRE_PERIOD_WEEKS: {MIN_PRE_PERIOD_WEEKS}")

    print("\nDiD Analysis:")
    print(f"  MIN_POST_PERIOD_WEEKS: {MIN_POST_PERIOD_WEEKS}")
    print(f"  MAX_POST_GAP_WEEKS: {MAX_POST_GAP_WEEKS}")
    print(f"  MIN_SALES_WEEKS_RATIO: {MIN_SALES_WEEKS_RATIO}")

    print("\nDrug Filtering:")
    print(f"  MIN_NOTSOLD_PERCENT: {MIN_NOTSOLD_PERCENT:.0%}")
    print(f"  MAX_NOTSOLD_PERCENT: {MAX_NOTSOLD_PERCENT:.0%}")
    print(f"  MIN_ACTIVE_PERIOD_DAYS: {MIN_ACTIVE_PERIOD_DAYS}")

    print("\nCross-Market Analysis:")
    print(f"  MIN_MARKET_COVERAGE_FOR_CI: {MIN_MARKET_COVERAGE_FOR_CI:.0%}")
    print(f"  CONFIDENCE_LEVEL: {CONFIDENCE_LEVEL:.0%}")

    print(f"\nValidation: {'PASSED' if validate_params() else 'FAILED'}")
