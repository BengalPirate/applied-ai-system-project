"""Tests for the RAG retriever."""

from src.retriever import KnowledgeRetriever


def test_retriever_loads_passages():
    r = KnowledgeRetriever()
    assert len(r.passages) >= 5
    titles = {p.title for p in r.passages}
    assert "lofi listener tendencies" in titles


def test_retriever_returns_relevant_lofi_passage():
    r = KnowledgeRetriever()
    hits = r.retrieve("lofi study chill low energy", top_k=3)
    assert hits, "expected at least one hit for the lofi query"
    titles = [h.passage.title for h in hits]
    # The lofi or study passage should rank in the top 3
    assert any("lofi" in t or "study" in t for t in titles), titles


def test_retriever_returns_workout_passage_for_gym_query():
    r = KnowledgeRetriever()
    hits = r.retrieve("gym workout high tempo running", top_k=3)
    assert hits
    assert any("workout" in h.passage.title or "tempo" in h.passage.title for h in hits)


def test_retriever_empty_query_returns_empty():
    r = KnowledgeRetriever()
    assert r.retrieve("", top_k=3) == []


def test_retrieve_for_profile_uses_genre_and_mood():
    r = KnowledgeRetriever()
    hits = r.retrieve_for_profile(
        {"genre": "edm", "mood": "energetic", "energy": 0.95},
        persona_name="workout",
        top_k=3,
    )
    assert hits
