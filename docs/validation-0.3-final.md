**English** · [Português (Brasil)](pt-BR/validation-0.3-final.md)

# PETRUS 0.3 — release checkpoint / 0.3c

**16 October 2026. Prepared checkpoint: 0.3.0-dev. Tests, development build, macOS package and sidecar smoke passed. User confirmed all seven native development checklist items and all three package visual smoke items. Final recommendation: CLOSE_0_3. Series 0.3 closed as development checkpoint 0.3.0-dev, without publication/notarization.**

## Short manual checklist — current development window

The window launches from workspace source with the isolated ten-paper database. Do not use the old registered application. Native CUA automation will not be used in this stage.

1. **Library:** confirm ten papers from the Arbovirus_evolution corpus.
2. **Settings → AI:** confirm LM Studio native; qwen/qwen3.5-9b; temperature 0.1; output limit 1600; timeout 90 s. Click Check connection and confirm success.
3. **EN/PT-BR fields:** check labels/values; save 1600/90, leave and reopen Settings; try values below/above limits and confirm blocking. Limits: tokens 128–8192, timeout 5–600 s. Boolean/string submission through the UI is unnecessary; actual backend tests cover this.
4. **Ask Q1:** submit `What methods were used for phylogenetic reconstruction?`; check loading and an accepted answer if generation is valid. If rejected, show technical failure rather than calling it insufficient evidence.
5. **Citation:** in an accepted answer, click [E#], check Evidence Card highlighting and paper/section/known page/provenance/excerpt.
6. **Navigation:** View in library → Open paper should open the PDF. The OS reader may not open at the exact page; the existing warning is expected.
7. **Abstention:** submit `What is the efficacy of the RTS,S malaria vaccine?`; if abstention is validated, check its state differs from technical failure. If generation is invalid, record failure; do not count it as abstention.

Extensive scientific evaluation is not requested. Confirming items and describing failures records manual validation. If Q1 produces no accepted answer, visual citation/card testing remains pending; success is not invented.

## Native UI status

**Development checklist confirmed by the user on 16 October 2026.** Direct item-by-item confirmation (translated responses):

| Item | User response |
|---|---|
| 1 — Library | There are ten papers |
| 2 — Settings AI / connection | Everything OK |
| 3 — Fields / limits | Values confirmed, including blocking |
| 4 — Ask Q1 | Answer OK |
| 5 — Citation / Evidence Card | Citation OK |
| 6 — Library / PDF | PDF opening correctly |
| 7 — Abstention | Insufficient evidence |

Confirmation covers all seven items above, including Q1 → citation/card → Library/PDF and the insufficient-evidence state. Source: human response, recorded in .local-data/release-checkpoint-0.3c/manual-dev-confirmation.json. No rejection was reported in the manual session; technical-failure presentation remains covered by browser tests, without inventing a native observation of that branch.

The development app compiled in 9.04 s and launched with the isolated ten-paper database. As instructed, no CUA, old registered app, AppleScript or automated clicks were used. During continuation after the checklist, the development instance was no longer running. The new package then launched explicitly through its executable, with PETRUS_DEV_ENGINE removed and PETRUS_DATA_DIR pointing to the package-smoke copy.

**Package visual smoke confirmed by the user:** “Os três itens funcionam” (“All three items work”) — Library opens with ten papers; Settings → AI opens and shows LM Studio native/Qwen 9B; Ask PETRUS opens. Confirmation followed explicit launch of the current package with package-smoke and is recorded in manual-package-confirmation.json. No repeat of Q1–Q9 was requested or run by the agent. Visual evidence is human confirmation, not automated GUI observation.

## Series 0.3 components

Local hybrid retrieval, EvidenceUnits/provenance, SQLite embeddings, EN/PT QueryPlan, Ask with sources/citations/Evidence Cards, bounded repair, validation and final research event, semantic similarity and native token/timeout settings. No new scientific capability in this stabilization.

Baseline: LMStudioNativeLLMProvider, qwen/qwen3.5-9b, reasoning off when advertised, temperature 0.1, context 8192, output 1600, timeout 90 s. Embedding text-embedding-nomic-embed-text-v1.5, 768 dimensions. 4B remains supported; it is not the recommended baseline.

Historical 9B benchmark: first pass 5/9; repair 4/9, success 2/4; final 7/9 including three abstentions; final generation median 49.282 s. Historical 4B benchmark at the same budget: first pass/final 2/9, two abstentions, seven failures; final generation median 57.707 s and median reasoning fraction 100%. The Q1 2400/180 probe was separate and did not change defaults. No new benchmark/model will run in this stage.

## Tests and regressions

- **Full Python: 186 passed in 6.44s** — .venv/bin/python -m pytest engine/tests -q. Includes two new explicit string-rejection settings cases; booleans/ranges/privacy remain covered.
- **Full Ruff for engine, tests and scripts: passed**, with ruff.toml.
- **npm run lint: passed**, including ESLint and TypeScript --noEmit.
- **Focused Playwright: 5 passed in 12.9s** — ask-03b, desktop-ui and scientific-i18n. Ask/citation/highlight/failure/abstention and EN/PT settings use mocked IPC. Onboarding/ingestion of two fixtures, search, details, collections, graph, sessions and persistence use the real Python engine with Tauri/dialog/OS boundaries substituted. These tests are not native-window observation.
- Initial pytest was restricted by the sandbox for the local HTTP mock; the suite was repeated with appropriate local permission. Version updating exposed an old editable installation (0.1.0) with an obsolete namespace; it was updated offline, without new dependencies, to 0.3.0.dev0. Version logging switched to __version__. An old graph test was adjusted to enable Shared authors explicitly, since it starts disabled under current policy. About now reads package.json version, preserving the copy/i18n test.

Tests did not change prompts, retrieval, defaults or embeddings. No LLM, 4B/Gemma or benchmark run occurred in this stage. Any Check connection/Q1/Q8 calls by the user belong to the manual checklist.

## macOS build and package

- Current PyInstaller sidecar rebuilt: arm64, with Python/NumPy/parser runtime included.
- Tauri development build passed, 9.04 s; current instance explicitly launched with the isolated database.
- **npm run desktop:build passed**, including frontend/TypeScript/Vite and Tauri debug with packaged assets; final Rust/bundle stage 13.16 s. Bundle approximately 60.19 MiB.
- Package: src-tauri/target/debug/bundle/macos/PETRUS.app. Version/CFBundleShortVersionString/CFBundleVersion 0.3.0-dev; Cargo/package.json/Tauri aligned. Python uses equivalent PEP 440 form 0.3.0.dev0, with engine version displayed as 0.3.0-dev.
- Local ad hoc signature applied and **codesign --verify --deep --strict passed**. No notarization/publication.
- Previous package preserved at .local-data/release-checkpoint-0.3c/previous/PETRUS-0.2.0.app and not opened.

### Package smoke: confirmation and limits

scripts/smoke_release_bundle.py ran the sidecar **inside the new .app**, with PATH reduced to /usr/bin:/bin, in .local-data/release-checkpoint-0.3c/package-smoke. The driver uses workspace Python only for orchestration; the executed engine includes its own packaged runtime.

Confirmed: sidecar startup/shutdown; Settings snapshot with LM Studio native/Qwen 9B/0.1/1600/90; ten-paper Library; Ask/native provider/NumPy imports and empty-question rejection before retrieval/LLM; settings round-trip; rejection of boolean/string/out-of-range values; unchanged jobs; build assets containing Ask, Settings and Library. No scan, LLM generation or paper reprocessing. Database copied through SQLite backup from validation, not the main database.

**Manually confirmed by the user:** Library with ten papers, Settings/AI with LM Studio native/Qwen 9B and Ask page in the current package. GUI was neither automated nor inferred from the sidecar; human confirmation complements technical smoke testing. No repeat of Q1/PDF in the package is claimed: that workflow was confirmed in the development instance under the original checklist.

To test the current package manually with that separate database (without using the old app or main database):

```sh
cd /Users/alexranieri/Documents/PETRUS_Follow_the_connections_Find_the_evidence
env -u PETRUS_DEV_ENGINE \
  PETRUS_DATA_DIR="$PWD/.local-data/release-checkpoint-0.3c/package-smoke" \
  ./src-tauri/target/debug/bundle/macos/PETRUS.app/Contents/MacOS/petrus
```

Development and package windows must be identified by launch mode; neither counts as visual confirmation of the other. The development instance had already closed when its confirmation arrived. Only the current package was then opened with the separate smoke database; its visual check was requested and user-confirmed after development confirmation.

## Integrity and artifacts

The agent did not open the main database. Test processes use only fixtures/temporary directories or explicitly separate validation databases. The ten-paper database retained 10 papers, 180 sections, 2255 source_spans and 2342 vectors; before/after index digest identical. Provider, prompt, Ask, validator and retrieval hashes are identical to stabilization-start hashes. Persisted selection remains qwen/qwen3.5-9b and effective settings 1600/90.

Logs/manifests in .local-data/release-checkpoint-0.3c/: pytest.log, ruff.log, frontend-lint.log, playwright.log, dev.log, sidecar-build.log, package-build.log, package-manifest.json, package-smoke.log, package-smoke.json, baseline.json, final-integrity.json and before-dev.sqlite3 backup. Smoke copy and previous package also remain there, ignored by Git. Screenshots in docs/screenshots are browser fixtures, not native captures from this stage.

Consolidated documentation: architecture.md gained CURRENT with present components and explicit historical-state markers, preserving evolution. README and version metadata aligned to the development checkpoint. 4B was not marked universally invalid and its support was not removed.

## Checkpoint and recommendation

**CLOSE_0_3.** Tests, builds, ad hoc signing, sidecar smoke, seven native development UI items and three package visual-smoke items complete. Series 0.3 closed as **PETRUS 0.3.0-dev**, a local development checkpoint. Visual confirmations are the user's; automated checks remain separately identified. No publication/notarization or automatic commit/tag; scientific limitations and deferred items remain valid.

This directory is not yet a Git repository. No init, commit or tag was run. With manual checks complete, recommended commands for the user if adopting Git:

```sh
git init
git add .
git commit -m "Checkpoint PETRUS 0.3.0-dev"
git tag -a v0.3.0-dev -m "PETRUS 0.3.0-dev release checkpoint"
```

.gitignore already excludes local databases, environments, builds and packages; these commands publish nothing. The recommended closing reference is v0.3.0-dev; no tag was created.

## Limitations and deferrals

Structural acceptance does not prove correctness/entailment; 9B output still varies. Injection resistance was observed in a sample, without a universal guarantee. Pages may be unknown; exact-page opening in the default reader is not portable. OCR, streaming, reranker, OpenAlex, Crossref, agent, Report Builder, full Research Trail, new models and indexing the entire V-GEN library are deferred. No publication/notarization or automatic commit/tag. Main database preserved.
