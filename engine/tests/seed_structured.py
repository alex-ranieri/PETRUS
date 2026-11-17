"""Controlled fixture injection for UI tests; never used by the product runtime."""

import sys
from pathlib import Path

from petrus_engine.database import Database
from petrus_engine.pdf.tei import parse_tei
from petrus_engine.scientific import ScientificService

db = Database(Path(sys.argv[1]) / "petrus.sqlite3")
with db.connect() as con:
    paper_id = con.execute("SELECT id FROM papers WHERE title='Synthetic viral evolution'").fetchone()[0]
    pages = [r[0] for r in con.execute("SELECT text FROM chunks WHERE paper_id=? ORDER BY page", (paper_id,))]
ScientificService(db, lambda: {}).replace(
    paper_id, parse_tei((Path(__file__).parent / "fixtures/scientific.tei.xml").read_text(), pages)
)
