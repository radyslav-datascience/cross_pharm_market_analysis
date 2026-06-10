# =============================================================================
# DID CONFIG MODULE - cross_pharm_market_analysis (Phase 1)
# =============================================================================
"""
Конфігурація параметрів Phase 1 DiD аналізу для мульти-ринкового аналізу.

Модулі:
    - stockout_params: Параметри детекції stock-out
    - classification_thresholds: Пороги класифікації препаратів
    - nfc_compatibility: Матриця сумісності NFC1

Використання:
    from project_core.did_config import stockout_params
    from project_core.did_config.classification_thresholds import CRITICAL_THRESHOLD
    from project_core.did_config.nfc_compatibility import is_compatible
"""

from . import stockout_params
from . import classification_thresholds
from . import nfc_compatibility

__all__ = ['stockout_params', 'classification_thresholds', 'nfc_compatibility']
