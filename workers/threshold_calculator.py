"""
Adaptive Threshold Calculator

Calculates dynamic LOW/MEDIUM/HIGH thresholds
using historical risk score distributions.

Current Strategy:
- Percentile based

Future Strategies:
- Moving Average
- Rolling Window
- Standard Deviation
"""

from __future__ import annotations

import math
import os
from workers.risk_history import RiskHistoryManager


class AdaptiveThresholdCalculator:
    """
    Calculates adaptive thresholds from historical scores.
    """

    # Fallback thresholds
    DEFAULT_LOW = 0.30
    DEFAULT_MEDIUM = 0.60
    DEFAULT_HIGH = 0.80

    # Minimum number of historical scores
    MIN_HISTORY = 30
    RECALCULATE_INTERVAL = int(os.getenv("RISK_RECALCULATE_INTERVAL","100",))
    
    # Percentiles
    LOW_PERCENTILE = int(os.getenv("LOW_PERCENTILE","60",))
    MEDIUM_PERCENTILE = int(os.getenv("MEDIUM_PERCENTILE","85",))
    HIGH_PERCENTILE = int(os.getenv("HIGH_PERCENTILE","95",))
    
    _cached_thresholds = None
    _last_history_size = 0

    @classmethod
    def get_thresholds(cls):

        history_size = RiskHistoryManager.history_size()

        if (
            cls._cached_thresholds is not None
            and history_size - cls._last_history_size < cls.RECALCULATE_INTERVAL
        ):
            return cls._cached_thresholds

        scores = RiskHistoryManager.get_all_scores()

        if len(scores) < cls.MIN_HISTORY:

            cls._cached_thresholds = {
                "low": cls.DEFAULT_LOW,
                "medium": cls.DEFAULT_MEDIUM,
                "high": cls.DEFAULT_HIGH,
            }

            return cls._cached_thresholds

        scores.sort()

        low = cls._percentile(scores, cls.LOW_PERCENTILE)

        medium = cls._percentile(
            scores,
            cls.MEDIUM_PERCENTILE,
        )

        high = cls._percentile(
            scores,
            cls.HIGH_PERCENTILE,
        )

        cls._cached_thresholds = {

            "low": round(low, 3),

            "medium": round(medium, 3),

            "high": round(high, 3),
        }

        cls._last_history_size = history_size

        return cls._cached_thresholds

    @staticmethod
    def _percentile(scores: list[float], percentile: float) -> float:
        """
        Calculate percentile using linear interpolation.
        """

        if not scores:
            return 0.0

        k = (len(scores) - 1) * percentile / 100

        f = math.floor(k)
        c = math.ceil(k)

        if f == c:
            return scores[int(k)]

        d0 = scores[f] * (c - k)
        d1 = scores[c] * (k - f)

        return d0 + d1