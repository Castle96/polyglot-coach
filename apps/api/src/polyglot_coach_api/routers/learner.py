from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import LearnerProfile
from learner_memory import get_profile, get_progress, record_mistake, update_profile

router = APIRouter()


class ProfileCreate(BaseModel):
    name: str
    native_language: str
    target_language: str
    locale: str = "neutral"
    proficiency_level: str = "A1"


class ProfileUpdate(BaseModel):
    name: str | None = None
    native_language: str | None = None
    target_language: str | None = None
    locale: str | None = None
    proficiency_level: str | None = None


class MistakeCreate(BaseModel):
    profile_id: int
    category: str
    user_input: str
    correction: str
    explanation: str | None = None
    context: str | None = None


@router.post("/profiles", status_code=201)
def api_create_profile(body: ProfileCreate):
    session = get_session()
    profile = LearnerProfile(**body.model_dump())
    session.add(profile)
    session.commit()
    session.close()
    return get_profile(body.name)


@router.get("/profiles/{name}")
def api_get_profile(name: str):
    result = get_profile(name)
    if result is None:
        raise HTTPException(404, "Profile not found")
    return result


@router.patch("/profiles/{profile_id}")
def api_update_profile(profile_id: int, body: ProfileUpdate):
    result = update_profile(profile_id=profile_id, **body.model_dump(exclude_none=True))
    if result is None:
        raise HTTPException(404, "Profile not found")
    return result


@router.post("/mistakes")
def api_record_mistake(body: MistakeCreate):
    return record_mistake(**body.model_dump(exclude_none=True))


@router.get("/progress/{profile_id}")
def api_get_progress(profile_id: int, event_type: str | None = None, limit: int = 50):
    return get_progress(profile_id=profile_id, event_type=event_type, limit=limit)
