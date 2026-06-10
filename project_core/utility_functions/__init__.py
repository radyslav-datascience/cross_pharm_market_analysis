# =============================================================================
# UTILITY FUNCTIONS MODULE - cross_pharm_market_analysis
# =============================================================================
"""
Утиліти та функції для мульти-ринкового аналізу.

Модулі:
    - etl_utils: ETL функції (Extract-Transform-Load)
    - did_utils: DiD функції (Difference-in-Differences)
    - parallel_runner: Паралельне виконання per-market обробки

Використання:
    from project_core.utility_functions.etl_utils import (
        load_raw_data, parse_period_id, fill_gaps
    )
    from project_core.utility_functions.did_utils import (
        calculate_market_growth, calculate_lift, calculate_shares
    )
    from project_core.utility_functions.parallel_runner import (
        run_markets_parallel, process_single_market_pipeline
    )
"""

from . import etl_utils
from . import did_utils
from . import parallel_runner

__all__ = ['etl_utils', 'did_utils', 'parallel_runner']
