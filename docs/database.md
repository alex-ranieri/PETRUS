**English** · [Português (Brasil)](pt-BR/database.md)

# Local data model

The authoritative schema is in migrations `001_initial.sql` through `007_research_claims.sql`, in `src-tauri/migrations/`. The initial migration was not changed. The applied version is recorded in `schema_migrations`. Each migration runs once inside a transaction.

| Table | Role in this version |
|---|---|
| libraries | Registered folders and last scan |
| papers | SHA-256 content identity, metadata, statuses and notes |
| paper_files | Physical locations, library, size, mtime, availability and errors |
| authors / paper_authors | Extracted authors and PDF-provided order |
| collections / collection_papers | Manual organization, N:N relationship |
| chunks | Extracted text per page, numbered from 1 |
| paper_search | FTS5 with rowid corresponding to papers.id |
| jobs | Persisted queue, scan progress and results |
| settings | Service-typed preferences, JSON values |
| research_sessions / research_events | Sessions and canonical chronological history of questions/retrieval/results and human actions |
| research_evidence | Per-session saved evidence snapshots, human decision, note and origin |
| embedding_index | Local vectors, provider/model/dimension identity and content hash |
| references | Ordered references, DOI, resolution state/confidence and local target |
| sections | TEI hierarchy, original heading, category, order, text and optional pages |
| evidence | Structure for passages with context and page |
| edges | Typed CITES citations with reference_id; other relationships are preserved |
| source_spans | Page, excerpt, optional offsets, coordinates and mapping origin |
| parser_runs | Scientific parsing attempts, TEI and warnings |
| paper_basic_metadata | Basic metadata snapshot, separate from scientific metadata |

`paper_files` normalizes location-dependent fields: a paper need not belong to only one library. Constraint `(library_id, file_path)` prevents duplicate locations within one registration; `papers.file_hash` prevents duplicate content. Overlapping library paths may create multiple links to the same location without duplicating indexed text.

A file unavailable before hashing has `paper_id=NULL`. A removed file retains its location record with `available=0`. An existing PDF that cannot be parsed may have `metadata_status=failed` and still open in the default application. A PDF without text may have `warning` status and need OCR.

Content is considered visible while at least one registered location exists; when all are unavailable, the displayed status is `unavailable`. Old papers without locations are retained for reuse but excluded from the catalog and graph. Removing a library neither deletes physical documents nor guarantees purging indexed text.

FTS updates in the same transaction as metadata and pages. The fallback title is searchable before parsing finishes. File paths and system preferences are not indexed in FTS.

To copy a database while the app is running, use SQLite's backup API; copying only `.sqlite3` can omit transactions in WAL. Do not manually change applied migrations; add a new migration.

## 0.2 update

`papers.scientific_status` is independent of metadata_status/index_status and availability: basic, structured, structured_warning or failed. `scientific_warning` and scientific_updated_at record the scientific result. A job can finish with partially unmapped sections; inspect the paper's scientific status too.

`references` retains historical fields and adds citation_order, authors_text, journal, year, resolution_status, resolution_confidence, tei_id and timestamps. The historical resolved boolean stays synchronized. Candidate may hold a possible target but does not generate CITES or count as resolved in the UI. Ambiguous resolutions do not arbitrarily choose a PDF version.

`sections.parent_section_id` preserves the tree. Chunks are not deleted during scientific reprocessing. Coordinate-based source spans have null character offsets; alignment spans store offsets in the original page text, with exclusive char_end. The stored passage is the TEI region text for coordinates or the original pypdf substring for alignment. It is not a translation.

Scientific replacement removes/reinserts only the paper's derived data inside a transaction, clears obsolete links and resolves local references. Attempt history remains in parser_runs. Repeating the operation does not duplicate references/sections. Jobs use job_type scan/integrity/scientific and optional paper_id, with translatable message keys.

`verify_integrity` recalculates hashes; normal rescan uses size/mtime. Settings adds language, scientific_parser, grobid_endpoint and grobid_fallback without rewriting existing preferences.

## SavedEvidence — 0.4a

Additive migration `005_research_evidence.sql` creates `research_evidence`. It does not change source, vector or settings table contents.

| Group | Fields |
|---|---|
| Identity | id AUTOINCREMENT; session_id NOT NULL/FK; UNIQUE(session_id, evidence_fingerprint) |
| Paper | optional paper_id/FK; paper_sha256; paper_title_snapshot; nullable paper_doi_snapshot |
| Unit/source | original evidence_unit_id; optional source_span_id/section_id; section_heading_snapshot; evidence_role; provenance_level; source_identity_json |
| Pagination | nullable page_start/page_end; supports_paginated_evidence boolean |
| Immutable excerpt | exact text_snapshot; UTF-8 text_sha256 |
| Human work | decision CHECK included/excluded/uncertain, default uncertain; user_note default empty |
| Origin | origin_type CHECK ask_answer/retrieved_source; optional research_event_id; optional question_snapshot/evidence_label_snapshot |
| Time | created_at/updated_at UTC |

Fingerprint: SHA-256 of canonical JSON (sorted keys, stable separators, preserved Unicode) containing paper/text SHA, pages, provenance and semantic section/source/subdivision-offset identity. Changing numeric IDs while preserving the source does not duplicate an item in the same session. A duplicate save returns the first snapshot/origin/decision/note unchanged; this stage does not accumulate history for every retrieval. Each session has its own selection.

Session FK uses ON DELETE CASCADE, following the prior research_events policy. Paper, source_span, section and research_event use ON DELETE SET NULL: deleting/replacing a source does not delete the snapshot. Current FKs may become null; evidence_unit_id and snapshots keep the original identity interpretable. Missing DOI, heading and pages are not invented.

Original 0.4a contract (event history is extended by 006 below): only decision/note are editable. updated_at changes only for a real change; notes preserve whitespace, Unicode and line breaks. Actions emit `evidence_saved`, `evidence_decision_changed`, `evidence_note_updated` and `evidence_removed`. Payload contains IDs/fingerprint/timestamp and previous/new decisions when applicable; it contains no excerpts or note text. Removal records an event before hard deletion in the same transaction, without undo/snapshot versioning. Session events remain after evidence removal; deleting the session also removes them by CASCADE.

The service returns `source_available`, derived from the current FK and availability recorded in paper_files. This stage has no unit remapping or stale-source detector: saved text is always the save-time snapshot. `E6` identifies a source only inside the recorded question; it is not global. EvidenceUnit IDs may also change after reprocessing.

## Research Trail — migration 006 / payload v1

Migration 006 adds these fields to existing `research_events`: `actor_type NOT NULL CHECK user/ai/system`, `object_type`, `object_id TEXT`, `payload_version NOT NULL CHECK=1` and `legacy NOT NULL CHECK 0/1`. The five historical fields (id, session_id, event_type, created_at, payload_json) remain intact. Known actors/objects are classified deterministically. Preexisting sessions receive one `trail_tracking_started` boundary; a unique partial index prevents duplication. New sessions start at session_created, without a retroactive boundary.

| v1 event | Actor | Durable contents |
|---|---|---|
| session_created | user | Title and session object |
| question_asked | user | Exact question, language and SHA-256 |
| retrieval_completed | system | Question ID; QueryPlan; config; returned counts; identities/hashes/ranks of selected sources; observed sources; audit-context hash |
| ask_accepted | ai | Question/retrieval IDs; final validated answer + SHA; local citations; provider/model/config; attempts/repair |
| ask_abstained | ai, or system without sources | Canonical insufficiency text and summary/status; no invented generation |
| ask_rejected / ask_generation_failed | system | Allowed codes, status and summary; no raw candidate/error |
| ask (DTO ask_saved_to_session) | user | Explicit save: reference to the result in the same session when available; otherwise final snapshot validated by the previous contract |
| evidence_saved | user | Identity/fingerprint/metadata/origin and durable snapshot of the explicitly saved source |
| evidence_decision_changed | user | Identity; old_decision/new_decision (previous/new preserved) |
| evidence_note_updated | user | Identity; old_note_sha256/new_note_sha256; exact new_note_snapshot |
| evidence_removed | user | Identity/title/paper SHA/section/pages/decision; reference to historical save or legacy snapshot captured now |
| trail_tracking_started | system | stage=0.4b and prior_activity_may_be_incomplete |

`payload_version=1` is an explicit column, without a payload replay/migration framework. Canonical UTF-8 JSON, sorted keys, SHA-256 hash of persisted payload. `E#` is question-local; EvidenceUnit may change after reprocessing. Source/excerpt/fingerprint remain independent in `research_evidence`, whose migration 005 was unchanged. Duplicating a human note version and an explicitly saved source in history is deliberate for auditing; retrieval never duplicates all excerpts.

Limits: question 2,000 characters, note 100,000 characters, answer snapshot 2,000,000 UTF-8 bytes, JSON payload 2,500,000 bytes. Exceeding a limit produces an explicit error/warning, without silent truncation. An INSERT trigger enforces the payload limit; UPDATE is forbidden. Individual DELETE is forbidden while the session exists; only the historical CASCADE when the session itself is deleted remains. Triggers do not protect against an administrator deliberately modifying the schema.

`research_trail_list`: required session_id, actor_type all/user/ai/system, limit 1–100 (default 50), after_event_id from the same session. Cursor uses timestamp+id and the same chronological order, without unstable OFFSET. The compact projection has no answer/note/excerpt. `research_trail_get(session_id,event_id)` loads details on demand. DTO includes actors/object/UTC/version/legacy/hash/metadata and links with current availability. Legacy payloads pass through a whitelist and are never forwarded in full. Incompleteness warning is independent of actor filtering.

Evidence mutation and event are atomic. Ask records the question before execution; retrieval and result are recorded after their state is known, in a joint transaction. Generation never runs inside a SQLite transaction. Reopening does not recreate events. The [0.4b report](validation-0.4b-research-trail.md) documents real comparison by IDs/timestamps/hashes and preservation of both 0.4a snapshots.

## Human claims — migration 007

| Table | Contract |
|---|---|
| research_claims | id AUTOINCREMENT; session_id/FK CASCADE; statement NOT NULL up to 10,000 characters; researcher_note up to 100.000; review_status draft/reviewed (default draft); created_at/updated_at UTC; nullable archived_at |
| research_claim_evidence | id AUTOINCREMENT; claim_id/session_id FKs CASCADE; saved_evidence_id FK SET NULL; relation supports/contradicts/context; UNIQUE(claim_id,evidence_fingerprint); paper/text SHA, fingerprint, paper_id_snapshot/title/section/pages/provenance/pagination; decision_at_link; source_snapshot_event_id/FK; created_at/updated_at UTC |

Additive migration, without modifying 005/006 or their rows. Triggers ensure consistency among claim, session and current source, including updates. A claim's owning session is immutable; linked SavedEvidence identity/session cannot be changed directly either. The API does not accept session_id in link/update as a substitute for the actual owner; it reads ownership from the database. Linking a source does not change its previous Included/Excluded/Uncertain state.

A removed source leaves saved_evidence_id NULL, but the link retains metadata/fingerprint and its historical snapshot reference. paper_id_snapshot is a historical identity without FK: current availability derives from live SavedEvidence and paper_files, not that old key. `decision_at_link` is historical and displayed as such only after source removal; otherwise the UI separately projects the current decision. Relationships and statuses are not recalculated by embeddings.

The snapshot reference points to the already-durable evidence_saved/remove, or to the first claim_evidence_linked that preserves still-available legacy text. Text is not in the link table. The original event remains append-only. Manually removing a link creates an event and DELETEs the current link; removing SavedEvidence retains the link row. Claims have only Archive/Restore in the API, without hard deletion. Session CASCADE retains the previous policy.

`research_claim_list(session_id,filter=all,limit=50,after_id?)` orders by updated_at DESC,id DESC. Limit 1–100. All/Draft/Reviewed count only active claims; Archived counts archived ones. Returns full statements and descriptive counts, without notes/excerpts; get(id) provides details and up to 100 links. Historical snapshot loads on demand through Trail. `research_claim_update` accepts only statement, researcher_note and review_status. Limits are explicit, without truncation. NUL text is rejected to keep SQLite/Python lengths consistent.

The nine new events' v1 payload uses actor_type=user/object_type=research_claim and claim_id. Created stores statement_snapshot/researcher_note_snapshot and hashes; statement_updated stores the exact new version and old/new hashes; note_updated stores exact new_note_snapshot and hashes; status/relationship store old/new. Link/unlink store identity, relationship and snapshot reference sufficient to interpret the past. Existing writer, 2.5 MB limit and append-only triggers are reused. Mutations and events are atomic; no read or opening produces retroactive events.
