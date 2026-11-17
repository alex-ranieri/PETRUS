**English** · [Português (Brasil)](pt-BR/validation-0.4b-research-trail.md)

# PETRUS 0.4b — Research Trail

Date: 16/10/2026. Baseline 0.4.0-dev/0.4a. Complete. Version 0.4.1-dev / Python 0.4.1.dev0, updated only after tests, real validation, human visual checks and comparison after restarting the app.

## Preflight — before the new schema

Inspection confirmed five migrations. `research_sessions` stores id, title, question/description and timestamps; `research_events` stores id, session_id/FK CASCADE, event_type, payload_json and created_at UTC. `research_evidence` (migration 005) is current state with independent snapshots, fingerprint/deduplication and human decisions/notes.

Existing events: session_created; ask (explicitly saved accepted answer, with question/answer/evidence and sanitized execution); evidence_saved, evidence_decision_changed (previous/new), evidence_note_updated (without text/hashes), evidence_removed (IDs/fingerprint/decision, without title/pagination). Local save/update/remove operations are already transactional. The API has no event edit/delete; the database still allows direct SQL. The UI shows only an activity label/date. Ask receipts are volatile, limited to 16 answers, not persistent history.

Gaps: explicit actors/object/version; automatic per-session question/retrieval/results; ranking/configuration summary; accepted/abstained/rejected/generation_failed distinction; exact note versions; interpretable removal after hard deletion; expandable timeline, links, filters and pagination.

Decision: evolve research_events without a second log or event sourcing. Preserve historical payloads, IDs and timestamps; no old question or retrieval will be fabricated. One tracking boundary will indicate earlier incompleteness.

Validation will use only `.local-data/research-trail-0.4b/native-smoke`, a SQLite backup of the isolated 0.4a copy. Both old items and their events were recorded before migration; the original database and main library remain outside this stage.

## Technical results and checks A–V

Real validation below uses the actual engine through its JSON-lines transport, local LM Studio and the isolated copy. UI coverage is separate, through Playwright/EN/PT-BR fixtures and the native human visual check confirmed by the user on 16/10/2026. No benchmark or extensive scientific evaluation was run.

| Item | Result |
|---|---|
| A — Preflight/schema | Existing tables/events inspected before migration; additive decision recorded above. |
| B — Migration | 006_research_trail.sql evolves research_events; 005 untouched; canonical metadata, chronological index, unique boundary and triggers. |
| C — Event model | Canonical JSON, payload_version=1, object, actor, UTC, SHA and on-demand projection; append-only. No second log/replay. |
| D — Actor model | User: explicit creation/question/save/decision/note/remove; AI: validated answer/abstention; System: retrieval/rejection/failure/boundary/no sources. |
| E — Question | Exact question, language/SHA; only when an explicit target session is submitted. Without a session, no Trail or session is created. |
| F — Retrieval | Current QueryPlan/config, bounded returned count, observed sources, selected identities/ranks/scores/hashes; no complete passage. |
| G — Ask results | accepted, abstained, rejected and generation_failed are distinct; only validated/canonical final content. Rejection does not persist the raw candidate. |
| H — Evidence | Manual save creates history and a durable snapshot; retrieval does not create SavedEvidence. Origin linked to the actual result when available. |
| I — Decision | Complete before/after; no event for no-op; atomic mutation and event. |
| J — Note | Exact new version + old/new hashes, only on Save note and real changes; 100 thousand characters without trim; rollback if event fails. |
| K — Removal | Title/paper SHA/fingerprint/section/pages/decision preserved; link to durable save or legacy snapshot captured in a new event. |
| L — Legacy boundary | Nine actual old events intact in all five historical fields + one boundary; no fabricated retroactive question/retrieval. |
| M — Trail UI | Evidence/Research Trail tabs; compact timeline, lazy details, local time, EN/PT-BR; previous workspace preserved. |
| N — Filters/navigation | All/User/PETRUS/System; pagination default 50/maximum 100; links to evidence, paper and related events; explicit unavailability. |
| O — Reopen | Two successive engine instances confirm identical IDs, order, timestamps, hashes and details; native app also restarted with the same database: 11 identical events. |
| P — Python | 278 tests passed (242 previous + 36 new), including legacy removal, answer identity and snapshot in another session; Ruff passed. |
| Q — Frontend | 23 passed (17 previous + 6 new); TypeScript/ESLint and Vite build passed; EN/PT images inspected. |
| R — Real validation | Q3 once, accepted on the first attempt; seven sources from seven papers, five citations; 11 events, literal workflow note and required transitions. |
| S — Preservation | 10 papers, 180 sections, 2255 spans, 2342 vectors and 17 settings identical; both old SavedEvidence items fully identical; 17 core/005 file SHA hashes unchanged. |
| T — Files | List below. |
| U — Report | docs/validation-0.4b-research-trail.md. |
| V — Recommendation | **CLOSE_0_4B**. Validation complete, 0.4.1-dev metadata updated at the end. No 0.4c work started. |

## Isolated real execution

New session **Arbovirus Research Trail test**, ID 2. Q3 was submitted with explicit session_id and retained LM Studio native / qwen/qwen3.5-9b, temperature 0.1, context 8192, output 1600 and timeout 90. Provider, model, retrieval, prompt, validator, repair and settings were not changed to obtain success. `ask_accepted` occurred in one attempt; retrieval returned 30 candidates and selected seven sources, with observed ranking and five local citations. Structural acceptance is not scientific review.

The workflow explicitly saved the first card (E1, id 3), marked Included and recorded exactly the human note supplied in the request: `Evidence selected during Research Trail validation.`. It changed Included → Uncertain → Included. It explicitly saved the second card (id 4) and removed that second item. The session retains one Included item; the trail retains the second item's save and removal. No card was saved by retrieval.

Events 11–21: session_created (user), question_asked (user), retrieval_completed (system), ask_accepted (ai), evidence_saved, evidence_decision_changed, evidence_note_updated, evidence_decision_changed, evidence_decision_changed, evidence_saved and evidence_removed (all seven last events user). Ordering created in UTC, displayed locally. The 11 IDs/timestamps/hashes and all details were compared in separate processes, unchanged. The note has SHA-256 `7188a5c7348de00c0b46626b03b1202bbbfbe69a32bf9aee8fee36070b703cea`.

The first verification routine incorrectly assumed the old item order (E6 before E2), although the workspace contract uses created_at DESC. The assertion was corrected to read-only comparison by identity; there was no second generation or repeated mutation. Actual state and events were already complete and correct. The subsequent check confirmed E6 Included + a 17-character note and E2 Uncertain, without changing any field.

## Preservation and local evidence

`.local-data/research-trail-0.4b/` contains data-before.json, legacy-events-before.json, core-before.json, preservation.json, real-validation.json, trail-before-native.json and test/build/lint/native logs. These are not product/export artifacts. Preservation comparison reads the source 0.4a SQLite copy and compares all tuples, including vector BLOBs, before calculating auxiliary hashes. It neither copies/reprocesses PDFs nor reindexes.

The nine previous events remain exactly identical in id/session_id/event_type/created_at/payload_json. Migration adds actor/object/version metadata and a boundary; it does not rewrite payloads. The original database, both old evidence items and PRAXIS were unchanged. The app points exclusively to `research-trail-0.4b/native-smoke`.

Observational limits: candidate counts are bounded returns, not the complete universe; ranks from unobserved internal fallback are unknown. Historical note versions that were never stored cannot be recovered. Append-only preserves existing session CASCADE and does not protect against direct schema administration. There is no automatic ID remapping after reprocessing or entailment guarantee. There was no new package/distribution; the packaged .app remains 0.3.0-dev.

## Implementation files

- `src-tauri/migrations/006_research_trail.sql`; allowlist in `src-tauri/src/main.rs`.
- New `engine/petrus_engine/trail.py`; integration in `service.py` and `research.py`.
- New `ResearchTrail.tsx` and `ResearchSessionWorkspace.tsx`; integration in `App.tsx`, `Ask.tsx`, `ResearchEvidenceWorkspace.tsx`, `services/api.ts`, `styles/app.css` and EN/PT-BR catalogs.
- New `engine/tests/test_research_trail.py`; compatibility in `test_engine.py` and historical note expectation in `test_research_evidence.py`; new `tests/research-trail.spec.mjs`.
- README, architecture, database, roadmap and this report. Final metadata updated after validation: package.json/package-lock.json, Cargo.toml/Cargo.lock, tauri.conf.json, engine/pyproject.toml/__init__.py and version displayed in EN/PT-BR catalogs.

Final review added three regressions: removing legacy evidence while preserving existing text without editing the old save; rejecting a manual save referencing a different persisted answer; and saving an answer in another session while retaining an independent snapshot. The last check found that historical Ask projection required `limitations`, a field not persisted by the old contract. Projection now revalidates existing citations/text with the minimum required structure; it neither invents/persists historical limitations nor modifies an old payload.

## Final native check and version

The user confirmed **“Tudo funciona”** (“Everything works”) for order/actors/question, retrieval, answer and note expansion in the new session, and E6 Included + note, E2 Uncertain and the incompleteness warning in the old session. The native window restarted in the same isolated directory; app/engine PIDs changed from 33773/33852 to 34446/34487. The 11 events were compared against the previous snapshot: identical IDs, order, UTC timestamps and payload hashes. No new generation or evidence mutation occurred during these checks.

An additional test-browser UI inspection, connected to the real engine only through allowed read operations, confirmed 11 new events, seven retrieval identities, question/retrieval/answer/note expansion and reload. The old session retains two items with included/uncertain decisions, notes of 17/0 characters and ten events (nine originals + boundary). Actual images and results are in live-trail-top.png, live-trail-note.png, live-legacy-boundary.png and live-ui.json in the local validation directory. This did not automate the native window.

After validation, metadata was raised to **0.4.1-dev / 0.4.1.dev0**. The development app remains open with the isolated copy; the old package was not replaced. Documentation and checks do not imply extensive scientific validation or a model benchmark.
