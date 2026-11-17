CREATE TABLE IF NOT EXISTS libraries (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, root_path TEXT NOT NULL UNIQUE,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, last_scan_at TEXT
);
CREATE TABLE IF NOT EXISTS papers (
 id INTEGER PRIMARY KEY, file_hash TEXT NOT NULL UNIQUE, file_name TEXT NOT NULL,
 title TEXT NOT NULL, doi TEXT, journal TEXT, publication_year INTEGER, abstract TEXT,
 metadata_status TEXT NOT NULL DEFAULT 'discovered', index_status TEXT NOT NULL DEFAULT 'pending',
 page_count INTEGER, warning TEXT, notes TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS paper_files (
 id INTEGER PRIMARY KEY, paper_id INTEGER REFERENCES papers(id) ON DELETE SET NULL,
 library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
 file_path TEXT NOT NULL, file_name TEXT NOT NULL, file_size INTEGER, file_modified_at INTEGER,
 available INTEGER NOT NULL DEFAULT 1, error TEXT, seen_scan TEXT, UNIQUE(library_id,file_path)
);
CREATE INDEX IF NOT EXISTS paper_files_paper ON paper_files(paper_id);
CREATE TABLE IF NOT EXISTS authors (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, orcid TEXT);
CREATE TABLE IF NOT EXISTS paper_authors (
 paper_id INTEGER REFERENCES papers(id) ON DELETE CASCADE, author_id INTEGER REFERENCES authors(id),
 author_order INTEGER NOT NULL, PRIMARY KEY(paper_id,author_id)
);
CREATE TABLE IF NOT EXISTS collections (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT);
CREATE TABLE IF NOT EXISTS collection_papers (
 collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
 paper_id INTEGER REFERENCES papers(id) ON DELETE CASCADE, PRIMARY KEY(collection_id,paper_id)
);
CREATE TABLE IF NOT EXISTS "references" (
 id INTEGER PRIMARY KEY, source_paper_id INTEGER REFERENCES papers(id) ON DELETE CASCADE,
 target_paper_id INTEGER REFERENCES papers(id), raw_citation TEXT, doi TEXT, title TEXT, resolved INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sections (
 id INTEGER PRIMARY KEY, paper_id INTEGER REFERENCES papers(id) ON DELETE CASCADE,
 section_type TEXT, heading TEXT, page_start INTEGER, page_end INTEGER, text TEXT
);
CREATE TABLE IF NOT EXISTS chunks (
 id INTEGER PRIMARY KEY, paper_id INTEGER REFERENCES papers(id) ON DELETE CASCADE,
 section_id INTEGER REFERENCES sections(id), page INTEGER, chunk_order INTEGER, text TEXT
);
CREATE TABLE IF NOT EXISTS evidence (
 id INTEGER PRIMARY KEY, paper_id INTEGER REFERENCES papers(id) ON DELETE CASCADE,
 section_id INTEGER REFERENCES sections(id), page INTEGER, quote TEXT, context TEXT, evidence_type TEXT
);
CREATE TABLE IF NOT EXISTS edges (
 id INTEGER PRIMARY KEY, source_type TEXT, source_id INTEGER, relation TEXT,
 target_type TEXT, target_id INTEGER, confidence REAL, evidence_id INTEGER REFERENCES evidence(id)
);
CREATE TABLE IF NOT EXISTS research_sessions (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, research_question TEXT NOT NULL DEFAULT '',
 description TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS research_events (
 id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES research_sessions(id) ON DELETE CASCADE,
 event_type TEXT NOT NULL, payload_json TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS jobs (
 id INTEGER PRIMARY KEY, library_id INTEGER REFERENCES libraries(id) ON DELETE CASCADE,
 status TEXT NOT NULL DEFAULT 'queued', stage TEXT NOT NULL DEFAULT 'discovered',
 total INTEGER NOT NULL DEFAULT 0, completed INTEGER NOT NULL DEFAULT 0,
 errors INTEGER NOT NULL DEFAULT 0, message TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 finished_at TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS paper_search USING fts5(title, authors, doi, abstract, body, tokenize='unicode61 remove_diacritics 2');
