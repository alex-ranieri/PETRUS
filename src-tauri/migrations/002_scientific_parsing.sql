ALTER TABLE papers ADD COLUMN scientific_status TEXT NOT NULL DEFAULT 'basic';
ALTER TABLE papers ADD COLUMN scientific_warning TEXT;
ALTER TABLE papers ADD COLUMN scientific_updated_at TEXT;
ALTER TABLE jobs ADD COLUMN job_type TEXT NOT NULL DEFAULT 'scan';
ALTER TABLE jobs ADD COLUMN paper_id INTEGER REFERENCES papers(id);
ALTER TABLE jobs ADD COLUMN message_key TEXT;
ALTER TABLE jobs ADD COLUMN message_params TEXT;
ALTER TABLE sections ADD COLUMN parent_section_id INTEGER REFERENCES sections(id) ON DELETE CASCADE;
ALTER TABLE sections ADD COLUMN section_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE sections ADD COLUMN tei_id TEXT;
ALTER TABLE "references" ADD COLUMN citation_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE "references" ADD COLUMN authors_text TEXT;
ALTER TABLE "references" ADD COLUMN journal TEXT;
ALTER TABLE "references" ADD COLUMN year INTEGER;
ALTER TABLE "references" ADD COLUMN resolution_status TEXT NOT NULL DEFAULT 'unresolved';
ALTER TABLE "references" ADD COLUMN resolution_confidence REAL;
ALTER TABLE "references" ADD COLUMN tei_id TEXT;
ALTER TABLE "references" ADD COLUMN created_at TEXT;
ALTER TABLE "references" ADD COLUMN updated_at TEXT;
ALTER TABLE edges ADD COLUMN reference_id INTEGER REFERENCES "references"(id) ON DELETE CASCADE;
CREATE TABLE source_spans (
 id INTEGER PRIMARY KEY, paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
 section_id INTEGER REFERENCES sections(id) ON DELETE CASCADE,
 reference_id INTEGER REFERENCES "references"(id) ON DELETE CASCADE,
 page INTEGER NOT NULL CHECK(page>0), char_start INTEGER, char_end INTEGER,
 text TEXT NOT NULL, source_type TEXT NOT NULL, coordinates_json TEXT
);
CREATE TABLE parser_runs (
 id INTEGER PRIMARY KEY, paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
 parser TEXT NOT NULL, status TEXT NOT NULL, tei_xml TEXT, warnings_json TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE paper_basic_metadata (
 paper_id INTEGER PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
 metadata_json TEXT NOT NULL
);
INSERT INTO paper_basic_metadata(paper_id,metadata_json)
 SELECT id,json_object('title',title,'doi',doi,'journal',journal,'publication_year',publication_year,'abstract',abstract)
 FROM papers;
CREATE INDEX sections_paper_order ON sections(paper_id,section_order);
CREATE INDEX references_source_order ON "references"(source_paper_id,citation_order);
CREATE INDEX references_doi ON "references"(doi);
CREATE INDEX references_target ON "references"(target_paper_id,resolution_status);
CREATE INDEX spans_section_page ON source_spans(section_id,page);
CREATE INDEX spans_reference_page ON source_spans(reference_id,page);
CREATE UNIQUE INDEX citation_reference ON edges(reference_id) WHERE relation='CITES';
CREATE INDEX parser_runs_paper ON parser_runs(paper_id,created_at);
