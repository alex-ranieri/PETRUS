**English** · [Português (Brasil)](pt-BR/validation-0.3.1-model-discovery.md)

# PETRUS 0.3.1-dev — LM Studio Model Discovery

Date: 16/10/2026. UX/provider integration stage on checkpoint 0.3.0-dev. Implementation and native validation complete; no new Ask benchmark run.

## A. Endpoint and contract

Explicit operation `llm_models({endpoint})` queries only **GET `/api/v1/models`**, validated with `http://127.0.0.1:1234`. It accepts a root or `/v1` configuration and normalizes the path to the native catalog. HTTP loopback only (`127.0.0.1`, `localhost`, `::1`), without credentials/query/fragment, proxy, redirects, telemetry or internet. Timeout 3 s, response limited to 1 MB and text fields limited to 4096 characters. No scientific content is sent.

`llm/catalog.py` shares catalog transport and reasoning interpretation with `LMStudioNativeLLMProvider`. Policy remains: capability with off sends off; capability present without off blocks; absent capability omits reasoning. Capability is not inferred from model names.

The UI receives only exact ID (`key`), display name, type/category, architecture, format, parameters, quantization, size, load state and normalized capability. Missing optional fields remain null; unrecognized types become unknown. Raw fields, paths and internal instances are not sent to the UI. Invalid/duplicate IDs are ignored; unknown models remain in the general catalog and a separate selector group.

## B–C. Actual models found and classification

Real engine query, before connection testing:

| Exact ID | Official category | Format / quantization | Parameters | Loaded in this query | Reasoning off |
|---|---|---|---|---|---|
| `google/gemma-4-e2b` | llm | mlx / 4bit | 2B | false | supported |
| `qwen3.5-4b-mlx` | llm | mlx / 4bit | 4B | false | capability absent; badge omitted |
| `qwen/qwen3.5-9b` | llm | mlx / 4bit | 9B | false | supported |
| `text-embedding-nomic-embed-text-v1.5` | embedding | gguf / Q4_K_M | null | false | capability absent; badge omitted |

The runtime returned no unknown models in this query. Classification uses `type`, without name heuristics. These are catalog-available models even when unloaded. Availability/loading may change; this snapshot is neither persistent cache nor a scientific compatibility guarantee. Querying the catalog loaded no model. No generation tests compared the listed models.

## D–E. Chat and embedding dropdowns

`LocalModelSelect` is used only when the respective provider is `lmstudio`. Chat shows llm; embedding shows embedding; unknown has its own group. Configured IDs remain visible even outside the list. Optional details appear only when known. Missing capability produces neither an error nor an invented internal-reasoning badge.

Without a saved ID, **Select a model / Selecionar um modelo** remains. No first, loaded, Qwen or embedding model is selected automatically. Selection changes only the draft; Save persists the exact ID, including Unicode strings. No baseline badge or automatic baseline selection. OpenAI-compatible retains manual input without LM Studio discovery.

## F. Refresh and connection testing

Opening the control and changing endpoints read the catalog into memory. **Refresh models / Atualizar modelos** forces another query, with button loading state. It does not save settings, change selection, call chat/embeddings, download or load models. Stale responses are discarded after endpoint changes/unmounting. No SQLite catalog table/cache was created.

**Save and check connection / Salvar e testar conexão** remains separate: it saves the draft and calls the existing provider/model test. This explicit action may use the model under the previous semantics; it is distinct from read-only discovery.

## G–I. Missing configured model, custom and offline

A missing model stays selected as **Configured — currently unavailable / Configurado — indisponível no momento**. Catalog failure shows EN/PT-BR instructions to start LM Studio and refresh, without clearing IDs or preventing Settings use. The UI does not expose raw server error text. An empty catalog has a distinct state.

**Custom model ID… / ID de modelo personalizado…** opens manual input, initially preserving the current ID. Manual IDs remain possible offline or with an incomplete catalog; Save is required to persist. No automatic change to the configured embedding.

## J. Python tests

- **212 passed**, full `engine/tests` suite, including **26 new catalog tests**.
- **48 existing native-provider tests** also passed focused verification after shared helpers were extracted.
- New coverage: normal/multiple/empty catalogs, missing/malformed optional fields, llm/embedding/unknown classification, Unicode/exact/duplicate IDs, offline, sanitized HTTP, rejected redirects, loopback, bounded/invalid responses, shared capability, GET only and no settings/database mutation.
- Ruff passed for engine, tests and scripts.

## K. Frontend tests and build

- **6 new Playwright tests**, EN/PT-BR with mocked IPC: list, classification, conditional badges, explicit selection, exact/Unicode ID saving, reopening, embedding, refresh without save/inference, loading, offline, missing, custom, empty and manual OpenAI-compatible.
- **5 existing Playwright tests**: Ask navigation with fixtures/mocked IPC, desktop flow with local fixture, i18n and scientific content. They are not a new Ask benchmark against LM Studio.
- Combined final run: **11 passed (20.5 s)**.
- ESLint and TypeScript passed without warnings.
- `npm run build` passed.
- Tauri development build 0.3.1-dev passed; app opened with the development engine and isolated database copy.
- The checkpoint 0.3.0-dev `.app` package was neither rebuilt nor replaced.

## L. Real and manual validation

Actual `Engine.call('llm_models', ...)` returned the four models above; complete before/after dumps confirmed **no database change from that query**.

The user literally confirmed **“Todos os cinco itens funcionam”** (“All five items work”) for:

1. Chat lists Gemma 4 E2B, Qwen3.5 4B and Qwen3.5 9B.
2. Select `qwen/qwen3.5-9b`, save, leave/reopen Settings and check persistence.
3. Run Save and check connection.
4. The embedding dropdown lists Nomic Embed Text v1.5.
5. Refresh preserves selection.

This is human confirmation of the native interface, separate from mocked-IPC browser tests and the actual engine query. The native GUI was not automated.

A subsequent read found `qwen3.5-4b-mlx` selected in the isolated database; this value was preserved without automatically restoring 9B. This does not change the documented baseline or replace the manual confirmation of 9B persistence. Embedding remained Nomic, temperature 0.1, context 8192, limit 1600, timeout 90 and expansion disabled.

Database used: `.local-data/model-discovery-0.3.1/native-smoke/petrus.sqlite3`, created through SQLite backup of the separate 0.3b validation database. The main application database was not used.

Preservation checked: 10 papers, 180 sections, 2255 source spans and 2342 vectors; papers/sections/spans and every embedding-index tuple, including vector blobs, identical to the copy's source. Settings changed only through explicit saving during the human check. SHA-256 for `rag/ask.py`, `rag/validation.py`, `rag/retrieval.py`, `rag/providers.py` and `llm/local.py` did not change during this stage. Prompts, validator, bounded repair, retrieval and embedding implementation preserved. Defaults 1600/90 preserved.

## M. Changed files

- Engine: new `engine/petrus_engine/llm/catalog.py`; shared refactoring in `llm/native.py`; operation in `service.py`.
- Native boundary: allowlist in `src-tauri/src/main.rs`.
- UI: new `app/src/components/LocalModelSelect.tsx`; integration in `AISettings.tsx`; types in `app/src/services/api.ts`; EN/PT-BR catalogs.
- Tests: new `engine/tests/test_model_catalog.py`; new `tests/model-discovery.spec.mjs`; mocked catalog response in `tests/ask-03b.spec.mjs`.
- Version: `package.json`, `package-lock.json`, `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`, `src-tauri/Cargo.lock`, `engine/pyproject.toml`, `engine/petrus_engine/__init__.py` and EN/PT-BR label updated to 0.3.1-dev (Python packaging: 0.3.1.dev0).
- Documentation: `README.md`, `docs/architecture.md` and this report.

## N. Local evidence and closure

Execution files in `.local-data/model-discovery-0.3.1/` (local validation data, not included in the product): `real-catalog.json`, `real-engine-discovery.json`, `core-before.json`, `data-before.json`, `preservation-check.json`, `python-tests.log`, `lint.log`, `frontend-build.log`, `native-dev.log` and `ui/*tests*.log`.

Stage 0.3.1-dev complete. No auto-selection, downloader, refresh-triggered model loading, SQLite cache, remote providers, new scientific evaluation or start of 0.4. The development app stays open for use with the isolated copy.
