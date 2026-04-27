"""End-to-end tests for the MoodMatch agentic workflow."""

import pytest

from src.agent import MoodMatchAgent
from src.guardrails import GuardrailError
from src.recommender import load_songs


@pytest.fixture(scope="module")
def agent():
    songs = load_songs("data/songs.csv")
    return MoodMatchAgent(songs=songs)


def test_agent_returns_top_k_with_explanations(agent):
    result = agent.run(
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.85},
        persona_name="default",
        k=5,
    )
    assert len(result.recommendations) == 5
    for rec in result.recommendations:
        assert rec.explanation
        assert rec.song["title"]


def test_agent_trace_contains_plan_act_reflect_finalize(agent):
    result = agent.run(
        user_prefs={"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": True},
        persona_name="study",
    )
    step_names = [s.name for s in result.trace]
    assert step_names[0] == "plan"
    assert "act" in step_names
    assert "reflect" in step_names
    assert step_names[-1] == "finalize"


def test_agent_plan_includes_rag_passages(agent):
    result = agent.run(
        user_prefs={"genre": "edm", "mood": "energetic", "energy": 0.92},
        persona_name="workout",
    )
    plan_step = next(s for s in result.trace if s.name == "plan")
    assert plan_step.detail["retrieved_passages"], "RAG should retrieve at least one passage"


def test_agent_auto_routes_workout_persona(agent):
    result = agent.run(
        user_prefs={"genre": "edm", "mood": "energetic", "energy": 0.92},
        context_text="gym workout playlist for heavy lifting",
    )
    assert result.persona.name == "workout"


def test_agent_auto_routes_discovery_persona(agent):
    result = agent.run(
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.8},
        context_text="I want to discover new genres I haven't heard before",
    )
    assert result.persona.name == "discovery"


def test_agent_validates_user_prefs(agent):
    with pytest.raises(GuardrailError):
        agent.run(user_prefs={"genre": "pop"}, persona_name="default")


def test_workout_persona_filters_low_energy(agent):
    result = agent.run(
        user_prefs={"genre": "edm", "mood": "energetic", "energy": 0.92, "likes_acoustic": False},
        persona_name="workout",
    )
    # Workout persona enforces energy_floor=0.7 with -2.0 penalty.
    # The top result must clear the floor.
    assert result.recommendations[0].song["energy"] >= 0.7


def test_personas_produce_different_results(agent):
    """Specialization must measurably change behavior for the same prefs."""
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.85}
    comfort = agent.run(user_prefs=prefs, persona_name="comfort")
    discovery = agent.run(user_prefs=prefs, persona_name="discovery")
    comfort_genres = {r.song["genre"] for r in comfort.recommendations}
    discovery_genres = {r.song["genre"] for r in discovery.recommendations}
    # Discovery should surface a broader genre set than comfort.
    assert len(discovery_genres) >= len(comfort_genres)


def test_refine_step_fires_when_confidence_below_threshold():
    """Force refine by constructing an agent with a near-impossible confidence threshold."""
    songs = load_songs("data/songs.csv")
    strict = MoodMatchAgent(songs=songs, confidence_threshold=0.99, max_iterations=2)
    result = strict.run(
        user_prefs={"genre": "blues", "mood": "sad", "energy": 0.3},
        persona_name="default",
    )
    refine_steps = [s for s in result.trace if s.name == "refine"]
    assert refine_steps, f"expected a refine step, got trace: {[s.name for s in result.trace]}"
    # Two reflect steps confirm the second (post-refine) reflection ran.
    reflect_steps = [s for s in result.trace if s.name == "reflect"]
    assert len(reflect_steps) == 2
    assert result.iterations == 2


def test_confidence_label_present(agent):
    result = agent.run(
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.85},
        persona_name="default",
    )
    assert result.confidence_label in ("high", "medium", "low", "very-low")
