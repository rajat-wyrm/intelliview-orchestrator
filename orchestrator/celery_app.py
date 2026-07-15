"""Compatibility wrapper for the shared Celery application.

The worker-side Celery app already lives in the repository-level
``workers`` package. This module re-exports it from the orchestrator
package so callers can import it as ``from orchestrator.celery_app import celery_app``.
"""

from __future__ import annotations

from workers.celery_app import celery_app

__all__ = ["celery_app"]
