"""Compare real retrieval on the isolated Arbovirus validation DB; never generates answers."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
from petrus_engine.rag.providers import configured_provider  # noqa: E402
from petrus_engine.rag.retrieval import HybridRetriever  # noqa: E402
from petrus_engine.service import Engine  # noqa: E402

LIBRARY = Path(
    "/Users/alexranieri/Library/CloudStorage/OneDrive-Pessoal/Butantan/V-GEN Lab/Arbovirus_evolution"
)
DEFAULT_DATA = ROOT / ".local-data/arbovirus-retrieval-validation"
QUERIES = [
    "arbovirus evolution",
    "recombination in arboviruses",
    "phylogenetic analysis of arboviruses",
    "genomic surveillance",
    "evolutionary dynamics of arboviruses",
    "evolução de arbovírus",
    "recombinação em arbovírus",
    "análise filogenética",
    "vigilância genômica",
    "dinâmica evolutiva dos arbovírus",
    "phylogenetic reconstruction method",
    "método de reconstrução filogenética",
    "software used for phylogenetic analysis",
    "software utilizado para análise filogenética",
    "phylogenetic analysis",
]


def open_validation(data_dir):
    data_dir = data_dir.resolve()
    if not data_dir.is_relative_to((ROOT / ".local-data").resolve()):
        raise ValueError("This evaluator only accepts development .local-data directories")
    database = data_dir / "petrus.sqlite3"
    if not database.is_file():
        raise ValueError("Validation database does not exist; catalog the test folder first")
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        libraries = [Path(row[0]).resolve() for row in db.execute("SELECT root_path FROM libraries")]
        if libraries != [LIBRARY.resolve()]:
            raise ValueError("Evaluator requires exclusively the Arbovirus_evolution library")
    return Engine(data_dir, start_worker=False)


def compact_hit(hit):
    unit = hit.unit
    return {
        "unit_id": unit.unit_id,
        "paper_id": unit.paper_id,
        "title": unit.title,
        "section_id": unit.section_id,
        "section_type": unit.section_type,
        "heading": unit.heading,
        "page_start": unit.page_start,
        "page_end": unit.page_end,
        "source_span_id": unit.source_span_id,
        "provenance": unit.provenance_level.value,
        "evidence_role": unit.evidence_role,
        "parent_unit_id": unit.parent_unit_id,
        "section_boost": hit.section_boost,
        "provenance_source": unit.provenance_source,
        "supports_paginated_evidence": unit.supports_paginated_evidence,
        "excerpt": unit.text[:500],
        "score": hit.score,
        "lexical_rank": hit.lexical_rank,
        "semantic_rank": hit.semantic_rank,
        "hybrid_score": hit.hybrid_score,
    }


def evaluate(engine, query, mode="all", top_k=5):
    provider = configured_provider(engine.get_settings())
    retriever = HybridRetriever(engine.db, provider)
    modes = ("lexical", "semantic", "hybrid") if mode == "all" else (mode,)
    result = {"query": query, "modes": {}}
    for name in modes:
        if provider is None and name != "lexical":
            result["modes"][name] = {
                "status": "not_run",
                "reason": "embedding_provider_not_configured",
                "hits": [],
            }
            continue
        try:
            hits = getattr(retriever, name + "_search")(query, top_k)
            result["modes"][name] = {"status": "ok", "hits": [compact_hit(hit) for hit in hits]}
        except Exception as exc:
            result["modes"][name] = {"status": "error", "error": str(exc), "hits": []}
    return result


def render(result):
    lines = ["QUERY:", result["query"]]
    for mode, data in result["modes"].items():
        lines.extend(["", mode.upper(), "Status: " + data["status"]])
        if data["status"] != "ok":
            lines.append(data.get("error", data.get("reason", "")))
        for rank, hit in enumerate(data["hits"], 1):
            lines.extend(
                [
                    f"{rank}. [P{hit['paper_id']}] {hit['title']}",
                    f"   Unit: {hit['unit_id']} | Section: {hit['heading'] or hit['section_type'] or 'unstructured'}",
                    f"   Pages: {hit['page_start']}–{hit['page_end']} | Provenance: {hit['provenance']}",
                    f"   Paginated evidence: {hit['supports_paginated_evidence']}",
                    f"   Score: {hit['score']:.6f} | lexical_rank={hit['lexical_rank']} | semantic_rank={hit['semantic_rank']} | hybrid_score={hit['hybrid_score']}",
                    "   Excerpt: " + hit["excerpt"].replace("\n", " "),
                ]
            )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--query", required=True)
    parser.add_argument("--mode", choices=("all", "lexical", "semantic", "hybrid"), default="all")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.query.strip() or not 1 <= args.top_k <= 100:
        parser.error("Nonempty query and top-k 1–100 required")
    engine = open_validation(args.data_dir)
    try:
        result = evaluate(engine, args.query, args.mode, args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render(result))
        if any(data["status"] == "error" for data in result["modes"].values()):
            raise SystemExit(1)
    finally:
        engine.close()


if __name__ == "__main__":
    main()
