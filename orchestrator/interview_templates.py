"""
Interview Templates Module

Manages interview structure templates, usage tracking, and success rates
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select

from database.db import get_db_session
from database.models import InterviewTemplate
from orchestrator.time_utils import utcnow

logger = logging.getLogger(__name__)


class InterviewTemplateManager:
    """Manages interview templates and their usage statistics"""

    INTERVIEW_TYPES = ["technical", "behavioral", "mixed"]

    def __init__(self):
        pass

    def create_template(
        self,
        name: str,
        interview_type: str,
        description: str | None = None,
        duration_minutes: int = 60,
        question_count: int = 10,
        category_distribution: dict[str, float] | None = None,
        difficulty_distribution: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Create a new interview template"""

        interview_type = interview_type.strip().lower()

        if interview_type not in self.INTERVIEW_TYPES:
            raise ValueError(
                f"Invalid interview type: {interview_type}. Must be one of: {self.INTERVIEW_TYPES}"
            )

        template_id = f"tmpl_{uuid.uuid4().hex[:12]}"
        now = utcnow()

        with get_db_session() as db:
            template = InterviewTemplate(
                template_id=template_id,
                name=name.strip(),
                description=description,
                interview_type=interview_type,
                duration_minutes=duration_minutes,
                question_count=question_count,
                category_distribution=category_distribution or {},
                difficulty_distribution=difficulty_distribution or {},
                usage_count=0,
                success_rate=None,
                created_at=now,
                updated_at=now,
            )

            db.add(template)

        logger.info(
            f"Created template {template_id}: {name} ({interview_type})"
        )

        return {
            "template_id": template_id,
            "name": name.strip(),
            "description": description,
            "interview_type": interview_type,
            "duration_minutes": duration_minutes,
            "question_count": question_count,
            "category_distribution": category_distribution or {},
            "difficulty_distribution": difficulty_distribution or {},
            "usage_count": 0,
            "success_rate": None,
            "created_at": now.isoformat(),
        }

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        """Get a template by ID"""

        with get_db_session() as db:
            template = db.execute(
                select(InterviewTemplate).where(
                    InterviewTemplate.template_id == template_id
                )
            ).scalar_one_or_none()

            if not template:
                return None

            return {
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "interview_type": template.interview_type,
                "duration_minutes": template.duration_minutes,
                "question_count": template.question_count,
                "category_distribution": template.category_distribution or {},
                "difficulty_distribution": template.difficulty_distribution or {},
                "usage_count": template.usage_count,
                "success_rate": template.success_rate,
                "created_at": (
                    template.created_at.isoformat()
                    if template.created_at
                    else None
                ),
            }

    def list_templates(
        self,
        interview_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List templates with optional type filter"""

        with get_db_session() as db:
            stmt = select(InterviewTemplate)

            if interview_type:
                stmt = stmt.where(
                    InterviewTemplate.interview_type
                    == interview_type.strip().lower()
                )

            stmt = stmt.order_by(
                InterviewTemplate.created_at.desc()
            ).limit(limit)

            rows = db.execute(stmt).scalars().all()

            return [
                {
                    "template_id": t.template_id,
                    "name": t.name,
                    "description": t.description,
                    "interview_type": t.interview_type,
                    "duration_minutes": t.duration_minutes,
                    "question_count": t.question_count,
                    "category_distribution": t.category_distribution or {},
                    "difficulty_distribution": t.difficulty_distribution or {},
                    "usage_count": t.usage_count,
                    "success_rate": t.success_rate,
                    "created_at": (
                        t.created_at.isoformat()
                        if t.created_at
                        else None
                    ),
                }
                for t in rows
            ]

    def record_usage(
        self,
        template_id: str,
        success: bool = True,
    ) -> bool:
        """Record a template usage and update success rate"""

        with get_db_session() as db:
            template = db.execute(
                select(InterviewTemplate).where(
                    InterviewTemplate.template_id == template_id
                )
            ).scalar_one_or_none()

            if not template:
                return False

            template.usage_count = (template.usage_count or 0) + 1

            count = template.usage_count

            if template.success_rate is None:
                template.success_rate = 1.0 if success else 0.0
            else:
                template.success_rate = (
                    (
                        template.success_rate * (count - 1)
                    )
                    + (1.0 if success else 0.0)
                ) / count

            template.updated_at = utcnow()

            return True


interview_template_manager = InterviewTemplateManager()