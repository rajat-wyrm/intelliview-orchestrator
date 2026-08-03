"""
Adaptive Risk Thresholding System

Provides modular threshold calculation strategies (fixed, percentile-based,
moving average, and rolling window) for dynamically adjusting interview risk
classification boundaries based on historical risk score distributions.
"""

from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskThresholds:
    """Class holding risk classification boundaries (0.0 <= low <= medium <= high <= 1.0)."""

    low: float
    medium: float
    high: float

    def __post_init__(self):
        # Validate boundaries
        low = min(max(float(self.low), 0.0), 1.0)
        medium = min(max(float(self.medium), low), 1.0)
        high = min(max(float(self.high), medium), 1.0)
        # Using object.__setattr__ because dataclass is frozen
        object.__setattr__(self, "low", round(low, 3))
        object.__setattr__(self, "medium", round(medium, 3))
        object.__setattr__(self, "high", round(high, 3))

    def as_dict(self) -> dict[str, float]:
        return {"low": self.low, "medium": self.medium, "high": self.high}


def calculate_quantile(data: list[float], quantile: float) -> float:
    """
    Computes quantile value using linear interpolation (0.0 <= quantile <= 1.0).
    Pure-Python implementation to avoid hard dependencies on numpy.
    """
    if not data:
        return 0.0
    if len(data) == 1:
        return float(data[0])

    sorted_data = sorted(data)
    q = min(max(float(quantile), 0.0), 1.0)
    idx = q * (len(sorted_data) - 1)
    lower = math.floor(idx)
    upper = math.ceil(idx)
    fraction = idx - lower

    if lower == upper:
        return float(sorted_data[lower])
    return float(sorted_data[lower] + fraction * (sorted_data[upper] - sorted_data[lower]))


class BaseThresholdStrategy(ABC):
    """Abstract base class for threshold calculation strategies."""

    @abstractmethod
    def calculate_thresholds(self, scores: list[float], fallback: RiskThresholds) -> RiskThresholds:
        """Calculate LOW, MEDIUM, and HIGH thresholds from historical scores."""


class FixedThresholdStrategy(BaseThresholdStrategy):
    """Fallback strategy using fixed static thresholds."""

    def __init__(
        self,
        low: float = 0.3,
        medium: float = 0.6,
        high: float = 0.8,
    ):
        self.fixed_thresholds = RiskThresholds(low=low, medium=medium, high=high)

    def calculate_thresholds(self, scores: list[float], fallback: RiskThresholds) -> RiskThresholds:
        return self.fixed_thresholds


class PercentileThresholdStrategy(BaseThresholdStrategy):
    """
    Calculates thresholds based on percentiles of historical score distribution.
    Default percentiles: 60% -> LOW boundary, 85% -> MEDIUM boundary, 95% -> HIGH boundary.
    """

    def __init__(
        self,
        low_percentile: float = 0.60,
        medium_percentile: float = 0.85,
        high_percentile: float = 0.95,
    ):
        self.low_pct = low_percentile
        self.medium_pct = medium_percentile
        self.high_pct = high_percentile

    def calculate_thresholds(self, scores: list[float], fallback: RiskThresholds) -> RiskThresholds:
        if not scores:
            return fallback

        low = calculate_quantile(scores, self.low_pct)
        medium = calculate_quantile(scores, self.medium_pct)
        high = calculate_quantile(scores, self.high_pct)

        # Enforce strictly non-decreasing boundaries
        low = min(low, 0.98)
        medium = max(medium, low + 0.01)
        high = max(high, medium + 0.01)

        return RiskThresholds(low=low, medium=medium, high=high)


class MovingAverageThresholdStrategy(BaseThresholdStrategy):
    """
    Calculates thresholds using historical mean score and standard deviation.
    LOW boundary: mean score
    MEDIUM boundary: mean + 1.0 * std
    HIGH boundary: mean + 2.0 * std
    """

    def __init__(
        self,
        low_std_mult: float = 0.0,
        medium_std_mult: float = 1.0,
        high_std_mult: float = 2.0,
    ):
        self.low_std_mult = low_std_mult
        self.medium_std_mult = medium_std_mult
        self.high_std_mult = high_std_mult

    def calculate_thresholds(self, scores: list[float], fallback: RiskThresholds) -> RiskThresholds:
        if not scores:
            return fallback

        n = len(scores)
        mean = sum(scores) / n
        variance = sum((x - mean) ** 2 for x in scores) / n if n > 1 else 0.0
        std = math.sqrt(variance)

        low = mean + self.low_std_mult * std
        medium = mean + self.medium_std_mult * std
        high = mean + self.high_std_mult * std

        return RiskThresholds(low=low, medium=medium, high=high)


class RollingWindowThresholdStrategy(BaseThresholdStrategy):
    """
    Applies an inner strategy over a rolling window of the most recent N interviews.
    """

    def __init__(
        self,
        inner_strategy: BaseThresholdStrategy,
        window_size: int = 100,
    ):
        self.inner_strategy = inner_strategy
        self.window_size = max(1, window_size)

    def calculate_thresholds(self, scores: list[float], fallback: RiskThresholds) -> RiskThresholds:
        if not scores:
            return fallback

        window_scores = scores[-self.window_size :]
        return self.inner_strategy.calculate_thresholds(window_scores, fallback)


class HistoricalRiskStore:
    """
    Stores historical interview risk scores in memory and persists to DB when available.
    """

    def __init__(self):
        self._in_memory_scores: list[dict[str, Any]] = []

    def record_score(self, session_id: str, risk_score: float, db_session: Any = None) -> None:
        """Record a newly generated risk score."""
        score_val = round(min(max(float(risk_score), 0.0), 1.0), 3)
        entry = {
            "session_id": session_id,
            "risk_score": score_val,
            "timestamp": datetime.now(timezone.utc),
        }
        self._in_memory_scores.append(entry)

        # Persist to database if db_session is provided or SessionLocal is accessible
        if db_session is not None:
            try:
                from database.models import RiskScoreHistory

                record = RiskScoreHistory(session_id=session_id, risk_score=score_val)
                db_session.add(record)
                db_session.commit()
            except Exception as err:
                logger.warning("Could not persist RiskScoreHistory to DB: %s", err)
        else:
            try:
                from database.db import SessionLocal
                from database.models import RiskScoreHistory

                with SessionLocal() as db:
                    record = RiskScoreHistory(session_id=session_id, risk_score=score_val)
                    db.add(record)
                    db.commit()
            except Exception:
                # Silently ignore if DB connection is unavailable in lightweight/offline mode
                pass

    def get_scores(self, limit: int | None = None, db_session: Any = None) -> list[float]:
        """Fetch historical scores ordered by timestamp/creation."""
        db_scores: list[float] = []
        if db_session is not None:
            try:
                from sqlalchemy import select

                from database.models import RiskScoreHistory

                stmt = select(RiskScoreHistory.risk_score).order_by(RiskScoreHistory.created_at.asc())
                if limit:
                    stmt = stmt.limit(limit)
                records = db_session.execute(stmt).scalars().all()
                db_scores = [float(r) for r in records]
            except Exception as err:
                logger.warning("Could not read RiskScoreHistory from DB: %s", err)
        else:
            try:
                from sqlalchemy import select

                from database.db import SessionLocal
                from database.models import RiskScoreHistory

                with SessionLocal() as db:
                    stmt = select(RiskScoreHistory.risk_score).order_by(RiskScoreHistory.created_at.asc())
                    if limit:
                        stmt = stmt.limit(limit)
                    records = db.execute(stmt).scalars().all()
                    db_scores = [float(r) for r in records]
            except Exception:
                pass

        if db_scores:
            return db_scores[-limit:] if limit else db_scores

        mem_scores = [e["risk_score"] for e in self._in_memory_scores]
        return mem_scores[-limit:] if limit else mem_scores

    def clear(self) -> None:
        """Clear in-memory scores (useful for testing)."""
        self._in_memory_scores.clear()


class AdaptiveThresholdManager:
    """
    Coordinates adaptive threshold calculation, strategy execution,
    minimum sample checks, and caching of calculated thresholds.
    """

    def __init__(
        self,
        store: HistoricalRiskStore | None = None,
        strategy_name: str = "percentile",
        min_samples: int = 10,
        fixed_low: float = 0.3,
        fixed_medium: float = 0.6,
        fixed_high: float = 0.8,
        low_percentile: float = 0.60,
        medium_percentile: float = 0.85,
        high_percentile: float = 0.95,
        rolling_window_size: int = 100,
        recalc_interval: int = 1,
    ):
        self.store = store or HistoricalRiskStore()
        self.strategy_name = strategy_name.lower()
        self.min_samples = max(1, min_samples)
        self.recalc_interval = max(1, recalc_interval)
        self.fallback = RiskThresholds(low=fixed_low, medium=fixed_medium, high=fixed_high)

        self._strategy = self._build_strategy(
            strategy_name=self.strategy_name,
            low_percentile=low_percentile,
            medium_percentile=medium_percentile,
            high_percentile=high_percentile,
            rolling_window_size=rolling_window_size,
            fixed_low=fixed_low,
            fixed_medium=fixed_medium,
            fixed_high=fixed_high,
        )

        self._cached_thresholds: RiskThresholds | None = None
        self._scores_since_last_recalc: int = 0

    def _build_strategy(
        self,
        strategy_name: str,
        low_percentile: float,
        medium_percentile: float,
        high_percentile: float,
        rolling_window_size: int,
        fixed_low: float,
        fixed_medium: float,
        fixed_high: float,
    ) -> BaseThresholdStrategy:
        if strategy_name == "fixed":
            return FixedThresholdStrategy(low=fixed_low, medium=fixed_medium, high=fixed_high)

        if strategy_name == "moving_average":
            return MovingAverageThresholdStrategy()

        if strategy_name == "rolling_window":
            inner = PercentileThresholdStrategy(
                low_percentile=low_percentile,
                medium_percentile=medium_percentile,
                high_percentile=high_percentile,
            )
            return RollingWindowThresholdStrategy(inner, window_size=rolling_window_size)

        # Default: percentile
        return PercentileThresholdStrategy(
            low_percentile=low_percentile,
            medium_percentile=medium_percentile,
            high_percentile=high_percentile,
        )

    def record_and_update(self, session_id: str, risk_score: float, db_session: Any = None) -> RiskThresholds:
        """Record score and update cached thresholds if recalculation is due."""
        self.store.record_score(session_id, risk_score, db_session=db_session)
        self._scores_since_last_recalc += 1

        if self._cached_thresholds is None or self._scores_since_last_recalc >= self.recalc_interval:
            self._cached_thresholds = self.get_current_thresholds(db_session=db_session)
            self._scores_since_last_recalc = 0

        return self._cached_thresholds

    def get_current_thresholds(self, db_session: Any = None) -> RiskThresholds:
        """
        Calculates and returns active thresholds.
        Returns fallback (static thresholds) if sample count < min_samples.
        """
        scores = self.store.get_scores(db_session=db_session)
        if len(scores) < self.min_samples:
            return self.fallback

        return self._strategy.calculate_thresholds(scores, fallback=self.fallback)
