"""retrieval: keyword-search, via plain-python.

Keyword search: query_pattern == lookup

Two retrievers, because each fails exactly where the other works. Lexical
matching finds part numbers, account references and names -- the tokens people
actually search for -- and is blind to meaning. Semantic search handles a
question phrased three different ways and fumbles an identifier. Running both
and fusing them lifts recall well above either alone.

**Fusion is on rank, not score.** Two retrievers do not produce comparable
numbers, and averaging them is the thing that looks reasonable and quietly
breaks: one retriever's 0.8 is not the other's. Reciprocal rank fusion needs no
scores at all, which is what lets it combine retrievers that share nothing --
including one that has no scores to give.

A document both tiers found outranks one only either found. That is the whole
mechanism, and it is why agreement is worth more than any single score.

This deployment runs the lexical tier alone (keyword search applies, and the
corpus is 58 standards). It ranks chunks, each indexed under its document's
heading; `retrieve` answers "which documents", `passages` answers "which text".
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from typing import Any

from app.contract import RefusedInput

# Rank-fusion constant. Damps the top of each list so one retriever's first
# result cannot dominate agreement between the others.
RRF_K = 60

TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")

# BM25. Term frequency saturates, so a chunk that says "MIME" twelve times does
# not outrank one that answers the question once.
K1 = 1.2
B = 0.75

# Passages handed to reasoning: enough to carry an answer, few enough that a
# small model is not reading past it.
PASSAGES = 3

# How a question is phrased, not what it is about. "stand" is the one to
# notice: rare in standards, so left in it outranks every chunk that actually
# defines the acronym being asked about.
STOPWORDS = frozenset("""
    a an and are as at be been being but by can could did do does each for from
    had has have how i if in into is it its many may might much must no not of
    on or s shall should so such than that the their them then there these they
    this those to was were what when where which who whom whose why will with
    would you your stand stands called mean means
""".split())


def fuse(ranked: dict[str, list[str]], k: int = RRF_K) -> list[str]:
    """Combine ranked lists using ranks alone.

    Deliberately score-free. It works across retrievers with incompatible
    scales, and it works when one of them has no score to offer.
    """
    totals: dict[str, float] = defaultdict(float)
    for results in ranked.values():
        for position, doc_id in enumerate(results):
            totals[doc_id] += 1.0 / (k + position + 1)
    return sorted(totals, key=lambda d: (-totals[d], d))


class Retrieval:
    """Retriever, as keyword-search."""

    interface = "Retriever"
    approach = "keyword-search"
    stack = "plain-python"

    def __init__(self, source: Callable[[], list[dict[str, Any]]] | None = None) -> None:
        # Where the index comes from when nobody handed it chunks: the
        # deployed corpus, read the way the pipeline reads it.
        self._source = source
        self._clear()

    def _clear(self) -> None:
        self._units: dict[str, dict[str, Any]] = {}
        self._frequencies: dict[str, Counter] = {}
        self._lengths: dict[str, int] = {}
        self._document_frequency: Counter = Counter()
        self._average_length = 0.0
        self._indexed: tuple[str, ...] = ()

    def index(self, documents: list[dict[str, Any]]) -> None:
        """Index units -- whole documents, or chunks naming their `source`."""
        for document in documents:
            unit = dict(document)
            unit.setdefault("source", unit["id"])
            tokens = self._tokenise(f"{unit.get('heading', '')}\n{unit['text']}")
            self._units[unit["id"]] = unit
            self._frequencies[unit["id"]] = Counter(tokens)
            self._lengths[unit["id"]] = len(tokens)
            for token in set(tokens):
                self._document_frequency[token] += 1
        self._average_length = sum(self._lengths.values()) / (len(self._lengths) or 1)

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Documents, ranked by their best chunk. Where a semantic tier exists,
        its ranking is fused with this one rather than averaged against it."""
        self._wire()
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for unit_id, score in self._lexical(query):
            unit = self._units[unit_id]
            if unit["source"] in seen:
                continue
            seen.add(unit["source"])
            results.append({
                "id": unit["source"], "rank": len(results) + 1, "score": round(score, 4),
                "chunk": unit_id, "text": unit["text"],
            })
            if len(results) >= k:
                break
        return results

    def passages(self, query: str, k: int = PASSAGES) -> list[dict[str, Any]]:
        """Chunks, ranked -- the evidence an answer is written from."""
        self._wire()
        return [
            {**self._units[unit_id], "rank": position + 1, "score": round(score, 4)}
            for position, (unit_id, score) in enumerate(self._lexical(query)[:k])
        ]

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RefusedInput(f"retrieval reads a payload object, not {type(payload).__name__}")
        query, chunks = payload.get("query"), payload.get("chunks")
        if not isinstance(query, str) or not query.strip():
            raise RefusedInput("retrieval needs the question, as text")
        if not isinstance(chunks, list) or not chunks:
            raise RefusedInput("retrieval needs chunks to search")
        if any(not isinstance(c, dict) or not isinstance(c.get("id"), str)
               or not isinstance(c.get("text"), str) for c in chunks):
            raise RefusedInput("every chunk needs an id and text")
        k = payload.get("k", PASSAGES)
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise RefusedInput(f"k is a positive whole number, not {k!r}")

        self._ensure(chunks)
        return {"query": query, "passages": self.passages(query, k)}

    # -- the index --------------------------------------------------------

    def _ensure(self, chunks: list[dict[str, Any]]) -> None:
        """Index these chunks unless they are exactly what is indexed already.
        Chunk ids are content hashes, so equal ids mean an unchanged corpus."""
        ids = tuple(c["id"] for c in chunks)
        if ids != self._indexed:
            self._clear()
            self.index(chunks)
            self._indexed = ids

    def _wire(self) -> None:
        if self._frequencies:
            return
        if self._source is None:
            # Refusing is the honest failure: an empty index returning [] would
            # read as "nothing relevant" when the truth is "nothing indexed".
            raise RuntimeError("nothing is indexed -- index() documents first, "
                               "or construct with source=")
        self._ensure(self._source())

    # -- lexical ----------------------------------------------------------

    def _lexical(self, query: str) -> list[tuple[str, float]]:
        """BM25: term frequency, saturated, against inverse document frequency.

        Unfashionable and hard to beat when the query contains the token the
        answer contains -- which is most of the time in a document corpus.
        """
        total = len(self._frequencies)
        scores: dict[str, float] = defaultdict(float)
        for token in set(self._tokenise(query, skip=STOPWORDS)):
            appearing = self._document_frequency.get(token, 0)
            if not appearing:
                continue
            rarity = math.log(1 + (total - appearing + 0.5) / (appearing + 0.5))
            for unit_id, counts in self._frequencies.items():
                count = counts.get(token)
                if count:
                    length = self._lengths[unit_id] / self._average_length
                    scores[unit_id] += rarity * count * (K1 + 1) / (
                        count + K1 * (1 - B + B * length)
                    )
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))

    @staticmethod
    def _tokenise(text: str, skip: frozenset[str] = frozenset()) -> list[str]:
        # Identifiers are kept whole. Splitting SKU-99312 into two tokens is
        # how a lexical tier loses the one thing it is better at -- so the
        # parts of a hyphenated token are added beside it, never instead.
        tokens = []
        for token in TOKEN.findall(text):
            token = token.lower()
            if token in skip:
                continue
            tokens.append(_stem(token))
            if "-" in token:
                tokens.extend(_stem(part) for part in token.split("-")
                              if part and part not in skip)
        return tokens


def _stem(token: str) -> str:
    """Plurals folded, nothing more (Harman's S-stemmer): "bits" finds "128-bit".
    Words only; an identifier with a digit in it is left exactly as written."""
    if len(token) <= 3 or not token.isalpha():
        return token
    if token.endswith("ies") and not token.endswith(("eies", "aies")):
        return token[:-3] + "y"
    if token.endswith("es") and not token.endswith(("aes", "ees", "oes")):
        return token[:-1]
    if token.endswith("s") and not token.endswith(("us", "ss")):
        return token[:-1]
    return token


def _deployed_chunks() -> list[dict[str, Any]]:
    # Imported here: the pipeline imports this module.
    from app import pipeline

    return pipeline.chunks()


# The deployed index. The pipeline answers from this instance and
# evals/retrieval.py measures it, so the recall number is the ceiling the
# answers actually live under. Wired on first use from the shipped corpus.
INDEX = Retrieval(source=_deployed_chunks)
