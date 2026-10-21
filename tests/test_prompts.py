"""Tests for language feature injection into tutor prompts."""

from polyglot_coach_api.services.llm import _make_context
from polyglot_coach_api.services.prompts import TutorContext, build_tutor_prompt


def test_prompt_includes_language_features_and_focus():
    context = TutorContext(
        language="Spanish",
        language_code="es",
        level="A1",
        language_features=[
            {
                "id": "ser_estar",
                "name": "Ser vs. estar",
                "category": "grammar",
                "description": "Choose the correct copula.",
                "examples": ["Soy estudiante.", "Estoy cansado."],
            }
        ],
        feature_focus=["ser_estar"],
        teaching_notes=["Ser is used for identity."],
        script="Latin",
        direction="ltr",
        proficiency_framework="CEFR",
    )

    prompt = build_tutor_prompt(context, [])

    assert "language_feature: Ser vs. estar [grammar] — Choose the correct copula." in prompt
    assert "language_feature_example: Soy estudiante." in prompt
    assert "language_feature_example: Estoy cansado." in prompt
    assert "feature_focus: prioritize Ser vs. estar in this session" in prompt
    assert "language_teaching_note: Ser is used for identity." in prompt
    assert "language_script: Latin (ltr)" in prompt
    assert "proficiency_framework: CEFR" in prompt
    assert "Language-Specific Teaching" in prompt


def test_make_context_loads_pack_features_and_filters_focus():
    context, _ = _make_context(
        language="es",
        level="A1",
        feature_focus=["ser_estar", "grammatical_case"],
    )

    assert context.script == "Latin"
    assert context.direction == "ltr"
    assert context.proficiency_framework == "CEFR"
    assert context.teaching_notes
    assert {feature["id"] for feature in context.language_features or []} >= {
        "ser_estar",
        "gender_agreement",
    }
    assert context.feature_focus == ["ser_estar"]


def test_make_context_without_focus_has_none():
    context, _ = _make_context(language="fr", level="A1")
    assert context.feature_focus is None
    assert context.language_features


def test_profile_does_not_override_explicit_session_selection():
    from polyglot_coach_api.routers.learner import ProfileCreate, api_create_profile

    profile = api_create_profile(
        ProfileCreate(
            name="Session Learner",
            target_language="es",
            locale="es_MX",
            proficiency_level="A1",
        )
    )

    context, _ = _make_context(
        language="es",
        level="A1",
        locale="es_ES",
        profile_id=profile["id"],
    )

    assert context.locale == "es_ES"
    assert context.level == "A1"
