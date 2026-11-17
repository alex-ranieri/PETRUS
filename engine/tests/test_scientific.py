import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import pytest
from make_fixtures import make_pdf
from petrus_engine.database import Database
from petrus_engine.files import GenericFileAvailabilityProvider, MacOSFileAvailabilityProvider
from petrus_engine.jobs.scanner import Scanner
from petrus_engine.pdf.grobid import GrobidService
from petrus_engine.pdf.tei import PageMapper, heading_type, parse_tei
from petrus_engine.references import normalize_title, resolve_reference
from petrus_engine.service import Engine

FIXTURE = Path(__file__).parent / "fixtures/scientific.tei.xml"
SOURCE = "Evidence for viral evolution. DOI: 10.1234/petrus.test"


def test_tei_metadata_nested_sections_and_references():
    doc = parse_tei(FIXTURE.read_text(), [SOURCE])
    assert doc["metadata"]["title"] == "Synthetic viral evolution"
    assert doc["metadata"]["authors"] == ["Example Researcher"]
    assert doc["metadata"]["publication_year"] == 2026
    methods = next(s for s in doc["sections"] if s["tei_id"] == "methods")
    nested = next(s for s in doc["sections"] if s["tei_id"] == "sampling")
    assert methods["section_type"] == "methods"
    assert methods["heading"] == "Materials and Methods"
    assert nested["parent"] == methods["section_order"]
    assert nested["page_start"] is None
    assert "warnings.unmappedSection" in doc["warnings"]
    assert len(doc["references"]) == 2
    ref = doc["references"][0]
    assert ref["doi"] == "10.5678/test.2026"
    assert ref["citation_order"] == 1
    assert ref["authors_text"] == "Example Researcher"
    assert ref["journal"] == "Controlled Journal"
    assert any(s["page"] == 1 for s in ref["spans"])


@pytest.mark.parametrize(
    "heading",
    [
        "Methods",
        "Materials and Methods",
        "Materials & Methods",
        "Experimental Procedures",
        "Methodology",
        "Métodos",
        "Materiais e Métodos",
        "Metodologia",
        "2. Materials and Methods",
    ],
)
def test_methods_normalization(heading):
    assert heading_type(heading) == "methods"


def test_page_mapping_exact_unique_conservative_and_coordinates():
    import xml.etree.ElementTree as ET

    paragraph = "This controlled scientific paragraph contains enough unique words to map reliably."
    node = ET.fromstring("<p>" + paragraph + "</p>")
    mapper = PageMapper(["First page.", paragraph])
    spans = mapper.map(node)
    assert spans[0]["page"] == 2
    assert spans[0]["text"] == paragraph.rstrip(".")
    assert (
        spans[0]["char_start"] == 0 and spans[0]["char_end"] == len(paragraph) - 1
    )  # trailing punctuation is outside token offsets
    assert PageMapper([paragraph, paragraph]).map(node) == []
    assert PageMapper(["unrelated text"]).map(node) == []
    coordinate = ET.fromstring('<p coords="2,10,20,30,40">A short source quote</p>')
    mapped = PageMapper(["", ""]).map(coordinate)
    assert mapped[0]["page"] == 2 and mapped[0]["source_type"] == "grobid_coordinates"
    coordinate.set("coords", "99,10,20,30,40")
    assert PageMapper([""]).map(coordinate) == []


def test_alignment_across_two_pages():
    import xml.etree.ElementTree as ET

    pages = ["This controlled paragraph spans two", "pages and preserves each original source excerpt."]
    spans = PageMapper(pages).map(ET.fromstring("<p>" + " ".join(pages) + "</p>"))
    assert [s["page"] for s in spans] == [1, 2]
    assert spans[0]["text"] == pages[0]
    assert spans[1]["text"] == pages[1].rstrip(".")


@pytest.mark.parametrize("xml", ["<invalid/>", "not xml", '<!DOCTYPE TEI [<!ENTITY x "expanded">]><TEI/>'])
def test_invalid_tei_rejected(xml):
    with pytest.raises(ValueError, match="invalidTei"):
        parse_tei(xml, [])


def test_local_resolution_exact_doi_title_candidate_and_false_positives():
    papers = [
        {
            "id": 2,
            "title": "Characterizing viral evolutionary dynamics within human hosts",
            "doi": "10.1234/exact",
        }
    ]
    ref = {"source_paper_id": 1, "doi": "https://doi.org/10.1234/EXACT.", "title": None}
    assert resolve_reference(ref, papers) == (2, "resolved", 1.0)
    title = " CHARACTERIZING viral evolutionary dynamics, within human hosts! "
    assert normalize_title(title) == normalize_title(papers[0]["title"])
    ref.update(doi=None, title=title)
    assert resolve_reference(ref, papers)[1] == "resolved"
    ref["title"] = "Characterizing viral evolutionary dynamics within animal hosts"
    assert resolve_reference(ref, papers)[1] == "candidate"
    ref.update(doi="10.5555/conflicting", title=papers[0]["title"])
    assert resolve_reference(ref, papers)[1] == "unresolved"
    ref.update(doi=None, title="Introduction")
    assert resolve_reference(ref, papers)[1] == "unresolved"
    assert (
        resolve_reference(
            {"source_paper_id": 2, "doi": "10.1234/exact", "title": papers[0]["title"]}, papers
        )[1]
        == "unresolved"
    )
    assert (
        resolve_reference({"source_paper_id": 1, "authors_text": "same author", "year": 2026}, papers)[1]
        == "unresolved"
    )


@pytest.fixture
def scientific_env(tmp_path):
    engine = Engine(tmp_path / "data", start_worker=False)
    library = tmp_path / "library"
    make_pdf(library / "evolution.pdf")
    make_pdf(
        library / "surveillance.pdf",
        title="Synthetic surveillance study",
        body="Genomic surveillance and sample testing. 10.5678/test.2026",
    )
    job = engine.call("add_library", {"path": str(library)})["job_id"]
    Scanner(engine.db).run(1, job)
    yield engine, library
    engine.close()


def test_idempotent_replacement_citation_direction_and_page_layer(scientific_env):
    engine, library = scientific_env
    doc = parse_tei(FIXTURE.read_text(), [SOURCE])
    with engine.db.connect() as db:
        before = [tuple(r) for r in db.execute("SELECT page,text FROM chunks WHERE paper_id=1")]
    for _ in range(2):
        engine.scientific.replace(1, doc)
    detail = engine.paper_detail(1)
    assert len(detail["references"]) == 2
    assert len(detail["sections"]) == 5
    assert "page_mapping_missing" in json.loads(detail["scientific_warning_codes"])
    with engine.db.connect() as db:
        codes = db.execute("SELECT warning_codes_json FROM parser_runs ORDER BY id DESC LIMIT 1").fetchone()[
            0
        ]
        assert codes == detail["scientific_warning_codes"]
    assert detail["references"][0]["target_paper_id"] == 2
    assert detail["references"][0]["resolution_status"] == "resolved"
    with engine.db.connect() as db:
        assert [tuple(r) for r in db.execute("SELECT page,text FROM chunks WHERE paper_id=1")] == before
        edge = db.execute("SELECT source_id,target_id,relation FROM edges WHERE relation='CITES'").fetchall()
        assert [tuple(r) for r in edge] == [(1, 2, "CITES")]
    graph = engine.call("graph", {})
    assert any(e["type"] == "CITES" and e["source"] == "1" and e["target"] == "2" for e in graph["edges"])
    assert len([e for e in graph["edges"] if e["type"] == "SHARED_AUTHOR"]) == 1
    assert (
        engine.list_papers({"query": "Synthetic Journal"})["total"] == 0
    )  # journal is a filter, not in the declared FTS contract


@pytest.mark.parametrize(
    "failure", [ConnectionError("offline"), ValueError("errors.invalidTei"), TimeoutError("timeout")]
)
def test_grobid_failure_preserves_basic_layer(scientific_env, monkeypatch, failure):
    engine, library = scientific_env
    engine.call("save_settings", {"scientific_parser": "grobid"})

    def fail(_path):
        raise failure

    monkeypatch.setattr(engine.scientific.grobid, "process", fail)
    assert engine.scientific.process(1) is False
    detail = engine.paper_detail(1)
    assert detail["scientific_status"] == "basic"
    expected = (
        "grobid_timeout"
        if isinstance(failure, TimeoutError)
        else "grobid_unavailable"
        if isinstance(failure, ConnectionError)
        else "grobid_invalid_response"
    )
    assert json.loads(detail["scientific_warning_codes"]) == [expected]
    with engine.db.connect() as db:
        assert json.loads(
            db.execute("SELECT warning_codes_json FROM parser_runs ORDER BY id DESC LIMIT 1").fetchone()[0]
        ) == [expected]
    assert detail["index_status"] == "indexed"
    assert engine.call("content", {"id": 1})["page"]["text"]


def test_successful_parse_then_transient_failure_retains_last_good_structure(scientific_env, monkeypatch):
    engine, _ = scientific_env
    engine.call("save_settings", {"scientific_parser": "grobid"})
    monkeypatch.setattr(engine.scientific.grobid, "process", lambda _path: FIXTURE.read_text())
    assert engine.scientific.process(1)
    monkeypatch.setattr(engine.scientific.grobid, "process", lambda _path: "<invalid/>")
    assert not engine.scientific.process(1)
    assert len(engine.paper_detail(1)["references"]) == 2
    assert engine.paper_detail(1)["scientific_status"] == "structured_warning"


def test_rescan_uses_stat_cache_but_integrity_forces_hash(scientific_env, monkeypatch):
    engine, library = scientific_env

    def forbidden(_path):
        raise AssertionError("Unexpected rehash")

    monkeypatch.setattr("petrus_engine.jobs.scanner.sha256_file", forbidden)
    Scanner(engine.db).run(1, 1)
    assert engine.snapshot()["jobs"][0]["errors"] == 0
    Scanner(engine.db).run(1, 1, verify_integrity=True)
    assert engine.snapshot()["jobs"][0]["errors"] == 2


def test_change_triggers_rehash(scientific_env, monkeypatch):
    from petrus_engine.jobs.scanner import sha256_file

    engine, library = scientific_env
    calls = []
    monkeypatch.setattr(
        "petrus_engine.jobs.scanner.sha256_file", lambda p: (calls.append(p), sha256_file(p))[1]
    )
    make_pdf(library / "evolution.pdf", title="Modified synthetic article")
    Scanner(engine.db).run(1, 1)
    assert [p.name for p in calls] == ["evolution.pdf"]


def test_availability_provider_is_separate():
    info = SimpleNamespace(st_mode=0o100644, st_flags=0x40000000)
    assert not MacOSFileAvailabilityProvider().is_available(info)
    assert GenericFileAvailabilityProvider().is_available(info)


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://127.0.0.1:8070",
        "http://example.com",
        "http://127.0.0.1@evil.com",
        "http://127.0.0.1/path",
        "http://127.0.0.2:8070",
    ],
)
def test_grobid_rejects_remote_endpoints(endpoint):
    with pytest.raises(ValueError, match="localEndpointOnly"):
        GrobidService(endpoint)


def test_adapter_local_http_only_no_consolidation_or_redirect(tmp_path):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"true")

        def do_POST(self):
            requests.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(FIXTURE.read_bytes())

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        service = GrobidService(f"http://127.0.0.1:{server.server_port}")
        assert service.health()["state"] == "available"
        result = service.process(make_pdf(tmp_path / "paper.pdf"))
        assert "<TEI" in result
        body = requests[0]
        for field in ["consolidateHeader", "consolidateCitations", "consolidateFunders"]:
            assert (f'name="{field}"\r\n\r\n0').encode() in body
        assert b"teiCoordinates" in body

        def redirect(self):
            self.send_response(302)
            self.send_header("Location", "https://example.com")
            self.end_headers()

        Handler.do_POST = redirect
        with pytest.raises(ValueError):
            service.process(tmp_path / "paper.pdf")
    finally:
        server.shutdown()
        server.server_close()


def test_001_upgrade_preserves_library_notes_and_settings(tmp_path):
    path = tmp_path / "upgrade.sqlite3"
    db = sqlite3.connect(path)
    db.executescript((Path(__file__).parents[2] / "src-tauri/migrations/001_initial.sql").read_text())
    db.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY)")
    db.execute("INSERT INTO schema_migrations VALUES('001_initial.sql')")
    db.execute("INSERT INTO libraries(name,root_path) VALUES('Existing','/existing')")
    db.execute(
        "INSERT INTO papers(file_hash,file_name,title,notes) VALUES('hash','a.pdf','Original title','Original note')"
    )
    db.execute("INSERT INTO settings VALUES('theme','\"dark\"')")
    db.commit()
    db.close()
    migrated = Database(path)
    with migrated.connect() as con:
        assert con.execute("SELECT notes FROM papers").fetchone()[0] == "Original note"
        assert (
            json.loads(con.execute("SELECT metadata_json FROM paper_basic_metadata").fetchone()[0])["title"]
            == "Original title"
        )
        assert con.execute("SELECT count(*) FROM libraries").fetchone()[0] == 1
        assert con.execute("SELECT value FROM settings").fetchone()[0] == '"dark"'


def test_scientific_job_queue_updates_progress_and_deduplicates(tmp_path, monkeypatch):
    import time

    library = tmp_path / "library"
    make_pdf(library / "evolution.pdf")
    make_pdf(
        library / "surveillance.pdf",
        title="Synthetic surveillance study",
        body="Genomic surveillance and sample testing. 10.5678/test.2026",
    )
    engine = Engine(tmp_path / "data")

    def wait(job_id):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            snapshot = engine.snapshot()
            job = next(j for j in snapshot["jobs"] if j["id"] == job_id)
            if job["status"] not in ("queued", "running"):
                return job
            time.sleep(0.02)
        raise AssertionError("Job did not finish")

    try:
        initial = engine.call("add_library", {"path": str(library)})["job_id"]
        assert wait(initial)["status"] == "completed"
        engine.call("save_settings", {"scientific_parser": "grobid"})

        def parse(_path):
            time.sleep(0.1)
            return FIXTURE.read_text()

        monkeypatch.setattr(engine.scientific.grobid, "process", parse)
        job = engine.call("reprocess_scientific", {"paper_id": 1})["job_id"]
        assert engine.call("reprocess_scientific", {"paper_id": 1})["job_id"] == job
        result = wait(job)
        assert result["status"] == "completed"
        assert result["completed"] == result["total"] == 1
        assert engine.paper_detail(1)["references"][0]["resolution_status"] == "resolved"
    finally:
        engine.close()


def test_integrity_detects_same_size_same_mtime_tampering(scientific_env):
    import os

    engine, library = scientific_env
    path = library / "evolution.pdf"
    info = path.stat()
    before = path.read_bytes()
    after = before.replace(b"Synthetic", b"Modified!")
    assert len(before) == len(after)
    path.write_bytes(after)
    os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
    with engine.db.connect() as db:
        old = db.execute("SELECT paper_id FROM paper_files WHERE file_name=?", ("evolution.pdf",)).fetchone()[
            0
        ]
    Scanner(engine.db).run(1, 1)
    with engine.db.connect() as db:
        assert (
            db.execute("SELECT paper_id FROM paper_files WHERE file_name=?", ("evolution.pdf",)).fetchone()[0]
            == old
        )
    Scanner(engine.db).run(1, 1, verify_integrity=True)
    with engine.db.connect() as db:
        assert (
            db.execute("SELECT paper_id FROM paper_files WHERE file_name=?", ("evolution.pdf",)).fetchone()[0]
            != old
        )
