import json
from pathlib import Path

import pytest
from petrus_engine.database import Database
from petrus_engine.graph import build_graph
from petrus_engine.graph.relatedness import RelatednessService, candidates, reference_key, terms


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "related.sqlite3")
    with database.connect() as db:
        db.execute("INSERT INTO libraries(id,name,root_path) VALUES(1,'synthetic','/synthetic')")
        for i, title in enumerate(
            [
                "Genomic surveillance dengue outbreaks northern Brazil",
                "Dengue genomic surveillance outbreaks in northern Brazil",
                "Stellar spectroscopy distant galaxies formation",
                "Estudo análise resultados métodos artigo vírus",
            ],
            1,
        ):
            db.execute(
                "INSERT INTO papers(id,file_hash,file_name,title,abstract) VALUES(?,?,?,?,?)",
                (i, str(i), str(i), title, ""),
            )
            db.execute(
                "INSERT INTO paper_files(paper_id,library_id,file_path,file_name) VALUES(?,1,?,?)",
                (i, str(i), str(i)),
            )
        yield db


def test_similar_titles_reasons_and_unrelated_rejection(db):
    edges = RelatednessService(db).relations([1, 2, 3, 4])
    title = [e for e in edges if e["relation_type"] == "TITLE_SIMILARITY"]
    assert len(title) == 1
    assert (title[0]["source_paper_id"], title[0]["target_paper_id"]) == (1, 2)
    assert title[0]["score"] == 1.0
    assert "dengue" in title[0]["metadata"]["shared_terms"]
    assert not any(3 in (e["source_paper_id"], e["target_paper_id"]) for e in edges)


def test_stopwords_and_unicode():
    assert terms("Study analysis results virus paper method estudo análise resultados vírus métodos") == set()
    assert terms("GENÔMICA,   Dengue! surveillance") == {"genomica", "dengue", "surveillance"}


def test_keywords_are_derived_deterministic_and_no_duplicate_pairs(db):
    db.execute(
        "UPDATE papers SET abstract='recombination chikungunya ECSA mosquito adaptation' WHERE id IN (1,2)"
    )
    service = RelatednessService(db)
    edges = service.relations([4, 2, 1, 3, 1])
    assert edges == service.relations([1, 2, 3, 4])
    keyword = next(e for e in edges if e["relation_type"] == "SHARED_KEYWORDS")
    assert keyword["metadata"]["term_source"] == "derived_term"
    assert keyword["metadata"]["count"] >= 3
    assert len({(e["source_paper_id"], e["target_paper_id"], e["relation_type"]) for e in edges}) == len(
        edges
    )
    assert candidates({1: {"a", "b"}, 2: {"a", "b"}}) == [(1, 2)]


def add_ref(db, paper, doi=None, title=None):
    db.execute('INSERT INTO "references"(source_paper_id,doi,title) VALUES(?,?,?)', (paper, doi, title))


def test_shared_unresolved_doi_references_deduplicated_and_normalized(db):
    for paper in (1, 3):
        add_ref(db, paper, "https://doi.org/10.1234/ONE")
        add_ref(db, paper, "10.1234/two")
        add_ref(db, paper, "10.1234/two")
    edge = next(
        e for e in RelatednessService(db).relations([1, 2, 3, 4]) if e["relation_type"] == "SHARED_REFERENCES"
    )
    assert edge["metadata"]["shared_reference_count"] == 2 and edge["score"] == 1
    assert len(edge["metadata"]["examples"]) == 2
    assert db.execute("SELECT count(*) FROM edges").fetchone()[0] == 0


def test_reference_titles_conservative_no_raw_or_doi_conflict_match(db):
    title = "A conservative unique reference about genomic surveillance"
    for paper in (1, 3):
        add_ref(db, paper, title=title.upper() if paper == 1 else title + ".")
        add_ref(db, paper, title="Another long reference concerning mosquito population genetics")
    assert any(e["relation_type"] == "SHARED_REFERENCES" for e in RelatednessService(db).relations([1, 3]))
    assert reference_key(None, "Short title") is None
    assert reference_key("10.1234/a", title) != reference_key("10.1234/b", title)
    db.execute('DELETE FROM "references"')
    add_ref(db, 1, "10.1234/a", title)
    add_ref(db, 3, "10.1234/b", title)
    assert not any(
        e["relation_type"] == "SHARED_REFERENCES" for e in RelatednessService(db).relations([1, 3])
    )


def test_only_one_shared_reference_is_not_sufficient(db):
    for paper in (1, 3):
        add_ref(db, paper, "10.1234/one")
    assert not any(
        e["relation_type"] == "SHARED_REFERENCES" for e in RelatednessService(db).relations([1, 3])
    )


def test_graph_integration_bounded_and_no_semantic_edges(db):
    graph = build_graph(db)
    assert any(e["type"] == "TITLE_SIMILARITY" and e["metadata"] for e in graph["edges"])
    assert not any(e["type"] == "SEMANTIC_SIMILARITY" for e in graph["edges"])
    service = RelatednessService(db)
    service.MAX_PER_TYPE = 1
    assert len([e for e in service.relations([1, 2, 3, 4]) if e["relation_type"] == "TITLE_SIMILARITY"]) <= 1


def test_i18n_labels_and_explanation():
    root = Path(__file__).resolve().parents[2]
    for locale in ("en", "pt-BR"):
        catalog = json.loads((root / f"app/src/i18n/locales/{locale}.json").read_text())
        for name in (
            "TITLE_SIMILARITY",
            "SHARED_KEYWORDS",
            "SHARED_REFERENCES",
            "relatednessDisclaimer",
            "derivedTerms",
        ):
            assert catalog["graph." + name]
