"""Tests for confidence scoring."""

from src.confidence import compute_confidence, confidence_label


def _song(idx, genre, artist, score):
    return ({"id": idx, "title": f"t{idx}", "artist": artist, "genre": genre}, score, "")


def test_confidence_high_when_top_score_strong_and_diverse():
    scored = [
        _song(1, "pop", "A", 5.2),
        _song(2, "rock", "B", 4.0),
        _song(3, "jazz", "C", 3.5),
        _song(4, "lofi", "D", 3.0),
        _song(5, "edm", "E", 2.5),
    ]
    r = compute_confidence(scored)
    assert r.overall >= 0.7
    assert confidence_label(r.overall) in ("high", "medium")


def test_confidence_low_when_filter_bubble_and_low_top_score():
    scored = [
        _song(1, "pop", "A", 1.5),
        _song(2, "pop", "A", 1.4),
        _song(3, "pop", "A", 1.3),
        _song(4, "pop", "A", 1.2),
        _song(5, "pop", "A", 1.1),
    ]
    r = compute_confidence(scored)
    assert r.overall < 0.5
    assert any("diversity" in n for n in r.notes)


def test_confidence_empty_returns_zero():
    r = compute_confidence([])
    assert r.overall == 0.0


def test_confidence_label_buckets():
    assert confidence_label(0.9) == "high"
    assert confidence_label(0.6) == "medium"
    assert confidence_label(0.4) == "low"
    assert confidence_label(0.1) == "very-low"


def test_confidence_supports_persona_specific_max_possible():
    scored = [
        _song(1, "pop", "A", 4.4),
        _song(2, "rock", "B", 3.8),
        _song(3, "jazz", "C", 3.4),
        _song(4, "lofi", "D", 3.0),
        _song(5, "edm", "E", 2.6),
    ]
    default_norm = compute_confidence(scored)
    discovery_norm = compute_confidence(scored, max_possible=4.5)
    assert discovery_norm.top_score_norm > default_norm.top_score_norm
    assert discovery_norm.overall > default_norm.overall
