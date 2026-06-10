# =============================================================================
# COVERAGE THRESHOLDS - cross_pharm_market_analysis (Phase 2)
# =============================================================================
# Файл: project_core/sub_coef_config/coverage_thresholds.py
# Дата: 2026-02-04
# Опис: Пороги для кластеризації препаратів за покриттям ринків
# =============================================================================

"""
Пороги покриття ринків для Phase 2 Cross-Market Aggregation.

Визначає:
    - Пороги для кластерів HIGH / MEDIUM / LOW / INSUFFICIENT
    - Функцію визначення кластера
    - Функцію валідації порогів

Логіка кластеризації:
    - HIGH: ≥50% ринків — найнадійніші дані для висновків
    - MEDIUM: 20-49% ринків — достатньо даних для аналізу
    - LOW: 10-19% ринків — обмежені дані, обережні висновки
    - INSUFFICIENT: <10% ринків — недостатньо даних для надійних висновків

Використання:
    from project_core.sub_coef_config.coverage_thresholds import (
        COVERAGE_HIGH,
        get_coverage_cluster,
        validate_thresholds
    )
"""


# =============================================================================
# COVERAGE CLUSTER THRESHOLDS
# =============================================================================

# HIGH: Препарат присутній на ≥50% ринків
# Найнадійніші дані для крос-ринкових висновків
COVERAGE_HIGH: float = 0.50

# MEDIUM: Препарат присутній на 20-49% ринків
# Достатньо даних для базового аналізу
COVERAGE_MEDIUM: float = 0.20

# LOW: Препарат присутній на 10-19% ринків
# Обмежені дані, широкі довірчі інтервали
COVERAGE_LOW: float = 0.10

# INSUFFICIENT: <10% ринків
# Недостатньо даних для надійних крос-ринкових висновків


# =============================================================================
# CLUSTER NAMES
# =============================================================================

CLUSTER_NAMES = {
    'HIGH': 'HIGH (≥50%)',
    'MEDIUM': 'MEDIUM (20-49%)',
    'LOW': 'LOW (10-19%)',
    'INSUFFICIENT': 'INSUFFICIENT (<10%)'
}


# =============================================================================
# CLASSIFICATION FUNCTION
# =============================================================================

def get_coverage_cluster(
    market_coverage: float,
    high_threshold: float = COVERAGE_HIGH,
    medium_threshold: float = COVERAGE_MEDIUM,
    low_threshold: float = COVERAGE_LOW
) -> str:
    """
    Визначення кластера покриття препарату.

    Args:
        market_coverage: Частка ринків, де присутній препарат (0.0-1.0)
        high_threshold: Поріг для HIGH кластера
        medium_threshold: Поріг для MEDIUM кластера
        low_threshold: Поріг для LOW кластера

    Returns:
        str: 'HIGH', 'MEDIUM', 'LOW', або 'INSUFFICIENT'

    Examples:
        >>> get_coverage_cluster(0.75)
        'HIGH'
        >>> get_coverage_cluster(0.35)
        'MEDIUM'
        >>> get_coverage_cluster(0.15)
        'LOW'
        >>> get_coverage_cluster(0.05)
        'INSUFFICIENT'
    """
    if market_coverage >= high_threshold:
        return 'HIGH'
    elif market_coverage >= medium_threshold:
        return 'MEDIUM'
    elif market_coverage >= low_threshold:
        return 'LOW'
    else:
        return 'INSUFFICIENT'


def get_cluster_description(cluster: str) -> str:
    """
    Отримати опис кластера покриття.

    Args:
        cluster: Назва кластера ('HIGH', 'MEDIUM', 'LOW', 'INSUFFICIENT')

    Returns:
        str: Опис кластера з порогами
    """
    return CLUSTER_NAMES.get(cluster, cluster)


# =============================================================================
# VALIDATION
# =============================================================================

def validate_thresholds() -> bool:
    """
    Валідація порогів покриття.

    Returns:
        bool: True якщо валідація пройшла

    Raises:
        AssertionError: Якщо пороги некоректні
    """
    assert 0 < COVERAGE_HIGH <= 1, \
        f"COVERAGE_HIGH must be in (0, 1], got {COVERAGE_HIGH}"

    assert 0 < COVERAGE_MEDIUM < COVERAGE_HIGH, \
        f"COVERAGE_MEDIUM must be in (0, COVERAGE_HIGH), got {COVERAGE_MEDIUM}"

    assert 0 < COVERAGE_LOW < COVERAGE_MEDIUM, \
        f"COVERAGE_LOW must be in (0, COVERAGE_MEDIUM), got {COVERAGE_LOW}"

    return True


# Автоматична валідація при імпорті
if __name__ != "__main__":
    validate_thresholds()


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("COVERAGE THRESHOLDS - cross_pharm_market_analysis (Phase 2)")
    print("=" * 60)

    print("\nCoverage Cluster Thresholds:")
    print(f"  COVERAGE_HIGH: {COVERAGE_HIGH:.0%} (≥{COVERAGE_HIGH:.0%} → HIGH)")
    print(f"  COVERAGE_MEDIUM: {COVERAGE_MEDIUM:.0%} ({COVERAGE_MEDIUM:.0%}-{COVERAGE_HIGH:.0%} → MEDIUM)")
    print(f"  COVERAGE_LOW: {COVERAGE_LOW:.0%} ({COVERAGE_LOW:.0%}-{COVERAGE_MEDIUM:.0%} → LOW)")
    print(f"  INSUFFICIENT: <{COVERAGE_LOW:.0%}")

    print("\nTest get_coverage_cluster:")
    test_cases = [
        (1.00, "HIGH"),
        (0.75, "HIGH"),
        (0.50, "HIGH"),
        (0.49, "MEDIUM"),
        (0.35, "MEDIUM"),
        (0.20, "MEDIUM"),
        (0.19, "LOW"),
        (0.15, "LOW"),
        (0.10, "LOW"),
        (0.09, "INSUFFICIENT"),
        (0.05, "INSUFFICIENT"),
        (0.00, "INSUFFICIENT"),
    ]

    all_passed = True
    for coverage, expected in test_cases:
        result = get_coverage_cluster(coverage)
        status = "OK" if result == expected else "FAIL"
        if result != expected:
            all_passed = False
        print(f"  coverage={coverage:.2f} → {result} [{status}]")

    print(f"\nValidation: {'PASSED' if validate_thresholds() else 'FAILED'}")
    print(f"All tests: {'PASSED' if all_passed else 'FAILED'}")
