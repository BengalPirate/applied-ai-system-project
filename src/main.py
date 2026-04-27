"""
Command line demo for MoodMatch Agent.

Runs three end-to-end agent invocations covering:
  1. an auto-routed persona based on a free-text context
  2. an explicit persona override (discovery mode)
  3. a forced-refine audit case that visibly exercises the agent loop

Run with:
    python -m src.main
"""

from __future__ import annotations

import json
from typing import Dict, Optional

from src.agent import AgentResult, MoodMatchAgent
from src.recommender import load_songs


SEPARATOR = "=" * 78


def _print_trace(result: AgentResult) -> None:
    print("Trace:")
    for i, step in enumerate(result.trace, 1):
        print(f"  [{i}] {step.name}")
        if step.name == "plan":
            print(f"      persona: {step.detail['persona']} -- {step.detail['persona_description']}")
            print(f"      starting weights: {step.detail['starting_weights']}")
            for hit in step.detail["retrieved_passages"]:
                print(f"      RAG hit ({hit['score']}): {hit['title']}")
        elif step.name == "act":
            iter_num = step.detail.get("iteration", 1)
            print(f"      iteration: {iter_num}")
            print(f"      weights: {step.detail['weights']}")
            print(f"      max possible score: {step.detail['max_possible_score']}")
            for title, score in step.detail["top"][:3]:
                print(f"      -> {title} ({score})")
        elif step.name == "reflect":
            c = step.detail["confidence"]
            print(
                f"      confidence={c['overall']} ({step.detail['label']}) "
                f"top_score_norm={c['top_score_norm']} genre_div={c['genre_diversity']} "
                f"artist_div={c['artist_diversity']}"
            )
            for note in c["notes"]:
                print(f"      note: {note}")
        elif step.name == "refine":
            print(f"      old: {step.detail['old_weights']}")
            print(f"      new: {step.detail['new_weights']}")
            for r in step.detail["rationale"]:
                print(f"      reason: {r}")
        elif step.name == "finalize":
            print(f"      iterations={step.detail['iterations']}")


def _print_result(label: str, result: AgentResult) -> None:
    print(f"\n{SEPARATOR}\n{label}\n{SEPARATOR}")
    print(f"User preferences: {json.dumps(result.user_prefs)}")
    print(f"Persona: {result.persona.name} ({result.persona.description})")
    if result.warnings:
        print(f"Guardrail warnings: {result.warnings}")
    print(f"Confidence: {result.confidence.overall:.3f} ({result.confidence_label})")
    if result.confidence.notes:
        for n in result.confidence.notes:
            print(f"  note: {n}")
    print(f"Iterations: {result.iterations}")
    print("\nTop recommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(
            f"  {i}. {rec.song['title']} -- {rec.song.get('artist','?')} "
            f"[{rec.song.get('genre','?')}/{rec.song.get('mood','?')} "
            f"energy={rec.song.get('energy',0):.2f}] score={rec.score:.2f}"
        )
        print(f"     {rec.explanation}")
    print()
    _print_trace(result)


def run_demo(
    agent: MoodMatchAgent,
    label: str,
    user_prefs: Dict,
    persona: Optional[str] = None,
    context_text: Optional[str] = None,
) -> AgentResult:
    result = agent.run(user_prefs=user_prefs, persona_name=persona, context_text=context_text)
    _print_result(label, result)
    return result


def main() -> None:
    songs = load_songs("data/songs.csv")
    agent = MoodMatchAgent(songs=songs)

    # 1. Auto-routed persona via free-text context
    run_demo(
        agent,
        label="Demo 1: Lofi study session (auto-routed persona)",
        user_prefs={"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True},
        context_text="I need quiet music for a long library study session",
    )

    # 2. Explicit persona override (discovery mode)
    run_demo(
        agent,
        label="Demo 2: Pop fan in Discovery mode (cross-genre exploration)",
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.85},
        persona="discovery",
    )

    # 3. Force the refine step for demonstration/audit purposes.
    strict_agent = MoodMatchAgent(songs=songs, confidence_threshold=0.99)
    run_demo(
        strict_agent,
        label="Demo 3: Forced refine audit case (strict threshold shows self-correction)",
        user_prefs={"genre": "blues", "mood": "sad", "energy": 0.3},
        persona="default",
    )


if __name__ == "__main__":
    main()
