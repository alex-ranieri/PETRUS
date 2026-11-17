import json
import logging
from pathlib import Path

from petrus_engine.files import availability_provider
from petrus_engine.pdf.grobid import GrobidPdfParser, GrobidService
from petrus_engine.references import resolve_all
from petrus_engine.scientific_warnings import failure_codes, structure_codes

log = logging.getLogger(__name__)


class ScientificService:
    def __init__(self, database, settings):
        self.db, self.settings = database, settings
        self.grobid = GrobidService(settings().get("grobid_endpoint", "http://127.0.0.1:8070"))

    def configure(self):
        endpoint = self.settings().get("grobid_endpoint", "http://127.0.0.1:8070")
        if endpoint != self.grobid.endpoint:
            self.grobid = GrobidService(endpoint)

    def process(self, paper_id, path=None):
        self.configure()
        if self.settings().get("scientific_parser", "simple") != "grobid":
            return False
        with self.db.connect() as db:
            file = db.execute(
                "SELECT * FROM paper_files WHERE paper_id=? AND available=1 ORDER BY id", (paper_id,)
            ).fetchone()
            pages = [
                row[0]
                for row in db.execute("SELECT text FROM chunks WHERE paper_id=? ORDER BY page", (paper_id,))
            ]
        try:
            if not file:
                raise OSError("errors.fileUnavailable")
            path = Path(path or file["file_path"])
            info = path.stat(follow_symlinks=False)
            if not availability_provider().is_available(info):
                raise OSError("errors.fileUnavailable")
            # Reprocessing cannot attach new structured data to stale content identity.
            if (info.st_size, info.st_mtime_ns) != (file["file_size"], file["file_modified_at"]):
                raise ValueError("errors.rescanBeforeReprocess")
            document = GrobidPdfParser(path, self.grobid, pages).parse_metadata()
            final = path.stat(follow_symlinks=False)
            if (info.st_size, info.st_mtime_ns) != (final.st_size, final.st_mtime_ns):
                raise ValueError("errors.fileChanged")
            self.replace(paper_id, document)
            return True
        except Exception as exc:
            log.exception("scientific_parse_failed paper_id=%s", paper_id)
            warning = str(exc) if str(exc).startswith("errors.") else "errors.grobidFailed"
            codes = json.dumps(failure_codes(exc))
            with self.db.connect() as db:
                previous = db.execute("SELECT 1 FROM sections WHERE paper_id=?", (paper_id,)).fetchone()
                status = (
                    "structured_warning"
                    if previous
                    else ("basic" if self.settings().get("grobid_fallback", True) else "failed")
                )
                db.execute(
                    "UPDATE papers SET scientific_status=?,scientific_warning=?,scientific_warning_codes=?,scientific_updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (status, warning, codes, paper_id),
                )
                db.execute(
                    "INSERT INTO parser_runs(paper_id,parser,status,warnings_json,warning_codes_json) VALUES(?,'grobid','failed',?,?)",
                    (paper_id, json.dumps([warning]), codes),
                )
            return False

    def replace(self, paper_id, document):
        """Replace all derived structures atomically. The independent page layer is never deleted."""
        codes = json.dumps(structure_codes(document))
        with self.db.connect() as db:
            original = db.execute(
                "SELECT metadata_json FROM paper_basic_metadata WHERE paper_id=?", (paper_id,)
            ).fetchone()
            if original:
                basic = json.loads(original[0])
                if "authors" not in basic:
                    basic["authors"] = [
                        r[0]
                        for r in db.execute(
                            "SELECT a.name FROM authors a JOIN paper_authors pa ON pa.author_id=a.id WHERE pa.paper_id=? ORDER BY pa.author_order",
                            (paper_id,),
                        )
                    ]
                    db.execute(
                        "UPDATE paper_basic_metadata SET metadata_json=? WHERE paper_id=?",
                        (json.dumps(basic), paper_id),
                    )
            db.execute(
                "DELETE FROM edges WHERE relation='CITES' AND source_type='paper' AND source_id=?",
                (paper_id,),
            )
            db.execute("DELETE FROM source_spans WHERE paper_id=?", (paper_id,))
            db.execute("UPDATE chunks SET section_id=NULL WHERE paper_id=?", (paper_id,))
            db.execute("UPDATE evidence SET section_id=NULL WHERE paper_id=?", (paper_id,))
            db.execute("DELETE FROM sections WHERE paper_id=?", (paper_id,))
            db.execute('DELETE FROM "references" WHERE source_paper_id=?', (paper_id,))
            section_ids = {}
            for index, section in enumerate(document["sections"]):
                section_id = db.execute(
                    """INSERT INTO sections(paper_id,parent_section_id,section_type,heading,
                    section_order,page_start,page_end,text,tei_id) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        paper_id,
                        section_ids.get(section["parent"]),
                        section["section_type"],
                        section["heading"],
                        section["section_order"],
                        section["page_start"],
                        section["page_end"],
                        section["text"],
                        section["tei_id"],
                    ),
                ).lastrowid
                section_ids[index] = section_id
                self._spans(db, paper_id, section["spans"], section_id=section_id)
            for ref in document["references"]:
                reference_id = db.execute(
                    """INSERT INTO "references"(source_paper_id,citation_order,raw_citation,title,
                    authors_text,journal,year,doi,tei_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)""",
                    (
                        paper_id,
                        ref["citation_order"],
                        ref["raw_citation"],
                        ref["title"],
                        ref["authors_text"],
                        ref["journal"],
                        ref["year"],
                        ref["doi"],
                        ref["tei_id"],
                    ),
                ).lastrowid
                self._spans(db, paper_id, ref["spans"], reference_id=reference_id)
            meta = document["metadata"]
            db.execute(
                """UPDATE papers SET title=coalesce(?,title),doi=coalesce(?,doi),journal=coalesce(?,journal),
                publication_year=coalesce(?,publication_year),abstract=coalesce(?,abstract),scientific_status=?,
                scientific_warning=?,scientific_warning_codes=?,scientific_updated_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (
                    meta["title"],
                    meta["doi"],
                    meta["journal"],
                    meta["publication_year"],
                    meta["abstract"],
                    "structured_warning" if document["warnings"] else "structured",
                    json.dumps(document["warnings"]) if document["warnings"] else None,
                    codes,
                    paper_id,
                ),
            )
            if meta["authors"]:
                db.execute("DELETE FROM paper_authors WHERE paper_id=?", (paper_id,))
                for order, author in enumerate(meta["authors"]):
                    db.execute("INSERT OR IGNORE INTO authors(name) VALUES(?)", (author,))
                    author_id = db.execute("SELECT id FROM authors WHERE name=?", (author,)).fetchone()[0]
                    db.execute(
                        "INSERT OR IGNORE INTO paper_authors VALUES(?,?,?)", (paper_id, author_id, order)
                    )
            paper = db.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()
            authors = "; ".join(
                r[0]
                for r in db.execute(
                    "SELECT a.name FROM authors a JOIN paper_authors pa ON pa.author_id=a.id WHERE pa.paper_id=? ORDER BY pa.author_order",
                    (paper_id,),
                )
            )
            body = "\n\n".join(
                r[0]
                for r in db.execute("SELECT text FROM chunks WHERE paper_id=? ORDER BY page", (paper_id,))
            )
            db.execute("DELETE FROM paper_search WHERE rowid=?", (paper_id,))
            db.execute(
                "INSERT INTO paper_search(rowid,title,authors,doi,abstract,body) VALUES(?,?,?,?,?,?)",
                (paper_id, paper["title"], authors, paper["doi"], paper["abstract"], body),
            )
            db.execute(
                "INSERT INTO parser_runs(paper_id,parser,status,tei_xml,warnings_json,warning_codes_json) VALUES(?,'grobid',?,?,?,?)",
                (
                    paper_id,
                    paper["scientific_status"],
                    document["tei_xml"],
                    json.dumps(document["warnings"]),
                    codes,
                ),
            )
            resolve_all(db, paper_id)

    @staticmethod
    def _spans(db, paper_id, spans, section_id=None, reference_id=None):
        for span in spans:
            db.execute(
                """INSERT INTO source_spans(paper_id,section_id,reference_id,page,char_start,char_end,text,source_type,coordinates_json)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    paper_id,
                    section_id,
                    reference_id,
                    span["page"],
                    span["char_start"],
                    span["char_end"],
                    span["text"],
                    span["source_type"],
                    json.dumps(span["coordinates"]) if span["coordinates"] else None,
                ),
            )
