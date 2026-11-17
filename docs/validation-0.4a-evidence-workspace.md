**English** · [Português (Brasil)](pt-BR/validation-0.4a-evidence-workspace.md)

# PETRUS 0.4a — Scientific Evidence Workspace

Date: 16/10/2026. Baseline: validated 0.3.1-dev state.

**Status: implementation, tests, real workflow and native reopening complete. Recommendation: CLOSE_0_4A. Version 0.4.0-dev / Python 0.4.0.dev0 applied only after validation. No final packaging/release.**

## A. Migration

New additive migration `src-tauri/migrations/005_research_evidence.sql`. Ledger increases from four to five migrations; idempotent application/reopening tested. Migration does not rewrite source, embedding or settings tables.

Prior policy links research_events to sessions with ON DELETE CASCADE, without session deletion in UI/API. Workspace retains this policy; evidence removal records an event before hard deletion in the same transaction. No undo/snapshot versioning at this stage.

## B. SavedEvidence schema

Table `research_evidence`, distinct from paper, source_span, retrieval hit, embedding and Ask answer:

- `id` AUTOINCREMENT, required `session_id`/FK, `evidence_fingerprint`.
- Current/optional `paper_id`, `paper_sha256`, `paper_title_snapshot`, nullable `paper_doi_snapshot`.
- Original `evidence_unit_id`, `source_span_id`, `section_id`, `section_heading_snapshot`, `evidence_role`, `provenance_level`.
- `page_start`, `page_end`, `supports_paginated_evidence`.
- `text_snapshot`, `text_sha256`, `source_identity_json`.
- `decision`, `user_note`.
- `origin_type`, optional `research_event_id`, `question_snapshot`, `evidence_label_snapshot`.
- `created_at`, `updated_at` UTC.

Session FK uses CASCADE; paper/span/section/research_event use SET NULL. Current FKs may disappear without deleting the snapshot. Missing DOI/pages/heading remain NULL, not inferred. Origin, source excerpt and human content are separate fields.

## C. Fingerprint and deduplication

SHA-256 of canonical JSON containing paper/text SHA, pages, provenance and semantic source/section identity (heading, type, origin, subdivision offsets). Not dependent solely on `span:123` or numeric section IDs. `UNIQUE(session_id,evidence_fingerprint)` guarantees idempotence. Duplicate returns the existing item without resetting decision, note or origin and without another saved event. The same source may belong to different sessions.

## D. Snapshot and verification

`ResearchEvidenceService` reserves an IMMEDIATE transaction, checks the session and reconstructs the current unit through the existing projector, without changing retrieval. Checks paper, text, pages, provenance, role and pagination capability when supplied. Arbitrary frontend text is rejected or ignored in favor of verified reconstruction; the engine produces snapshots. Snapshot fields are not editable through update.

Ask handler adds only an opaque `response_id` receipt after unchanged execution. A volatile register of the last 16 answers stores question, Evidence Cards and final status, without generated answer or reasoning. Save checks unit/label membership in that answer and then compares with the current source. A persisted Ask event may also establish origin after membership verification. Receipts expire on restart; only unsaved cards require another question. Already saved items remain readable without a receipt.

`ask_answer` identifies a source from an accepted answer; `retrieved_source` identifies a retrieved source in other cases. Origin is engine-derived, not frontend-decided. Deduplication retains the first origin context; no full trail of every retrieval. `research_event_id` stays NULL when the user has not saved a corresponding Ask event. E# labels are question-local; unit IDs are not permanent global identifiers either.

## E–F. Human decision and note

Required default `uncertain`, including sources cited by an accepted answer. Allowed values: included/excluded/uncertain. Save endpoint does not apply caller-suggested decisions/notes; explicit updates serve human actions. UI changes decisions only after selection and saves notes only through Save note. No LLM-generated, prefilled or rewritten notes.

Notes preserve the exact received string, including whitespace, newlines and Unicode; explicit 100000-character limit. Unchanged updates create no event and do not change updated_at. Excerpt and note have distinct visual presentations.

## G. Ask → Save evidence

Each Evidence Card has Save evidence/Salvar evidência and Saved/Salva state in the target session. A small selector chooses an existing session or creates another. Human validation identified ambiguity in the selector's generic Save button. Destination selection now uses Choose target session and Use session, without saving a card or answer. Save accepted answer to session is available only for an accepted answer and explicit destination, reusing save_ask_event; it does not automatically save workspace evidence. Two EN/PT-BR tests cover this distinction. No session is selected by recency; the explicit target stays only in Ask UI state, reusing an already-open session when applicable. No new global setting or automatic card/paper/answer saving.

Existing citation highlighting/navigation remain. After human checking, a shortcut next to the rejected-generation message was added to scroll to retrieved sources and their explicit save actions. Tests also check saving a retrieved source when its answer was rejected. Generation failure remains distinct from validated scientific abstention and does not turn a retrieved source into an accepted answer.

## H. Research workspace

Session details show total/included/excluded/uncertain counts, filters and a newest-save-first list. Each item displays title, heading, known page, provenance, origin, excerpt, question/label when available, decision and human note. Supports decision changes, saving notes, removal and source opening. No automatic synthesis, claims/findings, advanced search or complete Research Trail.

## I. Events

`evidence_saved`, `evidence_decision_changed`, `evidence_note_updated` and `evidence_removed` reuse research_events. Payload contains IDs, timestamp, fingerprint, paper ID and previous/new decisions when needed. Does not duplicate text_snapshot, note text, answer or reasoning. Removing evidence retains its session event; eventual session deletion removes its events through CASCADE under the existing schema.

## J–K. Persistence and navigation

Python tests check engine reopening, FKs, source deletion/reprocessing and snapshot immutability. The existing real-engine desktop test was preserved and extended: saves synthetic evidence, sets fixture decision/note, restarts the process and checks identical text/hash/fingerprint/decision/note through API and UI.

View paper, View in library and Open PDF use the current paper when available. Missing paper/null FK or recorded unavailability leave the snapshot visible and show Source currently unavailable. Availability follows catalog/last scan; no new scan or changed-source detector. Reprocessing never silently rewrites a snapshot.

A second independent copy (`contract-smoke`) exercised actual JSON-lines with a corpus unit (`span:2042`): reconstructed/verified save, exact snapshot/text hash, idempotent duplicate save and identical get after Python shutdown/restart. Fixture item remained retrieved_source/uncertain with an empty note. All source/vector/settings tuples stayed identical. No Ask/model call occurred and the probe inserted nothing in the native human workspace. Evidence: `real-contract-smoke.json`. This validates engine/transport/real data without replacing native human GUI checking.

Real native reopening confirmed: Tauri watcher stopped/restarted app/engine on the same isolated database; SHA-256 of complete research_evidence rows stayed identical before/after. User confirmed “Tudo funciona após reabrir; E2 está Uncertain” (“Everything works after reopening; E2 is Uncertain”), covering both items, note, Included filter and paper/PDF. Initially both were Included; those choices survived the first restart. The user later changed E2 to Uncertain. Subsequent 0.4.0-dev bump triggered another restart, again with complete rows identical to pre-bump captures.

## L. Python

**242 passed (12.03 s)**, including **30 new workspace tests**. Coverage: migration, coordinate/exact_page_alignment/section_only/basic_page_text, NULLs, text/hash, fingerprint and numeric ID replacement, per-session deduplication, exact decisions/notes, filters, events/no-op, removal/FKs, unavailable/deleted/reprocessed sources, forged fields, origin receipts and Ask events, membership, reasoning absence and snapshot protection. Old migration test updated to expect five migrations.

Ruff passed for engine, tests and scripts. No actual model calls in these tests.

## M. Frontend and builds

**17 Playwright tests passed (27.8 s)**: 6 new EN/PT-BR workspace tests, 6 model discovery, 2 Ask with mocked IPC, 1 desktop with real Python engine and 2 i18n/scientific-content tests. New tests cover session selection/creation, no auto-save, Saved/deduplication, snapshot, filters, three decisions, exact/manual notes, reload, retrieved_source origin, NULL page, unavailable source, PDF/library and removal.

Fixture screenshots inspected for complete card and visual source/human-note separation. ESLint/TypeScript and `npm run build` passed. Tauri dev compiled/opened the isolated copy, including 0.4.0-dev after validated bump. No final package/release created. Original logo preserved. Existing tests may update fixture screenshots.

## N. Isolated real validation

Database: `.local-data/evidence-workspace-0.4a/native-smoke/petrus.sqlite3`, SQLite backup of the known separate `.local-data/arbovirus-retrieval-validation-0.3b/petrus.sqlite3` database. Uses the 9B configuration already present, without changing settings. The 0.3.1 database with later 4B selection and main library were not used/changed.

User-created session: **Arbovirus evidence workspace test**.

User reported Q3 (“What evidence of arbovirus adaptation is present in these papers?”) returned **Generation failed / response rejected**. A later image also showed Q1 rejected with `missing_citations`. The image showed generation state, not cards below; it did not demonstrate save failure. The source-navigation shortcut was added to make this flow apparent, with 6 focused tests passing afterward. Failures were recorded; generation, validator, repair and models were not changed to force acceptance. The designed workflow permits explicit saving of a retrieved Q3 source as retrieved_source/uncertain. Final read and human confirmation validated two items: E6 from Q1 as retrieved_source/included, with a nonempty human note; E2 from repeated Q3 as ask_answer/uncertain. Repetition belonged to the requested workflow, not a benchmark/model comparison. Original Q3 failure and Q1 rejection remain recorded; no validator was relaxed to force acceptance. Filters and paper/PDF opening confirmed after reopening.

Validation is limited to persistence, provenance and workflow; not a benchmark or extensive scientific evaluation.

## O. Preservation

Final verification confirmed complete before/after tuple equality (including blobs) in papers (10), sections (180), source_spans (2255), embedding_index (2342) and settings (17). Hashes of all existing rag, llm and graph modules also identical. No PDF reprocessed, embedding reindexed or AI setting changed.

Migration naturally changes schema/database digest. Only new workspace tables/items and research_sessions/events receive this stage's actions. Documented Qwen 9B, Nomic 768, temperature 0.1, context 8192, 1600-token and 90 s baseline preserved. Model discovery, QueryPlan, RRF, boost/selection, validator, bounded repair, reasoning policy, graph and prompts preserved.

## P. Files

- New migration: `src-tauri/migrations/005_research_evidence.sql`.
- New domain: `engine/petrus_engine/research.py`; dispatch/receipts in `engine/petrus_engine/service.py`; allowlist in `src-tauri/src/main.rs`.
- UI: new `SaveEvidenceDialog.tsx` and `ResearchEvidenceWorkspace.tsx`; integration in `Ask.tsx`, `App.tsx`, types in `services/api.ts`, styles in `styles/app.css`, EN/PT-BR translations.
- Tests: new `engine/tests/test_research_evidence.py`, new `tests/research-evidence.spec.mjs`, extended real test in `tests/desktop-ui.spec.mjs`, migration expectation in `engine/tests/test_engine.py`.
- Docs: README (preflight corrected the obsolete AI-disabled limitation), architecture, database, roadmap and this report. Version/planning history preserved and identified.
- Versions after validation: package.json/package-lock.json, src-tauri/tauri.conf.json, Cargo.toml/Cargo.lock (petrus package), engine/pyproject.toml and petrus_engine/__init__.py, EN/PT-BR sidebar label updated to 0.4.0-dev / Python 0.4.0.dev0. Editable-install metadata aligned without dependency downloads.

## Q–R. Evidence and recommendation

Report: `docs/validation-0.4a-evidence-workspace.md`.

Local evidence in `.local-data/evidence-workspace-0.4a/`: `core-before.json`, `data-before.json`, `copy-source.txt`, `preservation-latest.json`, `check_preservation.py`, Python/lint/Ruff/build/dev logs, `ui/*tests*.log`, `real-contract-smoke.json`, `before-reopen.json`, `after-reopen.json`, `before-version.json`, `after-version.json`, `manual-confirmation.json` and `final-summary.json`. Workspace records no reasoning content.

**CLOSE_0_4A.** Development-workspace Definition of Done met. App 0.4.0-dev remains open with the isolated copy; no final package/release, automatic synthesis or start of 0.4b. Workflow validation neither turns a rejected answer into an accepted scientific answer nor proves source entailment.
