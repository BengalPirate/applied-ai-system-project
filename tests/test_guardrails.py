"""Tests for guardrail validators."""

import pytest

from src.guardrails import (
    GuardrailError,
    assert_valid_user_prefs,
    validate_song_catalog,
    validate_user_prefs,
)


def test_valid_prefs_pass():
    errors, warnings = validate_user_prefs(
        {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}
    )
    assert errors == []


def test_missing_required_keys_returns_errors():
    errors, _ = validate_user_prefs({"genre": "pop"})
    assert any("missing required keys" in e for e in errors)


def test_out_of_range_energy_errors():
    errors, _ = validate_user_prefs({"genre": "pop", "mood": "happy", "energy": 1.5})
    assert any("energy" in e for e in errors)


def test_unknown_mood_warns():
    _, warnings = validate_user_prefs({"genre": "pop", "mood": "transcendent", "energy": 0.5})
    assert any("transcendent" in w for w in warnings)


def test_assert_valid_raises_on_error():
    with pytest.raises(GuardrailError):
        assert_valid_user_prefs({"genre": "pop"})


def test_assert_valid_returns_warnings_when_no_errors():
    out = assert_valid_user_prefs(
        {"genre": "pop", "mood": "happy", "energy": 0.5}
    )
    assert isinstance(out, list)


def test_validate_song_catalog_rejects_empty():
    with pytest.raises(GuardrailError):
        validate_song_catalog([])


def test_validate_song_catalog_warns_on_missing_fields():
    warnings = validate_song_catalog([{"id": 1, "title": "x"}])
    assert warnings
