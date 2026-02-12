# =============================================================================
# SUBSTITUTION COEFFICIENTS CONFIG MODULE - cross_pharm_market_analysis (Phase 2)
# =============================================================================
"""
Конфігурація параметрів Phase 2 Cross-Market Aggregation.

Модулі:
    - coverage_thresholds: Пороги coverage кластерів (HIGH/MEDIUM/LOW/INSUFFICIENT)

Модулі (будуть додані):
    - aggregation_params: Параметри агрегації коефіцієнтів
    - reliability_thresholds: Пороги reliability (CV)

Використання:
    from project_core.sub_coef_config import coverage_thresholds
    from project_core.sub_coef_config.coverage_thresholds import (
        COVERAGE_HIGH,
        get_coverage_cluster
    )
"""

from . import coverage_thresholds

__all__ = ['coverage_thresholds']
