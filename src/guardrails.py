"""
Input validation and runtime guardrails.

The agent calls validate_user_prefs() before each run so malformed input
fails loudly instead of producing silently wrong recommendations.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from src.logging_setup import get_logger

logger = get_logger(__name__)


class GuardrailError(ValueError):
    """Raised when user input fails validation in a way the agent cannot recover from."""


REQUIRED_KEYS = {"genre", "mood", "energy"}
NUMERIC_RANGES = {
    "energy": (0.0, 1.0),
    "valence": (0.0, 1.0),
}
KNOWN_MOODS = {
    "happy", "chill", "intense", "relaxed", "focused", "energetic",
    "sad", "moody", "peaceful", "romantic", "rebellious", "dark",
    "nostalgic", "experimental",
}


def validate_user_prefs(prefs: Dict) -> Tuple[List[str], List[str]]:
    """
    Validate user preferences.

    Returns (errors, warnings). Errors block the run; warnings are surfaced
    in the trace but the agent proceeds.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(prefs, dict):
        raise GuardrailError(f"user_prefs must be a dict, got {type(prefs).__name__}")

    missing = REQUIRED_KEYS - set(prefs)
    if missing:
        errors.append(f"missing required keys: {sorted(missing)}")

    for key, (lo, hi) in NUMERIC_RANGES.items():
        if key in prefs:
            v = prefs[key]
            if not isinstance(v, (int, float)):
                errors.append(f"{key} must be numeric, got {type(v).__name__}")
            elif not (lo <= v <= hi):
                errors.append(f"{key}={v} outside [{lo}, {hi}]")

    if "genre" in prefs and not isinstance(prefs["genre"], str):
        errors.append(f"genre must be a string, got {type(prefs['genre']).__name__}")

    if "mood" in prefs:
        mood = prefs["mood"]
        if not isinstance(mood, str):
            errors.append(f"mood must be a string, got {type(mood).__name__}")
        elif mood.lower() not in KNOWN_MOODS:
            warnings.append(
                f"mood {mood!r} not in known set; recommendations may have low confidence"
            )

    if "likes_acoustic" in prefs and not isinstance(prefs["likes_acoustic"], bool):
        errors.append("likes_acoustic must be a bool")

    if errors:
        logger.error("user_prefs validation failed: %s", errors)
    if warnings:
        logger.warning("user_prefs validation warnings: %s", warnings)
    return errors, warnings


def assert_valid_user_prefs(prefs: Dict) -> List[str]:
    """Validate and raise on errors. Returns the (possibly empty) warnings list."""
    errors, warnings = validate_user_prefs(prefs)
    if errors:
        raise GuardrailError("; ".join(errors))
    return warnings


def validate_song_catalog(songs: List[Dict]) -> List[str]:
    """Sanity-check the catalog. Returns warnings (does not raise)."""
    warnings: List[str] = []
    if not songs:
        raise GuardrailError("song catalog is empty")
    required = {"id", "title", "artist", "genre", "mood", "energy", "acousticness"}
    for i, song in enumerate(songs):
        missing = required - set(song)
        if missing:
            warnings.append(f"song[{i}] missing fields: {sorted(missing)}")
    if len(warnings) > 0:
        logger.warning("catalog validation produced %d warnings", len(warnings))
    return warnings
