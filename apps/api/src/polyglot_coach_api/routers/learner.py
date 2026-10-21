from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from polyglot_coach_api.validation import resolve_language_request
from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import LearnerProfile
from learner_memory import get_profile, get_progress, record_mistake, update_profile

router = APIRouter()


class ProfileCreate(BaseModel):
    name: str
    native_language: str = "en"
    target_language: str
    locale: str | None = None
    proficiency_level: str | None = None


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
    _, level, locale = resolve_language_request(
        body.target_language,
        level=body.proficiency_level,
        locale=body.locale,
    )
    data = body.model_dump()
    data["proficiency_level"] = level
    data["locale"] = locale

    session = get_session()
    profile = LearnerProfile(**data)
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
    session = get_session()
    current = session.query(LearnerProfile).filter(LearnerProfile.id == profile_id).first()
    session.close()
    if current is None:
        raise HTTPException(404, "Profile not found")

    resolve_language_request(
        body.target_language or current.target_language,
        level=body.proficiency_level or current.proficiency_level,
        locale=body.locale or current.locale,
    )
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
