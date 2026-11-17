"""Explicit real-library validation on a SQLite backup; never writes to source PDFs or source DB."""

import argparse
import json
import sqlite3
import time
from pathlib import Path

from petrus_engine.files import availability_provider
from petrus_engine.jobs.scanner import Scanner, discover_pdfs
from petrus_engine.references import resolve_all
from petrus_engine.service import Engine

parser = argparse.ArgumentParser()
parser.add_argument("--source-db", type=Path, required=True)
parser.add_argument("--library", type=Path, required=True)
parser.add_argument("--data-dir", type=Path, required=True)
parser.add_argument("--limit", type=int)
args = parser.parse_args()
args.data_dir.mkdir(parents=True, exist_ok=True)
destination = args.data_dir / "petrus.sqlite3"
if args.source_db.resolve() == destination.resolve():
    raise ValueError("Validation must use a separate database")
with (
    sqlite3.connect(args.source_db.resolve().as_uri() + "?mode=ro", uri=True) as source,
    sqlite3.connect(destination) as target,
):
    source.backup(target)
engine = Engine(args.data_dir, start_worker=False)
engine.call(
    "save_settings",
    {
        "auto_scan": False,
        "watch_folders": False,
        "scientific_parser": "grobid",
        "grobid_endpoint": "http://127.0.0.1:8070",
        "language": "en",
    },
)
assert engine.call("grobid_health", {})["state"] == "available", "Local GROBID is not ready"
job = engine.call("add_library", {"path": str(args.library)})["job_id"]
with engine.db.connect() as db:
    library_id = db.execute("SELECT library_id FROM jobs WHERE id=?", (job,)).fetchone()[0]
Scanner(engine.db).run(library_id, job)
with engine.db.connect() as db:
    ids = [
        r[0]
        for r in db.execute(
            """SELECT DISTINCT p.id FROM papers p JOIN paper_files f ON f.paper_id=p.id
 WHERE f.library_id=? AND f.available=1 ORDER BY (p.page_count BETWEEN 3 AND 30 AND p.doi IS NOT NULL) DESC,p.id""",
            (library_id,),
        )
    ]
    if args.limit:
        ids = ids[: args.limit]
files = list(discover_pdfs(args.library))
provider = availability_provider()
local = sum(provider.is_available(p.stat(follow_symlinks=False)) for p in files)
parsed = failed = 0
start = time.monotonic()
try:
    for index, paper_id in enumerate(ids, 1):
        ok = engine.scientific.process(paper_id)
        parsed += ok
        failed += not ok
        print(
            json.dumps({"completed": index, "total": len(ids), "structured": parsed, "failed": failed}),
            flush=True,
        )
        if index == 3 and parsed == 0:
            raise RuntimeError("First three GROBID parses failed; inspect local logs before continuing")
    with engine.db.connect() as db:
        resolve_all(db)
        summary = {
            "pdf_locations": len(files),
            "local_pdf_locations": local,
            "cloud_or_unavailable_locations": len(files) - local,
            "unique_papers_attempted": len(ids),
            "grobid_parsed": parsed,
            "grobid_failed": failed,
            "references_extracted": db.execute('SELECT count(*) FROM "references"').fetchone()[0],
            "references_resolved": db.execute(
                "SELECT count(*) FROM \"references\" WHERE resolution_status='resolved'"
            ).fetchone()[0],
            "reference_candidates": db.execute(
                "SELECT count(*) FROM \"references\" WHERE resolution_status='candidate'"
            ).fetchone()[0],
            "citation_edges": db.execute("SELECT count(*) FROM edges WHERE relation='CITES'").fetchone()[0],
            "sections": db.execute("SELECT count(*) FROM sections").fetchone()[0],
            "mapped_sections": db.execute(
                "SELECT count(*) FROM sections WHERE page_start IS NOT NULL"
            ).fetchone()[0],
            "source_spans": db.execute("SELECT count(*) FROM source_spans").fetchone()[0],
            "elapsed_seconds": round(time.monotonic() - start, 2),
        }
    (args.data_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)
finally:
    engine.close()
