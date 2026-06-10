# =============================================================================
# PROJECT CORE MODULE - cross_pharm_market_analysis
# =============================================================================
"""
Центральний модуль конфігурації та утиліт для мульти-ринкового аналізу.

Структура:
    data_config/       - Конфігурація даних (шляхи, колонки)
    did_config/        - Параметри Phase 1 DiD (пороги, NFC)
    sub_coef_config/   - Параметри Phase 2 Cross-Market (coverage)
    utility_functions/ - Утиліти (ETL, DiD)

Використання:
    # Спосіб 1: Прямий імпорт підмодулів
    from project_core.data_config.paths_config import PROJECT_ROOT
    from project_core.did_config.stockout_params import MIN_STOCKOUT_WEEKS
    from project_core.utility_functions.etl_utils import load_raw_data

    # Спосіб 2: Через головний модуль (рекомендовано)
    import project_core
    paths = project_core.paths_config
    stockout = project_core.stockout_params

Примітка:
    Для використання в exec_scripts/ додайте на початку скрипта:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
"""

# Імпорт конфігурацій для зручного доступу
try:
    # Data config
    from .data_config import paths_config
    from .data_config import column_mapping

    # DiD config (Phase 1)
    from .did_config import stockout_params
    from .did_config import classification_thresholds
    from .did_config import nfc_compatibility

    # Sub coef config (Phase 2)
    from .sub_coef_config import coverage_thresholds

    # Utility functions
    from .utility_functions import etl_utils
    from .utility_functions import did_utils

    __all__ = [
        'paths_config',
        'column_mapping',
        'stockout_params',
        'classification_thresholds',
        'nfc_compatibility',
        'coverage_thresholds',
        'etl_utils',
        'did_utils'
    ]

except ImportError as e:
    # Якщо імпорт не вдався (наприклад, при прямому запуску)
    print(f"Warning: Could not import all modules: {e}")
    __all__ = []
