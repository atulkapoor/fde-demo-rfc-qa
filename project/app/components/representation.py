"""representation: segmentation, via plain-python.

Segmentation: output_shape == freeform

Documents into retrievable chunks with their origins attached. Fixed
windows with overlap, deliberately boring: semantic splitting is a
graduation to earn with measured retrieval quality, not a default.

Traceability is the non-negotiable half. Every chunk carries its source
and character offsets, so every generated sentence can point back at where
it came from -- an unverifiable answer inside a client's environment is a
liability wearing a feature's clothes.

Every chunk also carries its document's heading. A window cut from page forty
of a standard no longer says which standard it is, and that is often the
answer: what an acronym stands for, which version an RFC specifies.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.contract import RefusedInput

# Sized for retrieval, not for reading: long enough to carry an answer,
# short enough that a ranker can tell chunks apart.
WINDOW = 1200
OVERLAP = 200


class Representation:
    """Parser, as segmentation."""

    interface = "Parser"
    approach = "segmentation"
    stack = "plain-python"

    def __init__(self, window: int = WINDOW, overlap: int = OVERLAP) -> None:
        if overlap >= window:
            raise ValueError("overlap must be smaller than the window")
        self.window = window
        self.overlap = overlap
        # Same record, same chunks: segmenting a static corpus twice changes nothing.
        self._segmented: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RefusedInput(f"segmentation reads a payload object, not {type(payload).__name__}")
        # Perception's output, not its input: records are what was read.
        records = payload.get("records")
        if not isinstance(records, list):
            raise RefusedInput("segmentation needs perception's records, as a list")
        if not records:
            raise RefusedInput("there are no records to segment")

        chunks = [chunk for record in records for chunk in self._chunks(record)]
        result = {
            "chunks": chunks,
            "documents": len(records),
            # The number an index is sized from, and the denominator any
            # retrieval-quality measurement divides by.
            "chunk_count": len(chunks),
        }
        if "query" in payload:
            result["query"] = payload["query"]
        return result

    def _chunks(self, record: Any) -> list[dict[str, Any]]:
        if not isinstance(record, dict):
            raise RefusedInput(f"a record is an object, not {type(record).__name__}")
        source, text = record.get("id"), record.get("text")
        if not isinstance(source, str) or not source:
            raise RefusedInput("a record without an id cannot be traced to its source")
        if not isinstance(text, str) or not text.strip():
            raise RefusedInput(f"record {source!r} has no text to segment")
        heading = record.get("title") or source

        key = (source, heading, text)
        if key not in self._segmented:
            self._segmented[key] = self._windows(source, heading, text)
        return self._segmented[key]

    def _windows(self, source: str, heading: str, text: str) -> list[dict[str, Any]]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.window, len(text))
            body = text[start:end]
            chunks.append({
                # Stable identity: same corpus, same chunks, same ids --
                # a diff between two indexes means the corpus changed.
                "id": hashlib.sha256(
                    f"{source}:{start}:{body}".encode()
                ).hexdigest()[:16],
                "source": source,
                "heading": heading,
                "start": start,
                "end": end,
                "text": body,
            })
            if end == len(text):
                break
            start = end - self.overlap
        return chunks
