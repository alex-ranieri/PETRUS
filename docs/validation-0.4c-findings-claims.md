**English** · [Português (Brasil)](pt-BR/validation-0.4c-findings-claims.md)

# PETRUS 0.4c — Scientific Findings & Claims

19/10/2026. Validated baseline: 0.4.1-dev. Implementation in progress; no premature version bump.

## Preflight

Read the 0.4a/0.4b reports, README, architecture, database and roadmap. Inspected the actual 005/006 schema and services/API/UI. `research_evidence` represents independent current snapshots, with per-session/fingerprint deduplication, human decisions and notes. `research_events` is the canonical v1 log, protected by append-only triggers, with a maximum 2.5 MB payload and a unique legacy boundary. Session CASCADE is preserved; there is no session deletion in the UI. New events will use the same writer/transaction and user actor, without a second history or Finding entity.

New migration 007 will create only research_claims and research_claim_evidence. A claim will be a human statement; Findings will be the third tab. Links will have immutable fingerprint/metadata and a reference to an existing durable snapshot; for legacy sources without a durable snapshot, the first explicit link will preserve a copy in the new link event. Removing SavedEvidence will use SET NULL to retain the link/history.

New SQLite copy: `.local-data/findings-claims-0.4c/native-smoke`, created by backing up the validated 0.4b database in read-only mode. The preceding baseline includes all paper/section/span/vector tuples with BLOBs/settings/evidence/events, plus hashes of all rag/llm/graph modules and historical migrations. No old development instance was active. The original 0.4b database will not be opened by the new engine; no LLM, reindexing or PDF processing is part of the domain test.

## Implementation A–N

| Item | Result |
|---|---|
| A — Preflight | Actual schema and 0.4a/0.4b contracts inspected; obsolete descriptions of an absent Trail corrected in README. |
| B — Migration | Additive 007_research_claims.sql; no old migration modified. |
| C — Schema | research_claims + research_claim_evidence; FKs, session/date index, per-claim/fingerprint uniqueness and isolation triggers. |
| D — ResearchClaim | Exact human text and note, draft/reviewed, UTC timestamps and archived_at; no extra Finding entity. |
| E — Links | Manual N:N, only SavedEvidence from the same session; repeating a link does not silently change its relationship. |
| F — Fingerprint/provenance | Stable identity, paper/text SHA, title/section/pages/provenance/pagination; durable snapshot reused or preserved in a new explicit legacy link. |
| G — Relationships | supports/contradicts/context are human classifications, without LLM/embedding/entailment scores. |
| H — Status | Initial Draft; Reviewed requires a link and is a human action; source decision/relationship/review are independent. |
| I — Revisions | Initial version and new exact statement/note versions and hashes; no trimming, translation, generation or typing history. |
| J — Trail | Nine new user/v1 events, same append-only writer; atomic mutations/events, no events on reads/no-ops. |
| K — Archive/restore | No claim hard-delete in the API; archived claims outside the active list, readable through filter/Trail, explicit restore. |
| L — Findings UI | Third tab without session redesign, explicit forms, session selector, EN/PT-BR filters/counts and ordering by modification. |
| M — Navigation | Claim → SavedEvidence/paper/PDF; SavedEvidence → claims; Trail → claim, including archived claims. |
| N — Removed sources | SET NULL preserves link, identity, metadata and historical snapshot; Reviewed retained with a warning; no text reconstruction. |

## O–P — Tests

Domain tests do not call an LLM. New coverage includes defaults, exact Unicode text/notes and whitespace/newlines, empty/invalid fields/limits, isolation/FKs/constraints/uniqueness, independent relationships/statuses, no-ops, archive/restore, pagination, legacy/reused snapshots, unavailable/removed/reprocessed sources, reverse navigation, append-only behavior and reopening. Eight scenarios force event failure to prove rollback of create/update/link/relation/unlink/review/archive/restore.

The 31 new engine tests passed. The final full suite had **309 passing** (278 previous + 31 new), recorded in `full-engine-tests.log`. Ruff/ESLint/TypeScript and the Vite build passed. Tauri dev compiled and opened with the new isolated copy, still at 0.4.1-dev.

Playwright: **25 passed**, retaining the previous 23 and adding two complete EN/PT-BR workflows. The existing desktop test with the real Python engine and synthetic PDFs was extended: it creates a fixture claim through the UI, links a source, marks Reviewed, restarts the process and compares the full claim/links/trail, also checking the reopened UI. The two mocked tests cover create/edit/note/relationships/unlink/review/Draft/archive/restore/navigation/PDF/unavailability/removal/filters/Trail/reload. EN/PT screenshots inspected; historical source text and human notes remain visually separate.

Editing exposed a problem with accessible textarea names when populated. Explicit aria-labels were added and the suite passed. No old test was removed; only the ledger expectation changed from six to seven migrations.

## Q — Real validation / reopening: pending

The isolated 0.4c copy opened natively with migration 007. At this checkpoint, no claim had been created in the real corpus. The user was asked for an initial statement, revised version and note, explicitly as a preliminary test hypothesis, to preserve literal human authorship. Automated synthetic fixtures are not presented as the user's scientific statements. The real workflow and post-restart comparison are prepared in validate_real.py; they will not run without the texts.

The real E6 Supports + E2 Context workflow, review/note/status, disposable session for removal, reopening and native check remain pending. Neither E6 nor E2 will be removed or changed. No Ask/LLM question, benchmark or reindexing is part of this workflow.

## R — Preservation

Full comparison of every tuple, including BLOBs, against the read-only 0.4b source copy: 10 papers, 180 sections, 2255 source_spans, 2342 vectors, 17 settings, three preexisting SavedEvidence items (including E6/E2) and 21 preexisting events identical. The 22 monitored rag/llm/graph files and migrations 001–006 retain their SHA-256. The overall SQLite hash naturally changes with the schema; it was not used as a preservation test.

The SavedEvidence API projection now adds related claim IDs/statuses, without changing any persisted column. Migration 007 triggers are additional; no prior event payload/timestamp/actor/ID is rewritten. The validated 0.4b copy and main database were not mutated. No changes to Ask, prompts, validator, repair, models, settings, embeddings or graph.

## S — Changed files

- New migration 007_research_claims.sql; allowlist in src-tauri/src/main.rs.
- New engine/petrus_engine/claims.py domain; dispatch in service.py; reverse projection in research.py; event types/projection in trail.py.
- New Findings.tsx; integration in ResearchSessionWorkspace.tsx, ResearchEvidenceWorkspace.tsx and ResearchTrail.tsx; DTOs in services/api.ts; app.css styles and EN/PT-BR catalogs.
- New engine/tests/test_research_claims.py, ledger expectation in test_engine.py; new tests/research-claims.spec.mjs and claims-fixture.mjs; extended desktop-ui.spec.mjs.
- README, architecture, database, roadmap and this report.

## T–U — Report / current recommendation

Report: docs/validation-0.4c-findings-claims.md. Local evidence in `.local-data/findings-claims-0.4c/`: baseline/data/core hashes, preservation.json, test/build/lint/native logs and fixture screenshots. Real routines await human-text.json with user-provided text.

**BLOCKED for closing 0.4c**, awaiting human content and real/native validation. Implementation and technical tests are complete. Version retained at **0.4.1-dev / 0.4.1.dev0** until everything is validated, as requested. No final package was rebuilt or published. 0.4d was not started.
