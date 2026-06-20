from fastapi import APIRouter

from analytics import get_engagement_overview, get_learning_summary, get_retention_report

router = APIRouter()


@router.get("/summary/{profile_id}")
def api_get_learning_summary(profile_id: int):
    return get_learning_summary(profile_id=profile_id)


@router.get("/retention/{profile_id}")
def api_get_retention_report(profile_id: int):
    return get_retention_report(profile_id=profile_id)


@router.get("/engagement/{profile_id}")
def api_get_engagement_overview(profile_id: int):
    return get_engagement_overview(profile_id=profile_id)
