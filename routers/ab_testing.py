"""A/B testing dashboard routes."""

from fastapi import APIRouter


def create_ab_testing_routes(ab_testing_framework) -> APIRouter:
    """
    Create routes for A/B testing dashboard data.
    """

    router = APIRouter()

    @router.get("/ab-testing/experiments")
    async def get_ab_testing_experiments():
        """
        Return active A/B experiment statistics.

        Returns experiment ID, variant, session count,
        and average score for each variant.
        """

        return ab_testing_framework.get_experiment_data()

    return router
