import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys

import pytest
from make_fixtures import make_pdf
from petrus_engine.database import Database
from petrus_engine.jobs.scanner import Scanner, discover_pdfs, sha256_file
from petrus_engine.pdf.parser import SimplePdfParser, normalize_doi
from petrus_engine.pdf.worker import parse_pdf_isolated
from petrus_engine.service import Engine


@pytest.fixture
def env(tmp_path):
    library = tmp_path / "Research library ü"
    library.mkdir()
    engine = Engine(tmp_path / "data", start_worker=False)
    yield engine, library
    engine.close()


def scan(engine, path):
    response = engine.call("add_library", {"path": str(path)})
    with engine.db.connect() as db:
        row = db.execute("SELECT library_id FROM jobs WHERE id=?", (response["job_id"],)).fetchone()
    Scanner(engine.db).run(row[0], response["job_id"])
    return response["job_id"]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://doi.org/10.1234/ABC.123", "10.1234/abc.123"),
        ("doi: 10.1234/test(abc).", "10.1234/test(abc)"),
        ("(10.1000/XYZ);", "10.1000/xyz"),
        ("No DOI available", None),
        (None, None),
        ("10.12/invalid", None),
    ],
)
def test_doi_normalization(raw, expected):
    assert normalize_doi(raw) == expected


def test_recursive_unicode_discovery_and_symlink_policy(tmp_path):
    make_pdf(tmp_path / "Papers á" / "Study.PDF")
    make_pdf(tmp_path / ".cache" / "ignored.pdf")
    make_pdf(tmp_path / "~$temporary.pdf")
    (tmp_path / "readme.txt").write_text("not a PDF")
    (tmp_path / "link").symlink_to(tmp_path, target_is_directory=True)
    (tmp_path / "alias.pdf").symlink_to(tmp_path / "Papers á" / "Study.PDF")
    assert [p.name for p in discover_pdfs(tmp_path)] == ["Study.PDF"]


def test_sha256_known_digest(tmp_path):
    path = tmp_path / "bytes"
    path.write_bytes(b"abc")
    assert sha256_file(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_migrations_are_idempotent_and_enforce_relations(tmp_path):
    path = tmp_path / "data.sqlite3"
    Database(path)
    db = Database(path)
    with db.connect() as con:
        assert con.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 7
        assert con.execute("SELECT count(*) FROM sqlite_master WHERE name='paper_search'").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO paper_authors VALUES(999,999,0)")


def test_duplicate_content_has_multiple_locations_and_one_index(env):
    engine, library = env
    first = make_pdf(library / "one.pdf")
    shutil.copy2(first, library / "copy.pdf")
    scan(engine, library)
    assert engine.snapshot()["stats"]["papers"] == 1
    with engine.db.connect() as db:
        assert db.execute("SELECT count(*) FROM paper_files").fetchone()[0] == 2
        assert db.execute("SELECT count(*) FROM paper_search").fetchone()[0] == 1
    second = library.parent / "Another folder"
    second.mkdir()
    shutil.copy2(first, second / "same.pdf")
    scan(engine, second)
    assert engine.snapshot()["stats"]["papers"] == 1
    assert len(engine.paper_detail(1)["files"]) == 3


def test_rescan_new_modified_removed_and_restored(env):
    engine, library = env
    first = make_pdf(library / "one.pdf")
    original = first.read_bytes()
    scan(engine, library)
    scan(engine, library)
    assert engine.snapshot()["stats"]["papers"] == 1
    assert first.read_bytes() == original
    first.unlink()
    scan(engine, library)
    assert engine.list_papers({})["papers"][0]["status"] == "unavailable"
    first.write_bytes(original)
    scan(engine, library)
    assert engine.list_papers({})["papers"][0]["status"] == "ready"
    make_pdf(first, title="Changed version", body="Updated study 10.1234/changed")
    scan(engine, library)
    papers = engine.list_papers({})["papers"]
    assert len(papers) == 1
    assert papers[0]["title"] == "Changed version"
    assert engine.list_papers({"query": "updated"})["total"] == 1
    assert engine.list_papers({"query": "evolution"})["total"] == 0
    make_pdf(library / "new.pdf", title="New article")
    scan(engine, library)
    assert engine.snapshot()["stats"]["papers"] == 2


def test_corrupt_pdf_does_not_stop_other_papers(env):
    engine, library = env
    (library / "a-broken.pdf").write_bytes(b"not a valid PDF")
    make_pdf(library / "b-good.pdf")
    scan(engine, library)
    assert engine.snapshot()["stats"]["papers"] == 2
    assert engine.snapshot()["stats"]["indexed"] == 1
    assert engine.snapshot()["jobs"][0]["errors"] == 1
    assert engine.snapshot()["jobs"][0]["status"] == "warning"


def test_search_uses_extracted_body_and_handles_syntax(env):
    engine, library = env
    make_pdf(library / "one.pdf", body="Unique body keyword phylogeography. 10.1234/example")
    scan(engine, library)
    assert engine.list_papers({"query": "phylogeo"})["total"] == 1
    assert engine.list_papers({"query": "10.1234/example"})["total"] == 1
    assert engine.list_papers({"query": "Example Researcher"})["total"] == 1
    assert engine.list_papers({"query": '" OR *** --'})["total"] == 0
    assert engine.list_papers({"query": "***"})["total"] == 0
    assert engine.list_papers({"author": "nobody"})["total"] == 0


def test_parser_preserves_pages_and_does_not_invent_publication_year(tmp_path):
    path = make_pdf(tmp_path / "one.pdf")
    result = SimplePdfParser(path).parse_metadata()
    assert result.doi == "10.1234/petrus.test"
    assert result.authors == ["Example Researcher"]
    assert result.page_count == 1
    assert len(result.pages) == 1
    assert result.publication_year is None


def test_collection_author_graph_and_persistent_sessions_notes(env):
    engine, library = env
    make_pdf(library / "one.pdf")
    make_pdf(library / "two.pdf", title="Another paper", author="Different Author")
    scan(engine, library)
    engine.call("create_collection", {"name": "RSV"})
    for paper_id in (1, 2):
        engine.call("set_collection", {"paper_id": paper_id, "collection_id": 1, "selected": True})
    graph = engine.call("graph", {})
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["relation"] == "Same collection"
    assert engine.list_papers({"collection": 1})["total"] == 2
    engine.call(
        "new_session", {"title": "RSV surveillance", "question": "What is changing?", "description": "Scope"}
    )
    engine.call("save_notes", {"id": 1, "notes": "A traceable observation"})
    engine.call("save_settings", {"theme": "dark"})
    reopened = Engine(engine.data_dir, start_worker=False)
    assert reopened.snapshot()["settings"]["theme"] == "dark"
    assert reopened.snapshot()["sessions"][0]["research_question"] == "What is changing?"
    assert reopened.call("session", {"id": 1})["events"][0]["event_type"] == "session_created"
    assert reopened.paper_detail(1)["notes"] == "A traceable observation"
    reopened.close()


def test_shared_author_graph(env):
    engine, library = env
    make_pdf(library / "a.pdf")
    make_pdf(library / "b.pdf", title="Another title")
    scan(engine, library)
    assert engine.call("graph", {})["edges"][0]["relation"] == "Shared author"


def test_removing_library_keeps_originals_and_hides_orphan_graph(env):
    engine, library = env
    path = make_pdf(library / "one.pdf")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    scan(engine, library)
    engine.call("remove_library", {"id": 1})
    assert path.is_file()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert engine.list_papers({})["total"] == 0
    assert engine.call("graph", {})["nodes"] == []


def test_incomplete_traversal_does_not_mark_unseen_files_missing(env, monkeypatch):
    engine, library = env
    make_pdf(library / "one.pdf")
    scan(engine, library)

    def unreadable(_root, on_error):
        on_error(PermissionError("blocked directory"))
        return iter([])

    monkeypatch.setattr("petrus_engine.jobs.scanner.discover_pdfs", unreadable)
    scan(engine, library)
    assert engine.list_papers({})["papers"][0]["status"] == "ready"
    assert engine.snapshot()["jobs"][0]["status"] == "warning"


def test_json_lines_transport_and_shutdown(tmp_path):
    process = subprocess.Popen(
        [sys.executable, "-m", "petrus_engine", "--data-dir", str(tmp_path / "rpc")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    output, error = process.communicate(json.dumps({"id": 7, "method": "snapshot"}) + "\n", timeout=10)
    assert process.returncode == 0, error
    assert json.loads(output)["id"] == 7
    assert json.loads(output)["result"]["stats"]["papers"] == 0


def test_pdf_parser_timeout_terminates_worker(tmp_path):
    path = make_pdf(tmp_path / "timeout.pdf")
    with pytest.raises(ValueError, match="exceeded the 60-second limit"):
        parse_pdf_isolated(path, timeout=0.001)


def test_background_job_completes_and_original_stays_unchanged(tmp_path):
    import time

    library = tmp_path / "library"
    path = make_pdf(library / "paper.pdf")
    original = path.read_bytes()
    engine = Engine(tmp_path / "data")
    try:
        engine.call("add_library", {"path": str(library)})
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            snapshot = engine.snapshot()
            if snapshot["jobs"][0]["status"] not in ("queued", "running"):
                break
            time.sleep(0.05)
        assert snapshot["jobs"][0]["status"] == "completed"
        assert snapshot["stats"]["indexed"] == 1
        assert path.read_bytes() == original
    finally:
        engine.close()
