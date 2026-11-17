-- Human-authored statements, separate from source snapshots and append-only history.
CREATE TABLE research_claims (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 session_id INTEGER NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
 statement TEXT NOT NULL CHECK(length(statement) BETWEEN 1 AND 10000 AND length(trim(statement))>0),
 researcher_note TEXT NOT NULL DEFAULT '' CHECK(length(researcher_note)<=100000),
 review_status TEXT NOT NULL DEFAULT 'draft' CHECK(review_status IN ('draft','reviewed')),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 archived_at TEXT
);
CREATE INDEX research_claims_session ON research_claims(session_id,updated_at DESC,id DESC);
CREATE TABLE research_claim_evidence (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 claim_id INTEGER NOT NULL REFERENCES research_claims(id) ON DELETE CASCADE,
 session_id INTEGER NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
 saved_evidence_id INTEGER REFERENCES research_evidence(id) ON DELETE SET NULL,
 relation TEXT NOT NULL CHECK(relation IN ('supports','contradicts','context')),
 evidence_fingerprint TEXT NOT NULL,
 paper_sha256 TEXT NOT NULL,
 text_sha256 TEXT NOT NULL,
 paper_id_snapshot INTEGER,
 paper_title_snapshot TEXT NOT NULL,
 section_heading_snapshot TEXT,
 page_start INTEGER CHECK(page_start IS NULL OR page_start>0),
 page_end INTEGER CHECK(page_end IS NULL OR page_end>=page_start),
 provenance_level TEXT NOT NULL,
 supports_paginated_evidence INTEGER NOT NULL CHECK(supports_paginated_evidence IN (0,1)),
 decision_at_link TEXT NOT NULL CHECK(decision_at_link IN ('included','excluded','uncertain')),
 source_snapshot_event_id INTEGER REFERENCES research_events(id),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(claim_id,evidence_fingerprint)
);
CREATE INDEX research_claim_evidence_source ON research_claim_evidence(saved_evidence_id,claim_id);
CREATE TRIGGER research_claim_link_session_insert BEFORE INSERT ON research_claim_evidence
 WHEN NOT EXISTS(SELECT 1 FROM research_claims c WHERE c.id=NEW.claim_id AND c.session_id=NEW.session_id)
 OR (NEW.saved_evidence_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM research_evidence e
 WHERE e.id=NEW.saved_evidence_id AND e.session_id=NEW.session_id AND e.evidence_fingerprint=NEW.evidence_fingerprint))
 BEGIN SELECT RAISE(ABORT,'claims.crossSessionLink'); END;
CREATE TRIGGER research_claim_link_session_update BEFORE UPDATE ON research_claim_evidence
 WHEN NOT EXISTS(SELECT 1 FROM research_claims c WHERE c.id=NEW.claim_id AND c.session_id=NEW.session_id)
 OR (NEW.saved_evidence_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM research_evidence e
 WHERE e.id=NEW.saved_evidence_id AND e.session_id=NEW.session_id AND e.evidence_fingerprint=NEW.evidence_fingerprint))
 BEGIN SELECT RAISE(ABORT,'claims.crossSessionLink'); END;
-- Owning sessions are not mutable; relation and source-deletion SET NULL remain allowed.
CREATE TRIGGER research_claim_session_immutable BEFORE UPDATE OF session_id ON research_claims
 WHEN NEW.session_id!=OLD.session_id BEGIN SELECT RAISE(ABORT,'claims.immutableSession'); END;
CREATE TRIGGER research_evidence_session_for_claims BEFORE UPDATE OF session_id,evidence_fingerprint ON research_evidence
 WHEN EXISTS(SELECT 1 FROM research_claim_evidence l WHERE l.saved_evidence_id=OLD.id)
 AND (NEW.session_id!=OLD.session_id OR NEW.evidence_fingerprint!=OLD.evidence_fingerprint)
 BEGIN SELECT RAISE(ABORT,'claims.immutableSource'); END;
