"""
Real-time moment tracking for interview sessions.

Tracks key events during interviews: questions asked, answers received,
risk detections, AI feedback, etc. Stores moments in Redis for fast
access and in PostgreSQL for persistence.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from orchestrator.redis_client import get_redis

logger = logging.getLogger(__name__)

MOMENT_TTL = 86400 * 7  # 7 days


class MomentType:
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    QUESTION_ASKED = "question_asked"
    ANSWER_RECEIVED = "answer_received"
    RISK_DETECTED = "risk_detected"
    AI_FEEDBACK = "ai_feedback"
    SCREEN_SHARE_START = "screen_share_start"
    SCREEN_SHARE_STOP = "screen_share_stop"
    RECORDING_START = "recording_start"
    RECORDING_STOP = "recording_stop"
    CANDIDATE_JOINED = "candidate_joined"
    CANDIDATE_LEFT = "candidate_left"
    INTERVIEWER_JOINED = "interviewer_joined"
    INTERVIEWER_LEFT = "interviewer_left"
    TECHNICAL_ISSUE = "technical_issue"
    PAUSE = "pause"
    RESUME = "resume"


class MomentTracker:
    def __init__(self):
        self._redis = None

    def _get_redis(self):
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    def track_moment(
        self,
        session_id: str,
        moment_type: str,
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        redis = self._get_redis()
        now = timestamp or datetime.now(timezone.utc)

        moment = {
            "id": f"moment_{uuid4().hex[:12]}",
            "session_id": session_id,
            "type": moment_type,
            "timestamp": now.isoformat(),
            "metadata": metadata or {},
        }

        try:
            key = f"moments:{session_id}"
            redis.rpush(key, json.dumps(moment))
            redis.expire(key, MOMENT_TTL)

            redis.zadd(
                "moments:timeline",
                {f"{session_id}:{moment['id']}": now.timestamp()},
            )
        except Exception as e:
            logger.warning(f"Failed to track moment in Redis: {e}")

        logger.info(f"Moment tracked: session={session_id} type={moment_type} metadata={metadata or {}}")

        return moment

    def get_session_moments(
        self,
        session_id: str,
        moment_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        redis = self._get_redis()

        try:
            key = f"moments:{session_id}"
            raw = redis.lrange(key, 0, -1)
            moments = [json.loads(r) for r in raw]

            if moment_type:
                moments = [m for m in moments if m.get("type") == moment_type]

            return moments[-limit:]
        except Exception as e:
            logger.warning(f"Failed to get moments from Redis: {e}")
            return []

    def get_timeline(
        self,
        session_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        moments = self.get_session_moments(session_id, limit=1000)

        if start_time:
            moments = [m for m in moments if datetime.fromisoformat(m["timestamp"]) >= start_time]
        if end_time:
            moments = [m for m in moments if datetime.fromisoformat(m["timestamp"]) <= end_time]

        moments.sort(key=lambda m: m["timestamp"])

        for i, moment in enumerate(moments):
            moment["index"] = i
            moment["duration"] = None
            if i > 0:
                prev_time = datetime.fromisoformat(moments[i - 1]["timestamp"])
                curr_time = datetime.fromisoformat(moment["timestamp"])
                moment["duration"] = (curr_time - prev_time).total_seconds() * 1000

        return moments

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        moments = self.get_session_moments(session_id, limit=1000)

        if not moments:
            return {"session_id": session_id, "total_moments": 0}

        moment_counts = {}
        for m in moments:
            t = m.get("type", "unknown")
            moment_counts[t] = moment_counts.get(t, 0) + 1

        first_moment = moments[0]
        last_moment = moments[-1]
        start_time = datetime.fromisoformat(first_moment["timestamp"])
        end_time = datetime.fromisoformat(last_moment["timestamp"])
        total_duration = (end_time - start_time).total_seconds()

        risk_moments = [m for m in moments if m.get("type") == MomentType.RISK_DETECTED]
        avg_risk = 0
        if risk_moments:
            risk_scores = [m.get("metadata", {}).get("risk_score", 0) for m in risk_moments]
            avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0

        return {
            "session_id": session_id,
            "total_moments": len(moments),
            "moment_counts": moment_counts,
            "start_time": first_moment["timestamp"],
            "end_time": last_moment["timestamp"],
            "total_duration_seconds": total_duration,
            "average_risk_score": avg_risk,
            "risk_detections": len(risk_moments),
        }

    def get_analytics(self, time_range_hours: int = 24) -> dict[str, Any]:
        redis = self._get_redis()

        try:
            cutoff = datetime.now(timezone.utc).timestamp() - (time_range_hours * 3600)
            session_ids = redis.zrangebyscore("moments:timeline", cutoff, "+inf")

            sessions = set()
            for sid_key in session_ids:
                sid = sid_key.decode().split(":")[0] if isinstance(sid_key, bytes) else sid_key.split(":")[0]
                sessions.add(sid)

            total_moments = 0
            moment_type_counts = {}
            for session_id in sessions:
                moments = self.get_session_moments(session_id, limit=1000)
                total_moments += len(moments)
                for m in moments:
                    t = m.get("type", "unknown")
                    moment_type_counts[t] = moment_type_counts.get(t, 0) + 1

            return {
                "time_range_hours": time_range_hours,
                "total_sessions": len(sessions),
                "total_moments": total_moments,
                "moment_type_distribution": moment_type_counts,
            }
        except Exception as e:
            logger.warning(f"Failed to get analytics: {e}")
            return {
                "time_range_hours": time_range_hours,
                "total_sessions": 0,
                "total_moments": 0,
                "moment_type_distribution": {},
            }


moment_tracker = MomentTracker()
