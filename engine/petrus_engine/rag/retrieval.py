"""FTS/semantic RRF with explicit roles, moderate section boosts and final diversity."""

import re
from dataclasses import asdict, replace

from petrus_engine.rag.contracts import RetrievalHit
from petrus_engine.rag.index import EmbeddingIndexService, current_units
from petrus_engine.rag.query import plan_query

RRF_K = 60
CANDIDATES = 30
SECTION_BOOST = 1.15


def serialize_hit(hit):
    return {
        **asdict(hit),
        "paper_id": hit.unit.paper_id,
        "title": hit.unit.title,
        "text_excerpt": hit.unit.text[:600],
        "supports_paginated_evidence": hit.unit.supports_paginated_evidence,
    }


def diversify(hits, limit, max_hits_per_paper=2):
    if max_hits_per_paper < 1:
        raise ValueError("invalid_diversity_limit")
    output = []
    used = set()
    counts = {}
    # First expose distinct papers, then a second passage; only fill overflow if needed.
    for cap in range(1, max_hits_per_paper + 1):
        for hit in hits:
            pid = hit.unit.paper_id
            if hit.unit.unit_id not in used and counts.get(pid, 0) < cap:
                output.append(hit)
                used.add(hit.unit.unit_id)
                counts[pid] = counts.get(pid, 0) + 1
                if len(output) == limit:
                    return output
    for hit in hits:
        if hit.unit.unit_id not in used:
            output.append(hit)
            if len(output) == limit:
                break
    return output


def finalize(hits, query, limit, max_hits_per_paper=2):
    plan = plan_query(query)
    boosted = [
        replace(h, section_boost=SECTION_BOOST if h.unit.evidence_role == plan.intent else 1.0) for h in hits
    ]
    boosted.sort(key=lambda h: (-h.score * h.section_boost, h.unit.unit_id))
    return diversify(boosted, limit, max_hits_per_paper)


class HybridRetriever:
    def __init__(self, database, provider=None, include_bibliography=False, max_hits_per_paper=2):
        self.database, self.provider = database, provider
        self.service = EmbeddingIndexService(database, provider) if provider is not None else None
        self.include_bibliography = include_bibliography
        self.max_hits_per_paper = max_hits_per_paper

    def units(self):
        return {
            key: u
            for key, u in current_units(self.database).items()
            if self.include_bibliography or u.evidence_role not in ("bibliography", "metadata")
        }

    def lexical_search(self, query, top_k=10, raw=False):
        tokens = re.findall(r"\w+", query.casefold())[:30]
        if not tokens:
            return []
        fts = " AND ".join('"' + t + '"*' for t in tokens)
        with self.database.connect() as db:
            papers = [
                r[0]
                for r in db.execute(
                    "SELECT rowid FROM paper_search WHERE paper_search MATCH ? ORDER BY bm25(paper_search),rowid LIMIT ?",
                    (fts, CANDIDATES),
                )
            ]
        units = self.units()
        hits = []
        for paper in papers:
            matches = [u for u in units.values() if u.paper_id == paper]
            matches.sort(
                key=lambda u: (-len(set(tokens) & set(re.findall(r"\w+", u.text.casefold()))), u.unit_id)
            )
            for unit in matches:
                hits.append(RetrievalHit(unit, 1 / (1 + len(hits)), lexical_rank=len(hits) + 1))
                if len(hits) >= CANDIDATES:
                    break
            if len(hits) >= CANDIDATES:
                break
        return hits[:top_k] if raw else finalize(hits, query, top_k, self.max_hits_per_paper)

    def semantic_search(self, query, top_k=10, raw=False):
        if self.service is None:
            raise ValueError("embedding_provider_not_configured")
        if not self.service.status()["current"]:
            return []
        vector = self.provider.embed_query(query)
        units = self.units()
        ranked = self.service.index.search(vector, CANDIDATES, include_bibliography=self.include_bibliography)
        hits = [
            RetrievalHit(units[uid], score, semantic_rank=rank)
            for rank, (uid, score) in enumerate(ranked, 1)
            if uid in units
        ]
        return hits[:top_k] if raw else finalize(hits, query, top_k, self.max_hits_per_paper)

    def hybrid_search(self, query, top_k=10, query_plan=None):
        plan = query_plan or plan_query(query)
        sources = [("lexical", self.lexical_search(query, CANDIDATES, raw=True))]
        for expanded in plan.expanded_terms[:3]:
            sources.append(("lexical", self.lexical_search(expanded, CANDIDATES, raw=True)))
        if self.service:
            sources.append(("semantic", self.semantic_search(query, CANDIDATES, raw=True)))
        combined = {}
        for source, hits in sources:
            for rank, hit in enumerate(hits, 1):
                entry = combined.setdefault(
                    hit.unit.unit_id,
                    {"unit": hit.unit, "lexical_rank": None, "semantic_rank": None, "score": 0.0},
                )
                previous = entry[source + "_rank"]
                entry[source + "_rank"] = min(previous, rank) if previous else rank
                entry["score"] += 1 / (RRF_K + rank)
        hits = [
            RetrievalHit(e["unit"], e["score"], e["lexical_rank"], e["semantic_rank"], e["score"])
            for e in combined.values()
        ]
        return finalize(hits, query, top_k, self.max_hits_per_paper)
