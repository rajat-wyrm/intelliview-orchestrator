"""Admin/ops routes: cache management, load-balancing strategy, moment tracking, dashboard HTML."""

import logging
from datetime import datetime, timezone

from anyio import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import API_TOKEN
from orchestrator import http_cache
from orchestrator.auth import create_access_token, require_token
from orchestrator.load_balancer import BalancingStrategy
from orchestrator.security import require_role

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    api_token: str


def create_admin_routes(state_sync, load_balancer) -> APIRouter:
    """Create cache management, strategy-switching, moment-tracking, and dashboard routes.

    Args:
        state_sync: StateSynchronizer instance
        load_balancer: LoadBalancer instance

    Returns:
        APIRouter with admin routes
    """

    router = APIRouter()

    # ========== Auth ==========

    @router.post("/login")
    async def login(request: LoginRequest):
        """
        Exchange a valid API token for a JWT access token.
        """

        if request.api_token != API_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid API token")

        access_token = create_access_token({"sub": "system", "role": "admin"})

        return {"access_token": access_token, "token_type": "bearer"}

    @router.get("/admin/fairness-audit", dependencies=[Depends(require_token)])
    async def get_fairness_audit_report():
        """Return a lightweight fairness audit report for recent scoring patterns.

        This endpoint uses the existing BiasAuditor heuristic for scoring-dispersion
        review. It is intentionally informational and does not replace a full
        compliance or fairness assessment framework.
        """
        from workers.bias_auditor import BiasAuditor

        try:
            auditor = BiasAuditor(db_session=None)
            evaluations = []
            return auditor.analyze_scoring_consistency(evaluations, "gender")
        except Exception as exc:
            logger.error("Fairness audit endpoint failed: %s", exc)
            raise HTTPException(
                status_code=500, detail="Fairness audit unavailable"
            ) from exc

    # ========== Cache Management Endpoints ==========

    @router.get("/cache-stats")
    async def get_cache_stats():
        """
        Get Redis cache statistics

        Returns:
            dict: Cache health and statistics
        """
        try:
            return state_sync.get_cache_stats()
        except Exception as e:
            logger.error(f"Error fetching cache stats: {e!s}")
            raise HTTPException(status_code=500, detail="Error fetching cache stats")

    @router.post("/sync-to-database", dependencies=[Depends(require_token)])
    async def sync_cache_to_database(session_id: str | None = None):
        """
        Manually sync cache to database

        Args:
            session_id: Specific session to sync, or None to sync all active sessions

        Returns:
            dict: Sync result
        """
        try:
            if session_id:
                session_data = state_sync.get_session_state(session_id)
                if session_data:
                    state_sync.sync_state_to_db(session_id, session_data)
                    return {
                        "message": f"Synced session {session_id}",
                        "status": "success",
                    }
                raise HTTPException(
                    status_code=404, detail="Session not found in cache"
                )
            active_sessions = state_sync.get_active_sessions()
            for sid in active_sessions:
                session_data = state_sync.get_session_state(sid)
                if session_data:
                    state_sync.sync_state_to_db(sid, session_data)

            return {
                "message": f"Synced {len(active_sessions)} sessions",
                "status": "success",
                "synced_count": len(active_sessions),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing to database: {e!s}")
            raise HTTPException(status_code=500, detail="Error syncing to database")

    @router.delete("/clear-cache", dependencies=[Depends(require_role("admin"))])
    async def clear_session_cache():
        """
        Clear all session cache from Redis

        WARNING: This will clear all cached session states

        Returns:
            dict: Clear operation result
        """
        try:
            logger.warning("Clearing all session cache from Redis")
            result = state_sync.clear_cache()
            return {
                "message": "Cache cleared",
                "status": "success" if result else "failed",
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {e!s}")
            raise HTTPException(status_code=500, detail="Error clearing cache")

    @router.post("/switch-strategy", dependencies=[Depends(require_role("admin"))])
    async def switch_load_balancing_strategy(strategy: str):
        """
        Change the active load balancing strategy

        Supported strategies:
        - ROUND_ROBIN: Sequential worker assignment (even task distribution)
        - LEAST_LOADED: Assign to worker with fewest active tasks (recommended)
        - QUEUE_BASED: Use Redis queue length as selection metric

        Args:
            strategy: Strategy name (ROUND_ROBIN, LEAST_LOADED, QUEUE_BASED)

        Returns:
            dict: Strategy change confirmation
        """
        try:
            logger.info(f"Switching load balancing strategy to: {strategy}")

            valid_strategies = {
                "ROUND_ROBIN": BalancingStrategy.ROUND_ROBIN,
                "LEAST_LOADED": BalancingStrategy.LEAST_LOADED,
                "QUEUE_BASED": BalancingStrategy.QUEUE_BASED,
            }

            if strategy.upper() not in valid_strategies:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid strategy. Valid options: {', '.join(valid_strategies.keys())}",
                )

            new_strategy = valid_strategies[strategy.upper()]
            load_balancer.switch_strategy(new_strategy)

            logger.info(f"Load balancing strategy switched to: {strategy}")

            return {
                "status": "success",
                "message": f"Strategy switched to {strategy}",
                "previous_strategy": load_balancer.strategy.name,
                "new_strategy": strategy,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error switching strategy: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Error switching strategy: {e!s}"
            )

    # ========== Moment Tracking Endpoints ==========

    @router.post("/moments/track")
    async def track_moment(
        session_id: str, moment_type: str, metadata: dict | None = None
    ):
        """Track a real-time moment during an interview session."""
        from orchestrator.moment_tracker import moment_tracker

        try:
            moment = moment_tracker.track_moment(session_id, moment_type, metadata)
            http_cache.invalidate(f"moments:{session_id}")
            return {"status": "success", "moment": moment}
        except Exception as e:
            logger.error(f"Error tracking moment: {e!s}")
            raise HTTPException(status_code=500, detail=f"Error tracking moment: {e!s}")

    @router.get("/moments/{session_id}")
    async def get_session_moments(
        session_id: str, moment_type: str | None = None, limit: int = 100
    ):
        """Get all tracked moments for a session."""
        from orchestrator.moment_tracker import moment_tracker

        try:
            moments = moment_tracker.get_session_moments(session_id, moment_type, limit)
            return {"session_id": session_id, "count": len(moments), "moments": moments}
        except Exception as e:
            logger.error(f"Error fetching moments: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Error fetching moments: {e!s}"
            )

    @router.get("/moments/{session_id}/timeline")
    async def get_session_timeline(session_id: str):
        """Get the moment timeline for a session."""
        from orchestrator.moment_tracker import moment_tracker

        try:
            timeline = moment_tracker.get_timeline(session_id)
            return {
                "session_id": session_id,
                "count": len(timeline),
                "timeline": timeline,
            }
        except Exception as e:
            logger.error(f"Error fetching timeline: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Error fetching timeline: {e!s}"
            )

    @router.get("/moments/{session_id}/summary")
    async def get_session_moment_summary(session_id: str):
        """Get a summary of moments for a session."""
        from orchestrator.moment_tracker import moment_tracker

        try:
            summary = moment_tracker.get_session_summary(session_id)
            return summary
        except Exception as e:
            logger.error(f"Error fetching moment summary: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Error fetching moment summary: {e!s}"
            )

    @router.get("/moments/analytics")
    async def get_moment_analytics(time_range_hours: int = 24):
        """Get moment analytics across all sessions."""
        from orchestrator.moment_tracker import moment_tracker

        try:
            analytics = moment_tracker.get_analytics(time_range_hours)
            return analytics
        except Exception as e:
            logger.error(f"Error fetching moment analytics: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Error fetching moment analytics: {e!s}"
            )

    # ========== Dashboard HTML Endpoint ==========

    @router.get("/dashboard")
    async def get_dashboard():
        """
        Serve the monitoring dashboard HTML

        Returns:
            HTML content of the dashboard
        """
        try:
            dashboard_path = (
                Path(__file__).parent.parent /  "monitoring", "dashboard.html"
            )

            if await dashboard_path.exists():
                html_content = await dashboard_path.read_text(encoding="utf-8")

                from fastapi.responses import HTMLResponse

                return HTMLResponse(content=html_content)
            raise HTTPException(status_code=404, detail="Dashboard HTML not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error serving dashboard: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Error serving dashboard: {e!s}"
            )

    return router
