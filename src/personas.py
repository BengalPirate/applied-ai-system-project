"""
Specialization layer.

Personas adjust the scoring weights and tone of explanations to mimic
fine-tuned model behavior using a few-shot routing pattern. Output is
measurably different across personas for the same user_prefs (proven
in tests/test_personas.py and scripts/run_evaluation.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Persona:
    """A scoring + tone specialization."""
    name: str
    description: str
    weights: Dict[str, float]
    tone_prefix: str
    artist_repeat_penalty: float = 0.0  # penalty per repeat occurrence in top-K
    energy_floor: Optional[float] = None  # if set, songs below this take a penalty
    energy_floor_penalty: float = 0.0
    keywords: List[str] = field(default_factory=list)

    def with_overrides(self, **kwargs) -> "Persona":
        return Persona(**{**self.__dict__, **kwargs})


DEFAULT_WEIGHTS: Dict[str, float] = {
    "genre": 2.0,
    "mood": 1.0,
    "energy": 1.5,
    "acoustic": 0.5,
    "valence": 0.5,
}


PERSONAS: Dict[str, Persona] = {
    "default": Persona(
        name="default",
        description="Balanced match across all features.",
        weights=DEFAULT_WEIGHTS,
        tone_prefix="Recommended because",
        keywords=["default", "balanced"],
    ),
    "discovery": Persona(
        name="discovery",
        description="Lower genre weight, surface adjacent genres for cross-genre exploration.",
        weights={**DEFAULT_WEIGHTS, "genre": 0.7, "mood": 1.4, "valence": 0.9},
        tone_prefix="You might also enjoy",
        artist_repeat_penalty=0.4,
        keywords=["discover", "explore", "new", "variety", "different", "expand"],
    ),
    "comfort": Persona(
        name="comfort",
        description="Higher genre weight, narrow focus on familiar territory.",
        weights={**DEFAULT_WEIGHTS, "genre": 3.0, "mood": 1.2, "valence": 0.2},
        tone_prefix="Sticking with what you love:",
        keywords=["comfort", "familiar", "favorite", "usual", "same"],
    ),
    "workout": Persona(
        name="workout",
        description="High energy required, acoustic tracks down-weighted regardless of genre.",
        weights={**DEFAULT_WEIGHTS, "genre": 1.2, "mood": 0.8, "energy": 2.5, "acoustic": -0.5},
        tone_prefix="Workout pick:",
        energy_floor=0.7,
        energy_floor_penalty=2.0,
        keywords=["workout", "gym", "run", "running", "exercise", "training", "lift"],
    ),
    "study": Persona(
        name="study",
        description="Low energy, prefers acoustic and lofi/ambient/jazz.",
        weights={**DEFAULT_WEIGHTS, "genre": 1.0, "mood": 1.5, "energy": 2.0, "acoustic": 1.0, "valence": 0.2},
        tone_prefix="For deep focus:",
        energy_floor=None,
        keywords=["study", "focus", "concentration", "library", "homework", "reading"],
    ),
}


def get_persona(name: str) -> Persona:
    """Return persona by name. Falls back to default with a warning."""
    key = (name or "").lower().strip()
    if key in PERSONAS:
        return PERSONAS[key]
    logger.warning("persona %r not found; using default", name)
    return PERSONAS["default"]


def route_persona(context_text: str) -> Persona:
    """
    Few-shot keyword router that picks a persona from free-text context.

    This stands in for a fine-tuned classifier: keyword overlap routes the
    request to the persona whose few-shot example pool best matches the
    user's described situation. Reproducible and offline.
    """
    if not context_text:
        return PERSONAS["default"]
    text = context_text.lower()
    best_name = "default"
    best_score = 0
    for name, persona in PERSONAS.items():
        score = sum(1 for kw in persona.keywords if kw in text)
        if score > best_score:
            best_score = score
            best_name = name
    chosen = PERSONAS[best_name]
    logger.info("route_persona(%r) -> %s (score=%d)", context_text, chosen.name, best_score)
    return chosen


def format_explanation(persona: Persona, reasons: List[str]) -> str:
    """Apply the persona's tone prefix to the reason list."""
    body = "; ".join(reasons) if reasons else "no strong feature match"
    return f"{persona.tone_prefix} {body}"
