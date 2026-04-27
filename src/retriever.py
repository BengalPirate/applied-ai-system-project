"""
Retrieval-Augmented Generation layer.

Loads the curated music knowledge base from data/knowledge_base.md, indexes
each passage with a simple TF-IDF-style scorer, and returns the top-k
passages most relevant to the agent's query.

The retriever runs entirely offline (no API key, no embedding service)
so the system stays reproducible for any grader cloning the repo.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from src.logging_setup import get_logger

logger = get_logger(__name__)

PASSAGE_DELIM = "\n---\n"
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "is", "it", "its", "of", "on", "or", "that",
    "the", "to", "was", "were", "will", "with", "this", "these", "those",
    "but", "not", "should", "when", "if", "so", "than", "then", "also",
}


@dataclass
class Passage:
    """A single retrievable knowledge-base entry."""
    title: str
    tags: List[str]
    body: str
    raw: str = field(repr=False)


def _tokenize(text: str) -> List[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def _parse_passages(text: str) -> List[Passage]:
    chunks = [c.strip() for c in text.split(PASSAGE_DELIM) if c.strip()]
    passages: List[Passage] = []
    for chunk in chunks:
        if chunk.startswith("# "):
            continue
        title = ""
        tags: List[str] = []
        body_lines: List[str] = []
        for line in chunk.splitlines():
            stripped = line.strip()
            if stripped.startswith("title:"):
                title = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("tags:"):
                tags = [t.strip() for t in stripped.split(":", 1)[1].split(",") if t.strip()]
            else:
                body_lines.append(line)
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        passages.append(Passage(title=title or "(untitled)", tags=tags, body=body, raw=chunk))
    return passages


@dataclass
class RetrievalHit:
    passage: Passage
    score: float

    def to_dict(self) -> Dict:
        return {
            "title": self.passage.title,
            "tags": self.passage.tags,
            "score": round(self.score, 3),
            "body": self.passage.body,
        }


class KnowledgeRetriever:
    """TF-IDF retriever over the music knowledge base."""

    def __init__(self, kb_path: str | Path = "data/knowledge_base.md"):
        self.kb_path = Path(kb_path)
        if not self.kb_path.exists():
            raise FileNotFoundError(f"Knowledge base not found at {self.kb_path}")
        text = self.kb_path.read_text(encoding="utf-8")
        self.passages: List[Passage] = _parse_passages(text)
        if not self.passages:
            raise ValueError(f"No passages parsed from {self.kb_path}")
        self._doc_tokens: List[List[str]] = [
            _tokenize(p.title + " " + " ".join(p.tags) + " " + p.body)
            for p in self.passages
        ]
        self._idf = self._compute_idf(self._doc_tokens)
        self._doc_vectors = [self._tfidf(toks) for toks in self._doc_tokens]
        logger.info("KnowledgeRetriever loaded %d passages from %s",
                    len(self.passages), self.kb_path)

    @staticmethod
    def _compute_idf(docs: List[List[str]]) -> Dict[str, float]:
        n = len(docs)
        df: Dict[str, int] = {}
        for toks in docs:
            for term in set(toks):
                df[term] = df.get(term, 0) + 1
        return {term: math.log((1 + n) / (1 + count)) + 1.0 for term, count in df.items()}

    def _tfidf(self, tokens: Iterable[str]) -> Dict[str, float]:
        tf: Dict[str, float] = {}
        for tok in tokens:
            tf[tok] = tf.get(tok, 0) + 1.0
        if not tf:
            return tf
        max_tf = max(tf.values())
        return {
            term: (count / max_tf) * self._idf.get(term, 1.0)
            for term, count in tf.items()
        }

    @staticmethod
    def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        common = set(a).intersection(b)
        if not common:
            return 0.0
        dot = sum(a[t] * b[t] for t in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.05) -> List[RetrievalHit]:
        """Return the top_k most relevant passages for the query."""
        if not query or not query.strip():
            logger.warning("KnowledgeRetriever received empty query; returning []")
            return []
        q_tokens = _tokenize(query)
        q_vec = self._tfidf(q_tokens)
        scored = [
            RetrievalHit(self.passages[i], self._cosine(q_vec, dv))
            for i, dv in enumerate(self._doc_vectors)
        ]
        scored = [h for h in scored if h.score >= min_score]
        scored.sort(key=lambda h: h.score, reverse=True)
        hits = scored[:top_k]
        logger.info("retrieve(query=%r) -> %d hits (scores=%s)",
                    query, len(hits), [round(h.score, 3) for h in hits])
        return hits

    def retrieve_for_profile(self, user_prefs: Dict, persona_name: Optional[str] = None,
                             top_k: int = 3) -> List[RetrievalHit]:
        """Build a structured query from user prefs and persona, then retrieve."""
        parts: List[str] = []
        for key in ("genre", "mood"):
            v = user_prefs.get(key)
            if v:
                parts.append(str(v))
        energy = user_prefs.get("energy")
        if isinstance(energy, (int, float)):
            if energy >= 0.75:
                parts.append("high-energy")
            elif energy <= 0.4:
                parts.append("low-energy")
        if user_prefs.get("likes_acoustic") is True:
            parts.append("acoustic")
        if persona_name:
            parts.append(persona_name)
        query = " ".join(parts)
        return self.retrieve(query, top_k=top_k)
