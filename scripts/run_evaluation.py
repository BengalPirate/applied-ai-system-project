"""
Evaluation harness for the MoodMatch Agent.

Runs a fixed suite of test cases through the full agentic workflow,
records pass/fail per assertion, aggregates confidence statistics,
and writes a human-readable report to assets/evaluation_report.md.

Run with:
    python -m scripts.run_evaluation
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from src.agent import AgentResult, MoodMatchAgent
from src.confidence import confidence_label
from src.recommender import load_songs

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "assets" / "evaluation_report.md"


@dataclass
class Assertion:
    name: str
    check: Callable[[AgentResult], bool]
    description: str = ""


@dataclass
class TestCase:
    name: str
    user_prefs: Dict
    persona: Optional[str] = None
    context_text: Optional[str] = None
    assertions: List[Assertion] = field(default_factory=list)


def top_genre_is(expected: str) -> Assertion:
    return Assertion(
        name=f"top_genre=={expected}",
        check=lambda r: bool(r.recommendations) and r.recommendations[0].song.get("genre") == expected,
        description=f"Top recommendation should be in genre {expected!r}.",
    )


def top_song_is(expected_title: str) -> Assertion:
    return Assertion(
        name=f"top_title=={expected_title}",
        check=lambda r: bool(r.recommendations) and r.recommendations[0].song.get("title") == expected_title,
        description=f"Top recommendation should be {expected_title!r}.",
    )


def confidence_at_least(threshold: float) -> Assertion:
    return Assertion(
        name=f"confidence>={threshold:.2f}",
        check=lambda r: r.confidence.overall >= threshold,
        description=f"Overall confidence should be at least {threshold:.2f}.",
    )


def persona_is(expected: str) -> Assertion:
    return Assertion(
        name=f"persona=={expected}",
        check=lambda r: r.persona.name == expected,
        description=f"Routed persona should be {expected!r}.",
    )


def returns_at_least(n: int) -> Assertion:
    return Assertion(
        name=f"k>={n}",
        check=lambda r: len(r.recommendations) >= n,
        description=f"Should return at least {n} recommendations.",
    )


def used_refine_step() -> Assertion:
    return Assertion(
        name="used_refine",
        check=lambda r: any(s.name == "refine" for s in r.trace),
        description="Agent should trigger the refine step when confidence is low.",
    )


def genre_diversity_at_least(n: int) -> Assertion:
    return Assertion(
        name=f"distinct_genres>={n}",
        check=lambda r: len({rec.song.get("genre") for rec in r.recommendations}) >= n,
        description=f"Top results should span at least {n} distinct genres.",
    )


def all_high_energy(threshold: float = 0.7) -> Assertion:
    return Assertion(
        name=f"all_energy>={threshold}",
        check=lambda r: all(rec.song.get("energy", 0) >= threshold for rec in r.recommendations),
        description=f"Every recommendation should have energy >= {threshold}.",
    )


TEST_CASES: List[TestCase] = [
    TestCase(
        name="High-energy pop fan (default persona)",
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.85, "valence": 0.85},
        persona="default",
        assertions=[
            returns_at_least(5),
            top_genre_is("pop"),
            confidence_at_least(0.55),
        ],
    ),
    TestCase(
        name="Lofi study session (study persona auto-routes)",
        user_prefs={"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True},
        context_text="I need music for a long study session in the library",
        assertions=[
            returns_at_least(5),
            persona_is("study"),
            top_genre_is("lofi"),
            confidence_at_least(0.55),
        ],
    ),
    TestCase(
        name="Workout EDM (workout persona auto-routes, enforces energy floor)",
        user_prefs={"genre": "edm", "mood": "energetic", "energy": 0.95, "likes_acoustic": False, "valence": 0.75},
        context_text="Need a gym playlist for heavy lifting",
        assertions=[
            returns_at_least(5),
            persona_is("workout"),
            all_high_energy(0.7),
            confidence_at_least(0.55),
        ],
    ),
    TestCase(
        name="Discovery mode pop fan (broaden recommendations)",
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.8},
        context_text="I want to discover new genres beyond pop",
        assertions=[
            returns_at_least(5),
            persona_is("discovery"),
            genre_diversity_at_least(3),
        ],
    ),
    TestCase(
        name="Niche blues sad mood (low-data fallback)",
        user_prefs={"genre": "blues", "mood": "sad", "energy": 0.3},
        persona="default",
        assertions=[
            returns_at_least(5),
            top_genre_is("blues"),
            # The catalog has only 1 blues song; the remaining slots must come
            # from adjacent genres, so we expect at least 3 distinct genres.
            genre_diversity_at_least(3),
        ],
    ),
    TestCase(
        name="Comfort persona for rock fan (narrow on rock)",
        user_prefs={"genre": "rock", "mood": "intense", "energy": 0.9, "likes_acoustic": False},
        persona="comfort",
        assertions=[
            returns_at_least(5),
            top_genre_is("rock"),
            confidence_at_least(0.55),
        ],
    ),
]


def _format_assertion_row(name: str, passed: bool, description: str) -> str:
    icon = "PASS" if passed else "FAIL"
    return f"  - [{icon}] {name} -- {description}"


def _format_recs(result: AgentResult, limit: int = 3) -> List[str]:
    rows = []
    for i, rec in enumerate(result.recommendations[:limit], 1):
        rows.append(
            f"  {i}. {rec.song['title']} ({rec.song.get('artist','?')}) "
            f"[{rec.song.get('genre','?')}/{rec.song.get('mood','?')}] "
            f"score={rec.score:.2f}"
        )
    return rows


def run() -> int:
    songs = load_songs("data/songs.csv")
    agent = MoodMatchAgent(songs=songs)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    total_assertions = 0
    passed_assertions = 0
    failed_cases = 0
    confidence_values: List[float] = []
    iter_counts: List[int] = []
    case_summaries: List[str] = []
    json_records: List[Dict] = []

    for case in TEST_CASES:
        result = agent.run(
            user_prefs=case.user_prefs,
            persona_name=case.persona,
            context_text=case.context_text,
            k=5,
        )
        confidence_values.append(result.confidence.overall)
        iter_counts.append(result.iterations)

        case_lines = [
            f"### {case.name}",
            f"- user_prefs: `{json.dumps(case.user_prefs)}`",
            f"- persona requested: `{case.persona or '(auto)'}` -> selected `{result.persona.name}`",
            f"- iterations: {result.iterations}",
            f"- confidence: {result.confidence.overall:.3f} ({confidence_label(result.confidence.overall)})",
            "- top recommendations:",
            *_format_recs(result),
            "- assertions:",
        ]

        case_failed = False
        case_assertion_records: List[Dict] = []
        for assertion in case.assertions:
            total_assertions += 1
            try:
                ok = bool(assertion.check(result))
            except Exception as exc:  # pragma: no cover - defensive
                ok = False
                case_lines.append(_format_assertion_row(
                    assertion.name, False, f"raised {type(exc).__name__}: {exc}"
                ))
            else:
                case_lines.append(_format_assertion_row(
                    assertion.name, ok, assertion.description
                ))
            if ok:
                passed_assertions += 1
            else:
                case_failed = True
            case_assertion_records.append({
                "name": assertion.name,
                "passed": ok,
                "description": assertion.description,
            })

        if case_failed:
            failed_cases += 1
        case_summaries.append("\n".join(case_lines))
        json_records.append({
            "case": case.name,
            "user_prefs": case.user_prefs,
            "persona_requested": case.persona,
            "persona_selected": result.persona.name,
            "iterations": result.iterations,
            "confidence": result.confidence.to_dict(),
            "assertions": case_assertion_records,
            "top_recommendations": [r.to_dict() for r in result.recommendations[:5]],
        })

    avg_conf = statistics.mean(confidence_values) if confidence_values else 0.0
    median_conf = statistics.median(confidence_values) if confidence_values else 0.0
    min_conf = min(confidence_values) if confidence_values else 0.0
    avg_iter = statistics.mean(iter_counts) if iter_counts else 0.0

    summary = [
        "# MoodMatch Agent -- Evaluation Report",
        f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}_",
        "",
        "## Summary",
        f"- cases run: **{len(TEST_CASES)}**",
        f"- cases fully passing: **{len(TEST_CASES) - failed_cases} / {len(TEST_CASES)}**",
        f"- assertions passed: **{passed_assertions} / {total_assertions}** "
        f"({100.0 * passed_assertions / max(total_assertions,1):.1f}%)",
        f"- average confidence: **{avg_conf:.3f}** ({confidence_label(avg_conf)})",
        f"- median confidence:  **{median_conf:.3f}**",
        f"- min confidence:     **{min_conf:.3f}**",
        f"- average iterations: **{avg_iter:.2f}** (max=2)",
        "",
        "## Per-case breakdown",
        "",
    ]
    summary.extend(case_summaries)

    report = "\n".join(summary) + "\n"
    REPORT_PATH.write_text(report, encoding="utf-8")
    json_path = REPORT_PATH.with_suffix(".json")
    json_path.write_text(json.dumps({
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cases": json_records,
        "summary": {
            "cases": len(TEST_CASES),
            "fully_passing_cases": len(TEST_CASES) - failed_cases,
            "assertions_passed": passed_assertions,
            "assertions_total": total_assertions,
            "average_confidence": avg_conf,
            "median_confidence": median_conf,
            "min_confidence": min_conf,
            "average_iterations": avg_iter,
        },
    }, indent=2), encoding="utf-8")

    print("\n".join(summary[:11]))
    print(f"\nReport written to: {REPORT_PATH}")
    print(f"JSON written to:   {json_path}")

    return 0 if failed_cases == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
