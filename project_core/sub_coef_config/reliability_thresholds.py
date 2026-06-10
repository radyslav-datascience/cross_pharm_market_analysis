# =============================================================================
# RELIABILITY THRESHOLDS - cross_pharm_market_analysis (Phase 2)
# =============================================================================
# Файл: project_core/sub_coef_config/reliability_thresholds.py
# Дата: 2026-03-03
# Опис: Пороги для класифікації надійності коефіцієнтів субституції
# =============================================================================

"""
Пороги надійності коефіцієнтів субституції для Phase 2 Cross-Market Aggregation.

Визначає:
    - Пороги RELIABILITY на основі VARIATION_COEFFICIENT (коефіцієнт варіації)
    - Функцію класифікації надійності
    - Функцію валідації порогів

Логіка класифікації:
    - HIGH: VARIATION_COEFFICIENT < 0.15 — стабільна субституція across markets
    - MEDIUM: 0.15 <= VARIATION_COEFFICIENT < 0.30 — помірна варіативність
    - LOW: VARIATION_COEFFICIENT >= 0.30 — нестабільна субституція
    - SINGLE_MARKET: тільки 1 ринок — статистика відсутня

Використання:
    from project_core.sub_coef_config.reliability_thresholds import (
        RELIABILITY_HIGH,
        RELIABILITY_MEDIUM,
        get_reliability_class,
        validate_reliability_thresholds
    )
"""


# =============================================================================
# RELIABILITY THRESHOLDS (based on VARIATION_COEFFICIENT)
# =============================================================================

# HIGH: VARIATION_COEFFICIENT < 0.15
# Стабільна субституція — коефіцієнт надійний для бізнес-рішень
RELIABILITY_HIGH: float = 0.15

# MEDIUM: 0.15 <= VARIATION_COEFFICIENT < 0.30
# Помірна варіативність — коефіцієнт як орієнтир
RELIABILITY_MEDIUM: float = 0.30

# LOW: VARIATION_COEFFICIENT >= 0.30
# Нестабільна — потрібен додатковий аналіз причин

# SINGLE_MARKET: тільки 1 ринок (MARKET_COUNT_CLEAN == 1)
# Статистика відсутня, потрібні додаткові дані


# =============================================================================
# RELIABILITY NAMES
# =============================================================================

RELIABILITY_NAMES = {
    'HIGH': 'HIGH (VARIATION_COEFFICIENT < 0.15)',
    'MEDIUM': 'MEDIUM (0.15 <= VARIATION_COEFFICIENT < 0.30)',
    'LOW': 'LOW (VARIATION_COEFFICIENT >= 0.30)',
    'SINGLE_MARKET': 'SINGLE_MARKET (1 ринок)'
}


# =============================================================================
# CLASSIFICATION FUNCTION
# =============================================================================

def get_reliability_class(
    variation_coefficient: float,
    market_count_clean: int,
    high_threshold: float = RELIABILITY_HIGH,
    medium_threshold: float = RELIABILITY_MEDIUM
) -> str:
    """
    Визначення класу надійності коефіцієнта субституції.

    Args:
        variation_coefficient: Коефіцієнт варіації (ratio, не %)
        market_count_clean: Кількість ринків без outliers
        high_threshold: Поріг для HIGH (VARIATION_COEFFICIENT < threshold)
        medium_threshold: Поріг для MEDIUM (VARIATION_COEFFICIENT < threshold)

    Returns:
        str: 'HIGH', 'MEDIUM', 'LOW', або 'SINGLE_MARKET'

    Examples:
        >>> get_reliability_class(0.10, 15)
        'HIGH'
        >>> get_reliability_class(0.20, 10)
        'MEDIUM'
        >>> get_reliability_class(0.45, 8)
        'LOW'
        >>> get_reliability_class(0.0, 1)
        'SINGLE_MARKET'
    """
    import math

    if market_count_clean <= 1:
        return 'SINGLE_MARKET'

    if math.isnan(variation_coefficient) if isinstance(variation_coefficient, float) else False:
        return 'SINGLE_MARKET'

    if variation_coefficient < high_threshold:
        return 'HIGH'
    elif variation_coefficient < medium_threshold:
        return 'MEDIUM'
    else:
        return 'LOW'


def get_reliability_description(reliability: str) -> str:
    """
    Отримати опис класу надійності.

    Args:
        reliability: Назва класу ('HIGH', 'MEDIUM', 'LOW', 'SINGLE_MARKET')

    Returns:
        str: Опис класу з порогами
    """
    return RELIABILITY_NAMES.get(reliability, reliability)


# =============================================================================
# VALIDATION
# =============================================================================

def validate_reliability_thresholds() -> bool:
    """
    Валідація порогів надійності.

    Returns:
        bool: True якщо валідація пройшла

    Raises:
        AssertionError: Якщо пороги некоректні
    """
    assert 0 < RELIABILITY_HIGH <= 1, \
        f"RELIABILITY_HIGH must be in (0, 1], got {RELIABILITY_HIGH}"

    assert 0 < RELIABILITY_MEDIUM <= 1, \
        f"RELIABILITY_MEDIUM must be in (0, 1], got {RELIABILITY_MEDIUM}"

    assert RELIABILITY_HIGH < RELIABILITY_MEDIUM, \
        f"RELIABILITY_HIGH ({RELIABILITY_HIGH}) must be < RELIABILITY_MEDIUM ({RELIABILITY_MEDIUM})"

    return True


# Автоматична валідація при імпорті
if __name__ != "__main__":
    validate_reliability_thresholds()


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("RELIABILITY THRESHOLDS - cross_pharm_market_analysis (Phase 2)")
    print("=" * 60)

    print("\nReliability Thresholds:")
    print(f"  RELIABILITY_HIGH: {RELIABILITY_HIGH} (VARIATION_COEFFICIENT < {RELIABILITY_HIGH} -> HIGH)")
    print(f"  RELIABILITY_MEDIUM: {RELIABILITY_MEDIUM} ({RELIABILITY_HIGH} <= VARIATION_COEFFICIENT < {RELIABILITY_MEDIUM} -> MEDIUM)")
    print(f"  LOW: VARIATION_COEFFICIENT >= {RELIABILITY_MEDIUM}")
    print(f"  SINGLE_MARKET: market_count_clean <= 1")

    print("\nTest get_reliability_class:")
    test_cases = [
        # (variation_coefficient, market_count_clean, expected)
        (0.05, 20, "HIGH"),
        (0.10, 15, "HIGH"),
        (0.14, 10, "HIGH"),
        (0.15, 10, "MEDIUM"),
        (0.20, 8, "MEDIUM"),
        (0.29, 5, "MEDIUM"),
        (0.30, 5, "LOW"),
        (0.45, 8, "LOW"),
        (0.80, 3, "LOW"),
        (0.00, 1, "SINGLE_MARKET"),
        (0.10, 1, "SINGLE_MARKET"),
        (float('nan'), 5, "SINGLE_MARKET"),
    ]

    all_passed = True
    for vc, mc, expected in test_cases:
        result = get_reliability_class(vc, mc)
        status = "OK" if result == expected else "FAIL"
        if result != expected:
            all_passed = False
        print(f"  vc={vc}, mc={mc} -> {result} [{status}]")

    print(f"\nValidation: {'PASSED' if validate_reliability_thresholds() else 'FAILED'}")
    print(f"All tests: {'PASSED' if all_passed else 'FAILED'}")
