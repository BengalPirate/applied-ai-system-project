"""Tests for persona specialization."""

from src.personas import (
    DEFAULT_WEIGHTS,
    PERSONAS,
    format_explanation,
    get_persona,
    route_persona,
)


def test_all_personas_have_required_fields():
    for name, p in PERSONAS.items():
        assert p.name == name
        assert p.description
        assert "genre" in p.weights
        assert p.tone_prefix


def test_route_persona_picks_workout_for_gym_text():
    assert route_persona("I need music for the gym").name == "workout"


def test_route_persona_picks_study_for_library_text():
    assert route_persona("Concentrating on homework in the library").name == "study"


def test_route_persona_picks_discovery_for_explore_text():
    assert route_persona("I want to discover something new").name == "discovery"


def test_route_persona_falls_back_to_default():
    p = route_persona("xyzzy")
    assert p.name == "default"


def test_get_persona_unknown_falls_back_to_default():
    assert get_persona("does-not-exist").name == "default"


def test_personas_have_distinct_weights_from_default():
    """Specialization must produce measurably different weights."""
    for name, p in PERSONAS.items():
        if name == "default":
            continue
        assert p.weights != DEFAULT_WEIGHTS, f"{name} has identical weights to default"


def test_format_explanation_uses_persona_tone():
    p = get_persona("discovery")
    out = format_explanation(p, ["Genre match: pop (+0.7)"])
    assert out.startswith(p.tone_prefix)
    assert "Genre match" in out
