from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from polyglot_coach_api.validation import resolve_language_request
from polyglot_coach_shared.database import session_scope
from polyglot_coach_shared.models import LearnerProfile
from learner_memory import (
    get_profile,
    get_profile_by_id,
    get_progress,
    record_mistake,
    update_profile,
)

router = APIRouter()


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    native_language: str = Field(default="en", max_length=10)
    target_language: str = Field(max_length=10)
    locale: str | None = Field(default=None, max_length=10)
    proficiency_level: str | None = Field(default=None, max_length=5)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    native_language: str | None = Field(default=None, max_length=10)
    target_language: str | None = Field(default=None, max_length=10)
    locale: str | None = Field(default=None, max_length=10)
    proficiency_level: str | None = Field(default=None, max_length=5)


class MistakeCreate(BaseModel):
    profile_id: int = Field(gt=0)
    category: str = Field(max_length=50)
    user_input: str = Field(max_length=4000)
    correction: str = Field(max_length=4000)
    explanation: str | None = Field(default=None, max_length=4000)
    context: str | None = Field(default=None, max_length=4000)


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

    with session_scope() as session:
        existing = session.query(LearnerProfile).filter(LearnerProfile.name == body.name).first()
        if existing is not None:
            raise HTTPException(409, f"A profile named {body.name!r} already exists.")
        profile = LearnerProfile(**data)
        session.add(profile)
        session.flush()
        profile_id = profile.id
        if not isinstance(profile_id, int):
            raise HTTPException(500, "Profile id was not assigned.")

    result = get_profile_by_id(profile_id)
    if result is None:
        raise HTTPException(500, "Profile was created but could not be read back.")
    return result


@router.get("/profiles/{name}")
def api_get_profile(name: str):
    result = get_profile(name)
    if result is None:
        raise HTTPException(404, "Profile not found")
    return result


@router.patch("/profiles/{profile_id}")
def api_update_profile(profile_id: int, body: ProfileUpdate):
    with session_scope() as session:
        current = session.query(LearnerProfile).filter(LearnerProfile.id == profile_id).first()
        if current is None:
            raise HTTPException(404, "Profile not found")
        if body.name is not None and body.name != current.name:
            clash = session.query(LearnerProfile).filter(LearnerProfile.name == body.name).first()
            if clash is not None:
                raise HTTPException(409, f"A profile named {body.name!r} already exists.")

        target_language = body.target_language or current.target_language
        target_level = body.proficiency_level or current.proficiency_level
        target_locale = body.locale or current.locale

    resolve_language_request(
        target_language,
        level=target_level,
        locale=target_locale,
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
