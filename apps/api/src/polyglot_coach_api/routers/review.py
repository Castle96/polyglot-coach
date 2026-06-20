from fastapi import APIRouter
from pydantic import BaseModel

from review import get_due_words, record_review, schedule_review

router = APIRouter()


class ReviewSchedule(BaseModel):
    profile_id: int
    word: str
    language: str


class ReviewRecord(BaseModel):
    item_id: int
    quality: int


@router.get("/due/{profile_id}")
def api_get_due_words(profile_id: int, limit: int = 20):
    return get_due_words(profile_id=profile_id, limit=limit)


@router.post("/schedule")
def api_schedule_review(body: ReviewSchedule):
    return schedule_review(**body.model_dump())


@router.post("/record")
def api_record_review(body: ReviewRecord):
    return record_review(**body.model_dump())
