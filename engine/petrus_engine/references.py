"""Resolve only against the user's local catalog; fuzzy matches are candidates, never citations."""

import re
import unicodedata
from difflib import SequenceMatcher

from petrus_engine.pdf.parser import normalize_doi


def normalize_title(value):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value or "").casefold()))


def resolve_reference(reference, papers):
    candidates = [p for p in papers if p["id"] != reference["source_paper_id"]]
    ref_doi = normalize_doi(reference.get("doi"))
    if ref_doi:
        exact = [p for p in candidates if normalize_doi(p["doi"]) == ref_doi]
        if len(exact) == 1:
            return exact[0]["id"], "resolved", 1.0
        if len(exact) > 1:
            return None, "candidate", 1.0
    title = normalize_title(reference.get("title"))
    if len(title) < 30 or len(title.split()) < 5:
        return None, "unresolved", None
    compatible = [p for p in candidates if not (ref_doi and p["doi"] and normalize_doi(p["doi"]) != ref_doi)]
    exact = [p for p in compatible if normalize_title(p["title"]) == title]
    if len(exact) == 1:
        return exact[0]["id"], "resolved", 0.99
    if len(exact) > 1:
        return None, "candidate", 0.99
    words = set(title.split())
    scored = []
    for paper in compatible:
        other = paper.get("_title") or normalize_title(paper["title"])
        if (
            len(other) < 30
            or len(words & set(other.split())) / max(len(words), len(set(other.split())), 1) < 0.6
        ):
            continue
        scored.append((SequenceMatcher(None, title, other, autojunk=False).ratio(), paper["id"]))
    scored.sort(reverse=True)
    if scored and scored[0][0] >= 0.9:
        return scored[0][1], "candidate", round(scored[0][0], 4)
    return None, "unresolved", None


def resolve_all(db, source_paper_id=None):
    papers = [
        dict(row)
        for row in db.execute("""SELECT id,title,doi FROM papers p WHERE
        EXISTS(SELECT 1 FROM paper_files f WHERE f.paper_id=p.id)""")
    ]
    for paper in papers:
        paper["_title"] = normalize_title(paper["title"])
    query = 'SELECT * FROM "references"' + (" WHERE source_paper_id=?" if source_paper_id is not None else "")
    for row in db.execute(query, (source_paper_id,) if source_paper_id is not None else ()).fetchall():
        ref = dict(row)
        target, status, confidence = resolve_reference(ref, papers)
        db.execute(
            """UPDATE "references" SET target_paper_id=?,resolution_status=?,resolution_confidence=?,
                   resolved=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (target, status, confidence, int(status == "resolved"), ref["id"]),
        )
        db.execute("DELETE FROM edges WHERE relation='CITES' AND reference_id=?", (ref["id"],))
        if status == "resolved":
            db.execute(
                """INSERT INTO edges(source_type,source_id,relation,target_type,target_id,confidence,reference_id)
                VALUES('paper',?,'CITES','paper',?,?,?)""",
                (ref["source_paper_id"], target, confidence, ref["id"]),
            )
