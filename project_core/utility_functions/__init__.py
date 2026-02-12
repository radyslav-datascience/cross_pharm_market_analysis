# =============================================================================
# UTILITY FUNCTIONS MODULE - cross_pharm_market_analysis
# =============================================================================
"""
Утиліти та функції для мульти-ринкового аналізу.

Модулі:
    - etl_utils: ETL функції (Extract-Transform-Load)
    - did_utils: DiD функції (Difference-in-Differences)

Використання:
    from project_core.utility_functions.etl_utils import (
        load_raw_data, parse_period_id, fill_gaps
    )
    from project_core.utility_functions.did_utils import (
        calculate_market_growth, calculate_lift, calculate_shares
    )
"""

from . import etl_utils
from . import did_utils

__all__ = ['etl_utils', 'did_utils']
