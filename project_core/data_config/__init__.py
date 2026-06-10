# =============================================================================
# DATA CONFIG MODULE - cross_pharm_market_analysis
# =============================================================================
"""
Конфігурація даних для мульти-ринкового аналізу.

Модулі:
    - paths_config: Шляхи до папок та файлів
    - column_mapping: Маппінг колонок CSV

Використання:
    from project_core.data_config import paths_config
    from project_core.data_config.column_mapping import COLUMN_RENAME_MAP
"""

from . import paths_config
from . import column_mapping

__all__ = ['paths_config', 'column_mapping']
