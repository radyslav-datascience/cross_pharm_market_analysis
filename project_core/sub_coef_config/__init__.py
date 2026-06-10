# =============================================================================
# SUBSTITUTION COEFFICIENTS CONFIG MODULE - cross_pharm_market_analysis (Phase 2)
# =============================================================================
"""
Конфігурація параметрів Phase 2 Cross-Market Aggregation.

Модулі:
    - coverage_thresholds: Пороги coverage кластерів (HIGH/MEDIUM/LOW/INSUFFICIENT)
    - reliability_thresholds: Пороги reliability (VARIATION_COEFFICIENT)

Модулі (будуть додані):
    - aggregation_params: Параметри агрегації коефіцієнтів

Використання:
    from project_core.sub_coef_config import coverage_thresholds, reliability_thresholds
    from project_core.sub_coef_config.coverage_thresholds import (
        COVERAGE_HIGH,
        get_coverage_cluster
    )
    from project_core.sub_coef_config.reliability_thresholds import (
        RELIABILITY_HIGH,
        get_reliability_class
    )
"""

from . import coverage_thresholds
from . import reliability_thresholds

__all__ = ['coverage_thresholds', 'reliability_thresholds']
