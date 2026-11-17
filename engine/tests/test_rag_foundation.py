import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest
from petrus_engine.database import Database
from petrus_engine.rag.contracts import EmbeddingProvider, RetrievalHit, RetrievalQuery
from petrus_engine.rag.evidence import EvidenceRepository, ProvenanceLevel, subdivide_span
from petrus_engine.scientific_warnings import failure_codes, structure_codes

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def database(tmp_path):
    database = Database(tmp_path / "test.sqlite3")
    with database.connect() as db:
        for i in (1, 2):
            db.execute(
                "INSERT INTO papers(id,file_hash,file_name,title,doi) VALUES(?,?,?,?,?)",
                (i, str(i), "synthetic.pdf", f"Title {i}", "10.1234/test"),
            )
        db.execute(
            "INSERT INTO sections(id,paper_id,section_type,heading,text,page_start,page_end) VALUES(1,1,'methods','Original heading','Full section text',NULL,NULL)"
        )
        for page, source in ((2, "grobid_coordinates"), (3, "page_text_alignment")):
            db.execute(
                "INSERT INTO source_spans(paper_id,section_id,page,text,source_type) VALUES(1,1,?,?,?)",
                (page, "Controlled source text", source),
            )
        db.execute("INSERT INTO chunks(paper_id,page,text) VALUES(2,4,'Basic pypdf page')")
    return database


def test_units_preserve_identity_and_conservative_policy(database):
    units = list(EvidenceRepository(database).iter_units())
    assert [u.provenance_level for u in units] == list(ProvenanceLevel)
    for unit, page in zip(units[:2], (2, 3)):
        assert unit.paper_id == 1 and unit.section_id == 1
        assert unit.source_span_id is not None
        assert unit.page_start == unit.page_end == page
        assert unit.heading == "Original heading" and unit.section_type == "methods"
        assert unit.doi == "10.1234/test" and unit.title == "Title 1"
        assert unit.supports_paginated_evidence
        assert subdivide_span(unit) == (unit,)
    assert units[2].page_start is units[2].page_end is None
    assert not units[2].supports_paginated_evidence
    assert units[3].page_start == 4 and units[3].provenance_source == "pypdf"
    assert not units[3].supports_paginated_evidence
    assert len(list(EvidenceRepository(database).iter_units(2))) == 1


def test_warning_codes_and_persistence(database):
    assert failure_codes(TimeoutError("human text")) == ["grobid_timeout"]
    assert failure_codes(ValueError("errors.invalidTei")) == ["grobid_invalid_response"]
    assert failure_codes(ValueError("errors.pdfTooLarge")) == ["pdf_size_limit"]
    assert structure_codes(
        {
            "sections": [
                {"page_start": None, "spans": [], "text": "unknown"},
                {"page_start": None, "spans": [1], "text": "partial"},
                {"page_start": 1, "spans": [1], "text": "mapped"},
            ]
        }
    ) == ["page_mapping_missing", "page_mapping_partial"]
    with database.connect() as db:
        assert (
            json.loads(db.execute("SELECT scientific_warning_codes FROM papers LIMIT 1").fetchone()[0]) == []
        )


def test_upgrade_existing_002_preserves_legacy_warning(tmp_path):
    path = tmp_path / "upgrade.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY)")
        for version in ("001_initial.sql", "002_scientific_parsing.sql"):
            db.executescript((ROOT / "src-tauri/migrations" / version).read_text())
            db.execute("INSERT INTO schema_migrations VALUES(?)", (version,))
        db.execute(
            "INSERT INTO papers(file_hash,file_name,title,notes,scientific_warning) VALUES('x','x','x','keep','errors.pdfTooLarge')"
        )
        db.execute("INSERT INTO papers(id,file_hash,file_name,title) VALUES(2,'y','y','y')")
        db.execute("INSERT INTO sections(id,paper_id,text) VALUES(1,2,'partial')")
        db.execute("INSERT INTO sections(id,paper_id,text) VALUES(2,2,'missing')")
        db.execute(
            "INSERT INTO source_spans(paper_id,section_id,page,text,source_type) VALUES(2,1,1,'known','grobid_coordinates')"
        )

    upgraded = Database(path)
    with upgraded.connect() as db:
        row = db.execute("SELECT * FROM papers").fetchone()
        assert row["notes"] == "keep" and row["scientific_warning"] == "errors.pdfTooLarge"
        assert json.loads(row["scientific_warning_codes"]) == ["pdf_size_limit"]
        codes = db.execute("SELECT scientific_warning_codes FROM papers WHERE id=2").fetchone()[0]
        assert set(json.loads(codes)) == {"page_mapping_partial", "page_mapping_missing"}


def test_contracts_with_fake_provider(database):
    class Fake:
        provider_id, model_id, dimension = "fake", "synthetic", 2

        def embed_documents(self, texts):
            return [self.embed_query(text) for text in texts]

        def embed_query(self, text):
            return [float(len(text)), 0.0]

    provider: EmbeddingProvider = Fake()
    assert provider.embed_documents(["abc"]) == [[3.0, 0.0]]
    query = RetrievalQuery("synthetic", limit=2)
    hit = RetrievalHit(next(EvidenceRepository(database).iter_units()), 0.8)
    assert query.limit == 2 and hit.unit.paper_id == 1 and hit.score == 0.8
    with pytest.raises(ValueError):
        RetrievalQuery("")


def fixture_project(tmp_path):
    for name in (
        "scripts/clean.py",
        "scripts/clean.sh",
        "src-tauri/migrations/001_initial.sql",
        "engine/petrus_engine/scientific.py",
        "package.json",
    ):
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    return tmp_path / "scripts/clean.sh"


def test_cleanup_fixture_dry_run_execution_and_guards(tmp_path):
    script = fixture_project(tmp_path)
    artifact = tmp_path / "app/dist/output.js"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("disposable fixture")

    def run(*args):
        return subprocess.run(["bash", str(script), *args], capture_output=True, text=True)

    assert run("--dry-run", "build").returncode == 0
    assert artifact.exists()
    assert run("build").returncode == 0 and artifact.exists()
    assert run("--dry-run", "validation").returncode == 0
    assert run("--execute", "deep").returncode != 0
    protected = tmp_path / "app/dist/paper.pdf"
    protected.write_text("protect even synthetic pdf")
    assert run("--execute", "build").returncode != 0 and artifact.exists()
    protected.unlink()
    assert run("--execute", "build").returncode == 0 and not artifact.exists()
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "app/dist").symlink_to(outside, target_is_directory=True)
    assert run("--execute", "build").returncode != 0 and outside.exists()
