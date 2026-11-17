import hashlib
import json
import logging
import os
import uuid
from pathlib import Path

from petrus_engine.database import Database
from petrus_engine.files import availability_provider
from petrus_engine.pdf.worker import parse_pdf_isolated
from petrus_engine.references import resolve_all

log = logging.getLogger(__name__)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover_pdfs(root: Path, on_error=None):
    """Do not follow symlinks; walk errors don't turn into a successful removal sweep."""

    def error(exc):
        log.warning("directory_unreadable path=%s error=%s", exc.filename, exc)
        if on_error:
            on_error(exc)

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=error):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not Path(directory, d).is_symlink())
        for name in sorted(files):
            path = Path(directory, name)
            if name.lower().endswith(".pdf") and not name.startswith((".", "~$")) and not path.is_symlink():
                yield path


class Scanner:
    def __init__(self, database: Database, stop=None, scientific=None):
        self.database = database
        self.stop = stop
        self.scientific = scientific
        self.availability = availability_provider()
        self.verify = False

    def update_job(self, job_id: int, **fields):
        with self.database.connect() as db:
            db.execute(
                "UPDATE jobs SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?",
                (*fields.values(), job_id),
            )

    def run(self, library_id: int, job_id: int, verify_integrity=False):
        self.verify = verify_integrity
        token = str(uuid.uuid4())
        with self.database.connect() as db:
            library = db.execute("SELECT * FROM libraries WHERE id=?", (library_id,)).fetchone()
        if library is None:
            return
        root = Path(library["root_path"])
        self.update_job(job_id, status="running", stage="discovered", message="Discovering PDFs…")
        walk_errors = []
        if not root.is_dir():
            raise FileNotFoundError("Library folder is not currently available. Reconnect it and rescan.")
        paths = list(discover_pdfs(root, walk_errors.append))
        self.update_job(job_id, total=len(paths))
        errors = len(walk_errors)
        for index, path in enumerate(paths):
            if self.stop and self.stop.is_set():
                self.update_job(job_id, status="interrupted", message="Scan interrupted. Rescan to continue.")
                return
            self.update_job(job_id, stage="hashing", message=path.name, completed=index)
            try:
                self.ingest(path, library_id, token, job_id)
            except Exception as exc:
                errors += 1
                log.exception("pdf_ingestion_failed path=%s", path)
                # Keep the prior content record when a file temporarily cannot be read.
                with self.database.connect() as db:
                    db.execute(
                        """INSERT INTO paper_files(library_id,file_path,file_name,available,error,seen_scan)
                        VALUES(?,?,?,?,?,?) ON CONFLICT(library_id,file_path) DO UPDATE SET
                        available=excluded.available,error=excluded.error,seen_scan=excluded.seen_scan""",
                        (
                            library_id,
                            str(path),
                            path.name,
                            int(not isinstance(exc, OSError)),
                            self.friendly_error(exc),
                            token,
                        ),
                    )
            self.update_job(job_id, completed=index + 1, errors=errors)
        with self.database.connect() as db:
            # If traversal failed, unseen files may still exist in inaccessible directories.
            # Retain them until a complete traversal proves they are missing.
            if not walk_errors:
                db.execute(
                    """UPDATE paper_files SET available=0,error='File is no longer available at this location.'
                           WHERE library_id=? AND (seen_scan IS NULL OR seen_scan!=?)""",
                    (library_id, token),
                )
            db.execute("UPDATE libraries SET last_scan_at=CURRENT_TIMESTAMP WHERE id=?", (library_id,))
            resolve_all(db)
            db.execute(
                """UPDATE jobs SET status=?,stage='indexed',message=?,errors=?,
                       finished_at=CURRENT_TIMESTAMP WHERE id=?""",
                (
                    "warning" if errors else "completed",
                    f"{len(paths)} PDFs checked" + (f" · {errors} warnings" if errors else ""),
                    errors,
                    job_id,
                ),
            )
        log.info("scan_finished library_id=%s files=%s errors=%s", library_id, len(paths), errors)

    @staticmethod
    def friendly_error(exc: Exception) -> str:
        if isinstance(exc, PermissionError):
            return "Permission denied. Check access to this file or folder."
        if isinstance(exc, (FileNotFoundError, OSError)):
            return "File is not currently available locally. Make it available offline and rescan."
        if "exceeded the 60-second limit" in str(exc):
            return "PDF parsing timed out. Other files will continue."
        return "Could not read this PDF. Metadata extraction failed."

    def ingest(self, path: Path, library_id: int, token: str, job_id: int):
        info = path.stat(follow_symlinks=False)
        if not self.availability.is_available(info):
            raise OSError("File is only available on demand")
        with self.database.connect() as db:
            known = db.execute(
                """SELECT f.*,p.metadata_status,p.file_hash FROM paper_files f JOIN papers p ON p.id=f.paper_id
                WHERE f.library_id=? AND f.file_path=?""",
                (library_id, str(path)),
            ).fetchone()
            if (
                known
                and not self.verify
                and known["file_size"] == info.st_size
                and known["file_modified_at"] == info.st_mtime_ns
                and known["metadata_status"] in ("ready", "warning")
            ):
                db.execute(
                    "UPDATE paper_files SET available=1,error=NULL,seen_scan=? WHERE id=?",
                    (token, known["id"]),
                )
                return
        cached = (
            known
            and not self.verify
            and known["file_size"] == info.st_size
            and known["file_modified_at"] == info.st_mtime_ns
        )
        digest = known["file_hash"] if cached else sha256_file(path)
        after = path.stat(follow_symlinks=False)
        if (after.st_size, after.st_mtime_ns) != (info.st_size, info.st_mtime_ns):
            raise OSError("File changed while hashing; rescan when the file is stable")
        with self.database.connect() as db:
            existing = db.execute(
                "SELECT id,metadata_status FROM papers WHERE file_hash=?", (digest,)
            ).fetchone()
            if existing is None:
                paper_id = db.execute(
                    """INSERT INTO papers(file_hash,file_name,title,metadata_status)
                    VALUES(?,?,?,'processing')""",
                    (digest, path.name, path.stem),
                ).lastrowid
                db.execute("INSERT INTO paper_search(rowid,title) VALUES(?,?)", (paper_id, path.stem))
            else:
                paper_id = existing["id"]
            db.execute(
                """INSERT INTO paper_files(paper_id,library_id,file_path,file_name,file_size,file_modified_at,seen_scan)
                VALUES(?,?,?,?,?,?,?) ON CONFLICT(library_id,file_path) DO UPDATE SET
                paper_id=excluded.paper_id,file_size=excluded.file_size,file_modified_at=excluded.file_modified_at,
                seen_scan=excluded.seen_scan,available=1,error=NULL""",
                (paper_id, library_id, str(path), path.name, info.st_size, info.st_mtime_ns, token),
            )
        if existing and existing["metadata_status"] in ("ready", "warning"):
            return
        self.update_job(job_id, stage="metadata")
        try:
            self.update_job(job_id, stage="text_extraction")
            parsed = parse_pdf_isolated(path)
            # Verify the parser read the version whose hash is stored.
            final = path.stat(follow_symlinks=False)
            if (final.st_size, final.st_mtime_ns) != (info.st_size, info.st_mtime_ns):
                raise OSError("File changed during parsing")
            with self.database.connect() as db:
                db.execute(
                    """UPDATE papers SET title=?,doi=?,journal=?,publication_year=?,abstract=?,
                    metadata_status=?,index_status='indexed',page_count=?,warning=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                    (
                        parsed.title,
                        parsed.doi,
                        parsed.journal,
                        parsed.publication_year,
                        parsed.abstract,
                        "warning" if parsed.warning else "ready",
                        parsed.page_count,
                        parsed.warning,
                        paper_id,
                    ),
                )
                db.execute("DELETE FROM paper_authors WHERE paper_id=?", (paper_id,))
                for order, author in enumerate(parsed.authors):
                    db.execute("INSERT OR IGNORE INTO authors(name) VALUES(?)", (author,))
                    author_id = db.execute("SELECT id FROM authors WHERE name=?", (author,)).fetchone()[0]
                    db.execute(
                        "INSERT OR IGNORE INTO paper_authors VALUES(?,?,?)", (paper_id, author_id, order)
                    )
                db.execute("DELETE FROM chunks WHERE paper_id=?", (paper_id,))
                db.executemany(
                    "INSERT INTO chunks(paper_id,page,chunk_order,text) VALUES(?,?,?,?)",
                    ((paper_id, index + 1, index, text) for index, text in enumerate(parsed.pages)),
                )
                db.execute("DELETE FROM paper_search WHERE rowid=?", (paper_id,))
                db.execute(
                    "INSERT INTO paper_search(rowid,title,authors,doi,abstract,body) VALUES(?,?,?,?,?,?)",
                    (
                        paper_id,
                        parsed.title,
                        "; ".join(parsed.authors),
                        parsed.doi,
                        parsed.abstract,
                        "\n\n".join(parsed.pages),
                    ),
                )
                basic = {
                    key: getattr(parsed, key)
                    for key in ("title", "authors", "doi", "journal", "publication_year", "abstract")
                }
                db.execute(
                    "INSERT OR REPLACE INTO paper_basic_metadata VALUES(?,?)", (paper_id, json.dumps(basic))
                )
            if self.scientific:
                self.update_job(job_id, stage="scientific_parsing")
                self.scientific.process(paper_id, path)
        except Exception:
            with self.database.connect() as db:
                db.execute(
                    "UPDATE papers SET metadata_status='failed',warning='Metadata extraction failed.' WHERE id=?",
                    (paper_id,),
                )
            raise
