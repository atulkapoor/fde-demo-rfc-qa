"""perception: text-extraction, via plain-python.

Text extraction: input_format == text

This sets the ceiling for everything downstream, and it is the most
under-invested part of most systems. A badly parsed table is not recovered by a
better reranker or a better model -- the relationship between the numbers is
already gone.

So the job here is not only to extract. It is to **say what was lost**. A parser
that flattens a table silently sets a limit nobody discovers until the answers
are wrong; one that reports the flattening turns a mystery into a number an
engineer can quote before promising anything.

Tables are the usual casualty. A row of figures collapsed into a line has kept
every value and thrown away which column each belonged to, which is exactly the
part that mattered.

Two texts arrive here: the standards, and the operator's question. The question
is read as data too. A sentence in it that addresses the system rather than the
standards -- "ignore all previous instructions" -- is quarantined: kept out of
what retrieval and the model see, and reported, never obeyed.
"""

from __future__ import annotations

import re
from typing import Any

from app.contract import RefusedInput

# Lines that look like a row of a table: repeated separators with content
# between them. Crude, and enough to notice that structure was present.
TABULAR = re.compile(r"(\S+\s*[|\t]\s*){2,}\S+")

# Runs of whitespace used as column separation rather than as spacing.
COLUMNAR = re.compile(r"\S+ {3,}\S+ {3,}\S+")

BOM = chr(0xFEFF)

# Page furniture a paginated RFC repeats on every page: the footer that closes
# one page and the running header that opens the next. Left in, it lands in the
# middle of a sentence and carries nothing the document's heading does not.
FOOTER = re.compile(r"\[Page \d+\]$")
RUNNING_HEADER = re.compile(
    r"^RFC \d+ .+ (January|February|March|April|May|June|July|August|September"
    r"|October|November|December) \d{4}$"
)

# The front page: the metadata block, then the title, then the body.
FRONT_MATTER = re.compile(
    r"^(RFC\b|Request for Comments|Network Working Group|Internet Engineering Task Force"
    r"|Internet Research Task Force|Internet Architecture Board|Independent Submission"
    r"|Obsoletes|Updates|Category|ISSN|STD\b|BCP\b|FYI\b)",
    re.IGNORECASE,
)
DESIGNATION = re.compile(r"^(?:Request for Comments|RFC)\s*:?\s*#?\s*(\d+)", re.IGNORECASE)
BODY_START = ("status of this memo", "abstract", "table of contents", "introduction", "1.")
TITLE_CHARS = 160

# A sentence aimed at the system instead of at the standards.
OVERRIDE = re.compile(
    r"\b(ignore|disregard|forget)\b[^.?!]{0,40}\b(instructions?|prompts?)\b"
    r"|\b(system prompt|you are now|new instructions)\b",
    re.IGNORECASE,
)
SENTENCE_BREAK = re.compile(r"(?<=[.?!])\s+|\n+")


class Perception:
    """Parser, as text-extraction."""

    interface = "Parser"
    approach = "text-extraction"
    stack = "plain-python"

    def __init__(self) -> None:
        # The corpus is static, so a document read once is read for good.
        # Keyed on the text itself: a changed document is a new key.
        self._read_already: dict[tuple[str, str], dict[str, Any]] = {}

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RefusedInput(f"perception reads a payload object, not {type(payload).__name__}")

        result: dict[str, Any] = {}
        # The question first: it is the cheap check, and a request with no
        # question should not cost a read of the corpus.
        if "query" in payload:
            result["query"], result["quarantined"] = self._question(payload["query"])

        documents = payload.get("documents")
        if not isinstance(documents, list):
            raise RefusedInput("perception needs documents, as a list")
        if not documents:
            raise RefusedInput("there are no documents to read")

        records = [self._record(d) for d in documents]
        clean = [r for r in records if not r["losses"]]
        return {
            **result,
            "records": records,
            # One number to quote before promising anything downstream. If this
            # is 0.6, no amount of work further along gets the system past it.
            "clean_share": len(clean) / (len(records) or 1),
        }

    def _record(self, document: Any) -> dict[str, Any]:
        if not isinstance(document, dict):
            raise RefusedInput(f"a document is an object, not {type(document).__name__}")
        doc_id, text = document.get("id"), document.get("text")
        if not isinstance(doc_id, str) or not doc_id:
            raise RefusedInput("a document without an id cannot be traced")
        if not isinstance(text, str):
            raise RefusedInput(f"document {doc_id!r} has no text")
        if not text.strip(BOM).strip():
            raise RefusedInput(f"document {doc_id!r} is empty")

        key = (doc_id, text)
        if key not in self._read_already:
            self._read_already[key] = self._read(document)
        return self._read_already[key]

    def _read(self, document: dict[str, Any]) -> dict[str, Any]:
        text = document.get("text", "")
        losses = []

        tabular_lines = [ln for ln in text.splitlines() if TABULAR.search(ln)]
        columnar_lines = [ln for ln in text.splitlines() if COLUMNAR.search(ln)]

        if tabular_lines:
            losses.append({
                "kind": "table_flattened",
                "lines": len(tabular_lines),
                "detail": "row structure present in the source and not preserved here; "
                          "column membership is lost, and nothing downstream restores it",
            })
        if columnar_lines and not tabular_lines:
            losses.append({
                "kind": "columns_inferred_from_spacing",
                "lines": len(columnar_lines),
                "detail": "alignment suggests columns; whitespace is not a reliable "
                          "separator and this may have merged or split fields",
            })

        normalised = self._normalise(text)
        return {
            "id": document.get("id"),
            # What the document is, read off its front page -- so a passage cut
            # from page forty still says which standard it came from.
            "title": self._heading(normalised.splitlines()),
            "text": normalised,
            "losses": losses,
            # Not a model's confidence. A structural observation: how much of
            # this document arrived in a shape we can stand behind.
            "usable": not losses,
        }

    @staticmethod
    def _normalise(text: str) -> str:
        """Whitespace tidied, line structure kept.

        Line breaks are load-bearing in documents -- collapsing them is the
        second most common way a parser destroys what it was given. Blank runs
        shrink to one blank line, which keeps every paragraph break.
        """
        lines = (re.sub(r"[ \t]+", " ", line).strip() for line in text.lstrip(BOM).splitlines())
        kept = [ln for ln in lines if not (FOOTER.search(ln) or RUNNING_HEADER.match(ln))]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()

    @staticmethod
    def _heading(lines: list[str]) -> str | None:
        """'RFC 2045: Multipurpose Internet Mail Extensions ...', or what of it
        the front page gives up. None when it gives up nothing."""
        designation = title = None
        paragraph: list[str] = []
        for line in lines[:120] + [""]:
            if line:
                paragraph.append(line)
                continue
            if not paragraph:
                continue
            if paragraph[0].lower().startswith(BODY_START):
                break
            if any(FRONT_MATTER.match(ln) for ln in paragraph):
                for ln in paragraph:
                    found = DESIGNATION.match(ln)
                    if found and designation is None:
                        designation = found.group(1)
            else:
                candidate = " ".join(paragraph)
                title = candidate if len(candidate) <= TITLE_CHARS else None
                break
            paragraph = []

        if designation and title:
            return f"RFC {designation}: {title}"
        if designation:
            return f"RFC {designation}"
        return title

    @staticmethod
    def _question(query: Any) -> tuple[str, list[str]]:
        """The question as retrieval and the model will see it, and what was
        kept out of it."""
        if not isinstance(query, str):
            raise RefusedInput(f"a question is text, not {type(query).__name__}")
        kept, quarantined = [], []
        for sentence in SENTENCE_BREAK.split(query.lstrip(BOM)):
            sentence = " ".join(sentence.split())
            if sentence:
                (quarantined if OVERRIDE.search(sentence) else kept).append(sentence)
        if not kept:
            raise RefusedInput(
                "the input holds an instruction to the system and no question"
                if quarantined else "the question is empty"
            )
        return " ".join(kept), quarantined
