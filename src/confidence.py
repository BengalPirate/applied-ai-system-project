"""
Confidence scoring for the agent's final recommendation set.

Aggregates several reliability signals into a single 0.0-1.0 confidence
value plus a breakdown the agent uses to decide whether to refine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class ConfidenceReport:
    overall: float
    top_score_norm: float
    score_gap: float
    genre_diversity: float
    artist_diversity: float
    notes: List[str]

    def to_dict(self) -> Dict:
        return {
            "overall": round(self.overall, 3),
            "top_score_norm": round(self.top_score_norm, 3),
            "score_gap": round(self.score_gap, 3),
            "genre_diversity": round(self.genre_diversity, 3),
            "artist_diversity": round(self.artist_diversity, 3),
            "notes": self.notes,
        }


# Theoretical max score under default weights (genre+mood+energy+acoustic+valence)
DEFAULT_MAX_POSSIBLE = 5.5


def compute_confidence(
    scored: List[Tuple[Dict, float, str]],
    max_possible: float = DEFAULT_MAX_POSSIBLE,
) -> ConfidenceReport:
    """
    Compute confidence given the agent's ranked output.

    `scored` is the same shape as recommend_songs() returns:
    list of (song_dict, score, explanation) tuples.
    """
    notes: List[str] = []
    if not scored:
        return ConfidenceReport(0.0, 0.0, 0.0, 0.0, 0.0, ["empty result set"])

    top_score = scored[0][1]
    top_score_norm = max(0.0, min(1.0, top_score / max_possible))
    if top_score_norm < 0.4:
        notes.append("top score is low; user prefs may not be well-served by this catalog")

    if len(scored) >= 2:
        gap = scored[0][1] - scored[-1][1]
        score_gap = max(0.0, min(1.0, gap / max_possible))
    else:
        score_gap = 0.0

    genres = [s[0].get("genre", "?") for s in scored]
    artists = [s[0].get("artist", "?") for s in scored]
    genre_diversity = len(set(genres)) / len(genres)
    artist_diversity = len(set(artists)) / len(artists)
    if genre_diversity < 0.4:
        notes.append("low genre diversity in top results (filter-bubble risk)")
    if artist_diversity < 0.6:
        notes.append("artist over-representation detected")

    overall = (
        0.45 * top_score_norm
        + 0.20 * score_gap
        + 0.20 * genre_diversity
        + 0.15 * artist_diversity
    )
    return ConfidenceReport(
        overall=round(overall, 3),
        top_score_norm=top_score_norm,
        score_gap=score_gap,
        genre_diversity=genre_diversity,
        artist_diversity=artist_diversity,
        notes=notes,
    )


def confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.55:
        return "medium"
    if score >= 0.35:
        return "low"
    return "very-low"
