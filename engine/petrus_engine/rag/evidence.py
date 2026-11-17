"""Read-only evidence projection. IDs identify current rows, not a permanent vector index."""

import re
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Iterator


class ProvenanceLevel(StrEnum):
    COORDINATE = "coordinate"
    EXACT_PAGE_ALIGNMENT = "exact_page_alignment"
    SECTION_ONLY = "section_only"
    BASIC_PAGE_TEXT = "basic_page_text"


@dataclass(frozen=True)
class EvidenceUnit:
    unit_id: str
    paper_id: int
    section_id: int | None
    source_span_id: int | None
    section_type: str | None
    heading: str | None
    page_start: int | None
    page_end: int | None
    text: str
    provenance_level: ProvenanceLevel
    provenance_source: str
    doi: str | None
    title: str
    evidence_role: str = "body"
    parent_unit_id: str | None = None
    part_start: int | None = None
    part_end: int | None = None

    @property
    def supports_paginated_evidence(self) -> bool:
        return (
            self.provenance_level in (ProvenanceLevel.COORDINATE, ProvenanceLevel.EXACT_PAGE_ALIGNMENT)
            and self.source_span_id is not None
            and self.page_start is not None
            and self.page_end is not None
        )


def subdivide_span(unit: EvidenceUnit, max_chars: int = 6000) -> tuple[EvidenceUnit, ...]:
    """Lossless, no-overlap partitions: paragraphs, sentences, then bounded characters."""
    if max_chars < 1:
        raise ValueError("invalid_subdivision_limit")
    if len(unit.text) <= max_chars:
        return (unit,)
    parts, start = [], 0
    while start < len(unit.text):
        end = min(start + max_chars, len(unit.text))
        if end < len(unit.text):
            segment = unit.text[start:end]
            minimum = max(1, max_chars // 3)
            paragraph = [m.end() for m in re.finditer(r"\n\s*\n", segment) if m.end() >= minimum]
            sentence = [m.end() for m in re.finditer(r"[.!?]\s+", segment) if m.end() >= minimum]
            boundary = paragraph or sentence
            if boundary:
                end = start + boundary[-1]
        parts.append(
            replace(
                unit,
                unit_id=f"{unit.unit_id}:part:{len(parts) + 1}",
                parent_unit_id=unit.unit_id,
                part_start=start,
                part_end=end,
                text=unit.text[start:end],
            )
        )
        start = end
    return tuple(parts)


def section_role(section, sections):
    seen = set()
    while section and section["id"] not in seen:
        seen.add(section["id"])
        kind = section["section_type"]
        if kind == "references":
            return "bibliography"
        if kind in ("abstract", "methods", "results", "discussion", "conclusion"):
            return kind
        heading = (section["heading"] or "").casefold()
        if re.search(r"limitation|caveat|limita[çc]", heading):
            return "limitations"
        if re.search(r"acknowledg|funding|author contribution|data availability|agradecimento", heading):
            return "metadata"
        section = sections.get(section["parent_section_id"])
    return "body"


class EvidenceRepository:
    def __init__(self, database):
        self.database = database

    def iter_units(self, paper_id: int | None = None) -> Iterator[EvidenceUnit]:
        with self.database.connect() as db:
            papers = db.execute(
                "SELECT id,title,doi FROM papers WHERE (? IS NULL OR id=?) ORDER BY id",
                (paper_id, paper_id),
            )
            for paper in papers:
                base = {"paper_id": paper["id"], "doi": paper["doi"], "title": paper["title"]}
                spans = db.execute(
                    """SELECT sp.*,s.section_type,s.heading FROM source_spans sp
                    LEFT JOIN sections s ON s.id=sp.section_id WHERE sp.paper_id=? ORDER BY sp.id""",
                    (paper["id"],),
                ).fetchall()
                section_map = {
                    r["id"]: r for r in db.execute("SELECT * FROM sections WHERE paper_id=?", (paper["id"],))
                }
                for span in spans:
                    level = {
                        "grobid_coordinates": ProvenanceLevel.COORDINATE,
                        "page_text_alignment": ProvenanceLevel.EXACT_PAGE_ALIGNMENT,
                    }.get(span["source_type"])
                    # Unknown sources must never silently become paginated evidence.
                    if level is None or not span["text"].strip():
                        continue
                    yield EvidenceUnit(
                        **base,
                        unit_id=f"span:{span['id']}",
                        section_id=span["section_id"],
                        source_span_id=span["id"],
                        section_type=span["section_type"],
                        heading=span["heading"],
                        page_start=span["page"],
                        page_end=span["page"],
                        text=span["text"],
                        provenance_level=level,
                        provenance_source=span["source_type"],
                        # Reference-linked spans currently represent bibl entries or isolated markers,
                        # not the surrounding body paragraph. That paragraph has its own section span.
                        evidence_role="bibliography"
                        if span["reference_id"] is not None
                        else section_role(section_map.get(span["section_id"]), section_map),
                    )
                sections = db.execute(
                    "SELECT * FROM sections WHERE paper_id=? ORDER BY section_order,id", (paper["id"],)
                ).fetchall()
                for section in sections:
                    # Partial sections retain their full discovery text without claiming a page.
                    mapped = any(
                        s["section_id"] == section["id"]
                        and s["source_type"] in ("grobid_coordinates", "page_text_alignment")
                        for s in spans
                    )
                    if (section["text"] or "").strip() and (section["page_start"] is None or not mapped):
                        yield EvidenceUnit(
                            **base,
                            unit_id=f"section:{section['id']}",
                            section_id=section["id"],
                            source_span_id=None,
                            section_type=section["section_type"],
                            heading=section["heading"],
                            page_start=None,
                            page_end=None,
                            text=section["text"],
                            provenance_level=ProvenanceLevel.SECTION_ONLY,
                            provenance_source="sections",
                            evidence_role=section_role(section, section_map),
                        )
                if not sections and not spans:
                    for chunk in db.execute(
                        "SELECT * FROM chunks WHERE paper_id=? ORDER BY page,id", (paper["id"],)
                    ):
                        if (chunk["text"] or "").strip():
                            yield EvidenceUnit(
                                **base,
                                unit_id=f"chunk:{chunk['id']}",
                                section_id=None,
                                source_span_id=None,
                                section_type=None,
                                heading=None,
                                page_start=chunk["page"],
                                page_end=chunk["page"],
                                text=chunk["text"],
                                provenance_level=ProvenanceLevel.BASIC_PAGE_TEXT,
                                provenance_source="pypdf",
                            )
