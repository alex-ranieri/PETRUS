CREATE TABLE embedding_index (
 id INTEGER PRIMARY KEY,
 unit_id TEXT NOT NULL,
 paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
 provider_id TEXT NOT NULL,
 model_id TEXT NOT NULL,
 dimension INTEGER NOT NULL CHECK(dimension>0),
 content_hash TEXT NOT NULL,
 vector_blob BLOB NOT NULL CHECK(length(vector_blob)=dimension*4),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(unit_id,provider_id,model_id)
);
CREATE INDEX embedding_index_paper ON embedding_index(paper_id);
CREATE INDEX embedding_index_model ON embedding_index(provider_id,model_id,dimension);
