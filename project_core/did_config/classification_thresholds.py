# =============================================================================
# CLASSIFICATION THRESHOLDS - cross_pharm_market_analysis
# =============================================================================
# Файл: project_core/did_config/classification_thresholds.py
# Дата: 2026-01-28
# Опис: Пороги для класифікації препаратів за субституційністю
# =============================================================================

"""
Пороги класифікації препаратів для проекту cross_pharm_market_analysis.

Визначає:
    - Пороги для CRITICAL / MODERATE / SUBSTITUTABLE
    - Функції класифікації
    - Пороги для cross-market стабільності

Логіка класифікації:
    - CRITICAL: SHARE_LOST > 40% → тримати в асортименті (клієнти йдуть)
    - SUBSTITUTABLE: SHARE_INTERNAL > 60% → можна замінити (клієнти залишаються)
    - MODERATE: між порогами → потребує додаткового аналізу

Використання:
    from project_core.did_config.classification_thresholds import (
        CRITICAL_THRESHOLD,
        classify_drug,
        classify_drug_cross_market
    )
"""

import numpy as np
from typing import Tuple, Optional


# =============================================================================
# SINGLE-MARKET CLASSIFICATION THRESHOLDS
# =============================================================================

# CRITICAL: клієнти йдуть до конкурентів
CRITICAL_THRESHOLD: float = 0.40  # SHARE_LOST > 40%

# SUBSTITUTABLE: клієнти залишаються в аптеці
SUBSTITUTABLE_THRESHOLD: float = 0.60  # SHARE_INTERNAL > 60%


# =============================================================================
# CROSS-MARKET CLASSIFICATION THRESHOLDS
# =============================================================================

# Стабільність класифікації across markets
# Якщо >70% ринків дають однакову класифікацію — вона стабільна
CROSS_MARKET_STABILITY_THRESHOLD: float = 0.70

# Максимальне стандартне відхилення для "стабільного" препарату
MAX_STD_FOR_STABLE: float = 0.15  # 15%

# Мінімальна ширина CI для "uncertain" препарату
MIN_CI_WIDTH_FOR_UNCERTAIN: float = 0.20  # 20%


# =============================================================================
# SINGLE-MARKET CLASSIFICATION
# =============================================================================

def classify_drug(
    share_internal: float,
    share_lost: float,
    critical_threshold: float = CRITICAL_THRESHOLD,
    substitutable_threshold: float = SUBSTITUTABLE_THRESHOLD
) -> str:
    """
    Класифікація препарату на основі SHARE метрик (один ринок).

    Логіка:
    - SHARE_LOST > critical_threshold → CRITICAL
    - SHARE_INTERNAL > substitutable_threshold → SUBSTITUTABLE
    - Інше → MODERATE

    Args:
        share_internal: Частка попиту, що залишилась в аптеці
        share_lost: Частка попиту, що пішла до конкурентів
        critical_threshold: Поріг для CRITICAL
        substitutable_threshold: Поріг для SUBSTITUTABLE

    Returns:
        str: 'CRITICAL', 'SUBSTITUTABLE', 'MODERATE', або 'UNKNOWN'
    """
    if np.isnan(share_lost) or np.isnan(share_internal):
        return 'UNKNOWN'

    if share_lost > critical_threshold:
        return 'CRITICAL'
    elif share_internal > substitutable_threshold:
        return 'SUBSTITUTABLE'
    else:
        return 'MODERATE'


# =============================================================================
# CROSS-MARKET CLASSIFICATION
# =============================================================================

def classify_drug_cross_market(
    mean_share_internal: float,
    mean_share_lost: float,
    std_share_internal: float,
    ci_lower: float,
    ci_upper: float,
    markets_count: int,
    min_markets: int = 3
) -> Tuple[str, str, float]:
    """
    Класифікація препарату на основі крос-ринкової статистики.

    Args:
        mean_share_internal: Середній SHARE_INTERNAL по ринках
        mean_share_lost: Середній SHARE_LOST по ринках
        std_share_internal: Стандартне відхилення SHARE_INTERNAL
        ci_lower: Нижня межа 95% CI
        ci_upper: Верхня межа 95% CI
        markets_count: Кількість ринків з даними
        min_markets: Мінімальна кількість ринків для надійної класифікації

    Returns:
        Tuple: (classification, stability, confidence)
        - classification: 'CRITICAL', 'SUBSTITUTABLE', 'MODERATE', 'INSUFFICIENT_DATA'
        - stability: 'STABLE', 'UNSTABLE', 'UNCERTAIN'
        - confidence: float 0-1 (рівень впевненості)
    """
    # Перевірка достатності даних
    if markets_count < min_markets:
        return 'INSUFFICIENT_DATA', 'UNCERTAIN', 0.0

    # Базова класифікація
    base_class = classify_drug(mean_share_internal, mean_share_lost)

    if base_class == 'UNKNOWN':
        return 'UNKNOWN', 'UNCERTAIN', 0.0

    # Визначення стабільності
    ci_width = ci_upper - ci_lower

    if std_share_internal <= MAX_STD_FOR_STABLE:
        stability = 'STABLE'
        confidence = 1.0 - (std_share_internal / MAX_STD_FOR_STABLE)
    elif ci_width >= MIN_CI_WIDTH_FOR_UNCERTAIN:
        stability = 'UNCERTAIN'
        confidence = 0.5
    else:
        stability = 'UNSTABLE'
        confidence = 0.7

    # Перевірка чи CI не перетинає пороги
    if base_class == 'CRITICAL':
        # Якщо верхня межа CI для share_lost < threshold — не впевнені
        if ci_upper < CRITICAL_THRESHOLD:
            stability = 'UNCERTAIN'
            confidence *= 0.7

    elif base_class == 'SUBSTITUTABLE':
        # Якщо нижня межа CI для share_internal < threshold — не впевнені
        if ci_lower < SUBSTITUTABLE_THRESHOLD:
            stability = 'UNCERTAIN'
            confidence *= 0.7

    return base_class, stability, min(1.0, max(0.0, confidence))


def get_classification_label(
    classification: str,
    stability: str
) -> str:
    """
    Отримати людино-читабельний label класифікації.

    Args:
        classification: 'CRITICAL', 'SUBSTITUTABLE', 'MODERATE'
        stability: 'STABLE', 'UNSTABLE', 'UNCERTAIN'

    Returns:
        str: Опис класифікації
    """
    labels = {
        ('CRITICAL', 'STABLE'): "КРИТИЧНИЙ - тримати в асортименті",
        ('CRITICAL', 'UNSTABLE'): "КРИТИЧНИЙ (нестабільно) - потребує моніторингу",
        ('CRITICAL', 'UNCERTAIN'): "ЙМОВІРНО КРИТИЧНИЙ - недостатньо даних",

        ('SUBSTITUTABLE', 'STABLE'): "ЗАМІНЮВАНИЙ - можна вивести з асортименту",
        ('SUBSTITUTABLE', 'UNSTABLE'): "ЗАМІНЮВАНИЙ (нестабільно) - потребує моніторингу",
        ('SUBSTITUTABLE', 'UNCERTAIN'): "ЙМОВІРНО ЗАМІНЮВАНИЙ - недостатньо даних",

        ('MODERATE', 'STABLE'): "ПОМІРНИЙ - залишити, моніторити",
        ('MODERATE', 'UNSTABLE'): "ПОМІРНИЙ (нестабільно) - детальний аналіз",
        ('MODERATE', 'UNCERTAIN'): "НЕВИЗНАЧЕНИЙ - потрібно більше даних"
    }

    key = (classification, stability)
    return labels.get(key, f"{classification} ({stability})")


# =============================================================================
# VALIDATION
# =============================================================================

def validate_thresholds() -> bool:
    """
    Валідація порогів класифікації.

    Returns:
        bool: True якщо валідація пройшла
    """
    assert 0 < CRITICAL_THRESHOLD < 1, \
        "CRITICAL_THRESHOLD must be in (0, 1)"

    assert 0 < SUBSTITUTABLE_THRESHOLD < 1, \
        "SUBSTITUTABLE_THRESHOLD must be in (0, 1)"

    assert CRITICAL_THRESHOLD + SUBSTITUTABLE_THRESHOLD <= 1.0, \
        "Sum of thresholds should not exceed 1.0 for logical consistency"

    assert 0 < CROSS_MARKET_STABILITY_THRESHOLD <= 1, \
        "CROSS_MARKET_STABILITY_THRESHOLD must be in (0, 1]"

    assert 0 < MAX_STD_FOR_STABLE < 1, \
        "MAX_STD_FOR_STABLE must be in (0, 1)"

    return True


# Автоматична валідація при імпорті
if __name__ != "__main__":
    validate_thresholds()


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("CLASSIFICATION THRESHOLDS - cross_pharm_market_analysis")
    print("=" * 60)

    print("\nSingle-Market Thresholds:")
    print(f"  CRITICAL_THRESHOLD: {CRITICAL_THRESHOLD:.0%}")
    print(f"  SUBSTITUTABLE_THRESHOLD: {SUBSTITUTABLE_THRESHOLD:.0%}")

    print("\nCross-Market Thresholds:")
    print(f"  CROSS_MARKET_STABILITY_THRESHOLD: {CROSS_MARKET_STABILITY_THRESHOLD:.0%}")
    print(f"  MAX_STD_FOR_STABLE: {MAX_STD_FOR_STABLE:.0%}")
    print(f"  MIN_CI_WIDTH_FOR_UNCERTAIN: {MIN_CI_WIDTH_FOR_UNCERTAIN:.0%}")

    print("\nTest classify_drug:")
    test_cases = [
        (0.30, 0.70, "CRITICAL"),        # High lost
        (0.70, 0.30, "SUBSTITUTABLE"),   # High internal
        (0.50, 0.50, "MODERATE"),        # Middle
        (0.55, 0.45, "MODERATE"),        # Just below substitutable
    ]

    for share_int, share_lost, expected in test_cases:
        result = classify_drug(share_int, share_lost)
        status = "OK" if result == expected else "FAIL"
        print(f"  share_int={share_int}, share_lost={share_lost} → {result} [{status}]")

    print(f"\nValidation: {'PASSED' if validate_thresholds() else 'FAILED'}")
