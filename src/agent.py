"""
MoodMatch Agent: agentic workflow over the music catalog.

The agent runs a Plan -> Act -> Reflect -> (optionally) Refine loop.
Every step is captured in an AgentTrace so the workflow is observable
in the demo, in tests, and in the evaluation harness.

Required AI feature: agentic workflow with observable intermediate steps.
Stretch coverage:
  * RAG (the Plan step retrieves from the knowledge base and the
    retrieved context shapes weight choices in the Refine step)
  * Specialization (Persona weights and tone)
  * Confidence-driven self-correction (Reflect)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.confidence import ConfidenceReport, compute_confidence, confidence_label
from src.guardrails import assert_valid_user_prefs, validate_song_catalog
from src.logging_setup import get_logger
from src.personas import (
    DEFAULT_WEIGHTS,
    Persona,
    format_explanation,
    get_persona,
    route_persona,
)
from src.recommender import recommend_with_weights
from src.retriever import KnowledgeRetriever, RetrievalHit

logger = get_logger(__name__)


@dataclass
class AgentStep:
    name: str  # plan | act | reflect | refine | finalize
    detail: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "detail": self.detail}


@dataclass
class Recommendation:
    song: Dict
    score: float
    explanation: str

    def to_dict(self) -> Dict:
        return {
            "title": self.song.get("title"),
            "artist": self.song.get("artist"),
            "genre": self.song.get("genre"),
            "mood": self.song.get("mood"),
            "energy": self.song.get("energy"),
            "score": round(self.score, 3),
            "explanation": self.explanation,
        }


@dataclass
class AgentResult:
    persona: Persona
    user_prefs: Dict
    recommendations: List[Recommendation]
    confidence: ConfidenceReport
    confidence_label: str
    iterations: int
    trace: List[AgentStep] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "persona": self.persona.name,
            "user_prefs": self.user_prefs,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "confidence": self.confidence.to_dict(),
            "confidence_label": self.confidence_label,
            "iterations": self.iterations,
            "warnings": self.warnings,
            "trace": [s.to_dict() for s in self.trace],
        }


class MoodMatchAgent:
    """
    Agentic recommender. Each call to .run() executes the full loop and
    returns an AgentResult whose .trace lists every observable step.
    """

    def __init__(
        self,
        songs: List[Dict],
        retriever: Optional[KnowledgeRetriever] = None,
        max_iterations: int = 2,
        confidence_threshold: float = 0.55,
    ):
        validate_song_catalog(songs)
        self.songs = songs
        self.retriever = retriever or KnowledgeRetriever()
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        logger.info(
            "MoodMatchAgent ready: %d songs, max_iter=%d, threshold=%.2f",
            len(songs), max_iterations, confidence_threshold,
        )

    def run(
        self,
        user_prefs: Dict,
        persona_name: Optional[str] = None,
        context_text: Optional[str] = None,
        k: int = 5,
    ) -> AgentResult:
        """Execute the full Plan -> Act -> Reflect -> Refine loop."""
        warnings = list(assert_valid_user_prefs(user_prefs))
        trace: List[AgentStep] = []

        # -------- PLAN --------
        persona = self._select_persona(persona_name, context_text, user_prefs)
        hits = self.retriever.retrieve_for_profile(user_prefs, persona.name, top_k=3)
        weights = dict(persona.weights)
        plan_detail = {
            "persona": persona.name,
            "persona_description": persona.description,
            "starting_weights": dict(weights),
            "retrieved_passages": [h.to_dict() for h in hits],
            "context_text": context_text,
        }
        trace.append(AgentStep("plan", plan_detail))
        logger.info("PLAN: persona=%s, %d KB hits", persona.name, len(hits))

        # -------- ACT --------
        ranked = self._score(user_prefs, weights, persona, k)
        trace.append(AgentStep("act", {
            "weights": dict(weights),
            "top": [(s["title"], round(score, 3)) for s, score, _ in ranked],
        }))

        # -------- REFLECT --------
        report = compute_confidence(ranked)
        trace.append(AgentStep("reflect", {
            "confidence": report.to_dict(),
            "label": confidence_label(report.overall),
            "threshold": self.confidence_threshold,
        }))
        logger.info(
            "REFLECT: confidence=%.3f (%s), notes=%s",
            report.overall, confidence_label(report.overall), report.notes,
        )

        iterations = 1

        # -------- REFINE (conditional) --------
        if report.overall < self.confidence_threshold and iterations < self.max_iterations:
            adjusted = self._refine_weights(weights, report, persona, hits)
            artist_penalty = self._refine_artist_penalty(persona, report)
            trace.append(AgentStep("refine", {
                "old_weights": dict(weights),
                "new_weights": dict(adjusted),
                "artist_repeat_penalty": artist_penalty,
                "rationale": self._refine_rationale(report, adjusted, weights),
            }))
            weights = adjusted
            ranked = self._score(user_prefs, weights, persona, k, artist_repeat_penalty=artist_penalty)
            new_report = compute_confidence(ranked)
            trace.append(AgentStep("reflect", {
                "confidence": new_report.to_dict(),
                "label": confidence_label(new_report.overall),
                "threshold": self.confidence_threshold,
                "iteration": 2,
            }))
            report = new_report
            iterations = 2

        # -------- FINALIZE --------
        recommendations = [
            Recommendation(
                song=song,
                score=score,
                explanation=format_explanation(persona, [reason_str]),
            )
            for song, score, reason_str in ranked
        ]
        trace.append(AgentStep("finalize", {
            "iterations": iterations,
            "final_confidence": report.to_dict(),
        }))

        return AgentResult(
            persona=persona,
            user_prefs=dict(user_prefs),
            recommendations=recommendations,
            confidence=report,
            confidence_label=confidence_label(report.overall),
            iterations=iterations,
            trace=trace,
            warnings=warnings,
        )

    # -- helpers -------------------------------------------------------
    def _select_persona(self, name: Optional[str], context: Optional[str], prefs: Dict) -> Persona:
        if name:
            return get_persona(name)
        # Build a routing context from any free-text plus prefs values.
        parts: List[str] = []
        if context:
            parts.append(context)
        for v in (prefs.get("mood"), prefs.get("genre")):
            if isinstance(v, str):
                parts.append(v)
        return route_persona(" ".join(parts))

    def _score(
        self,
        user_prefs: Dict,
        weights: Dict[str, float],
        persona: Persona,
        k: int,
        artist_repeat_penalty: Optional[float] = None,
    ) -> List[Tuple[Dict, float, str]]:
        repeat_pen = (
            artist_repeat_penalty
            if artist_repeat_penalty is not None
            else persona.artist_repeat_penalty
        )
        return recommend_with_weights(
            user_prefs,
            self.songs,
            weights,
            k=k,
            energy_floor=persona.energy_floor,
            energy_floor_penalty=persona.energy_floor_penalty,
            artist_repeat_penalty=repeat_pen,
        )

    @staticmethod
    def _refine_weights(
        weights: Dict[str, float],
        report: ConfidenceReport,
        persona: Persona,
        hits: List[RetrievalHit],
    ) -> Dict[str, float]:
        """Adjust weights based on confidence breakdown and retrieved context."""
        new = dict(weights)

        # Filter-bubble fix: if genre diversity is low, drop the genre weight.
        if report.genre_diversity < 0.4:
            new["genre"] = max(0.5, new.get("genre", 2.0) * 0.6)
            new["mood"] = new.get("mood", 1.0) * 1.2
        # Low top-score-norm: user prefs may not match well; widen by lowering genre,
        # raise mood/valence to find emotional adjacency.
        if report.top_score_norm < 0.4:
            new["genre"] = max(0.5, new.get("genre", 2.0) * 0.7)
            new["valence"] = new.get("valence", 0.5) + 0.3

        # Pull a hint from the retrieved context: if a passage tagged with
        # "fallback" or "mood" was retrieved, nudge mood up.
        for hit in hits:
            tags = " ".join(hit.passage.tags)
            if "fallback" in tags or "mapping" in tags:
                new["mood"] = new.get("mood", 1.0) + 0.2
                break
        return new

    @staticmethod
    def _refine_artist_penalty(persona: Persona, report: ConfidenceReport) -> float:
        if report.artist_diversity < 0.6:
            return max(persona.artist_repeat_penalty, 0.5)
        return persona.artist_repeat_penalty

    @staticmethod
    def _refine_rationale(
        report: ConfidenceReport,
        new: Dict[str, float],
        old: Dict[str, float],
    ) -> List[str]:
        notes: List[str] = []
        if report.genre_diversity < 0.4:
            notes.append(
                f"low genre diversity ({report.genre_diversity:.2f}); "
                f"reduced genre weight {old.get('genre'):.2f} -> {new.get('genre'):.2f}"
            )
        if report.top_score_norm < 0.4:
            notes.append(
                f"low top-score ({report.top_score_norm:.2f}); "
                f"raised valence weight to {new.get('valence'):.2f}"
            )
        if report.artist_diversity < 0.6:
            notes.append(
                f"low artist diversity ({report.artist_diversity:.2f}); "
                f"applying artist-repeat penalty"
            )
        if not notes:
            notes.append("confidence below threshold but no specific weakness diagnosed")
        return notes
