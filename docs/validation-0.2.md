**English** · [Português (Brasil)](pt-BR/validation-0.2.md)

# PETRUS 0.2 validation

Date: 15 October 2026. Platform: macOS / Apple Silicon. Tauri development build, with local ad hoc signature. Version 0.1 remains recorded in [validation.md](validation.md).

## Results with the real library

Validation used a separate SQLite backup of the development database and read-only access to PDFs in the requested library. The script opened the source database read-only, backed it up through the SQLite API and ran migrations/reprocessing only on the copy. It neither edited PDFs nor requested cloud-only file downloads. In the final run, all 266 discovered paths were already locally available. This is an execution-time snapshot, differing from availability recorded in 0.1 validation.

| Measure | Result |
|---|---:|
| Discovered local PDF locations | 266 |
| Cloud-only/unavailable locations | 0 |
| Unique SHA-256 contents attempted | 257 |
| Additional duplicate-content locations | 9 |
| Processed by GROBID | 248 |
| Failed scientific attempts | 9 |
| Extracted references | 10,773 |
| Locally resolved references | 120 |
| Candidate matches, without creating CITES | 24 |
| Directed CITES edges | 120 |
| Extracted sections | 4,228 |
| Sections with complete page ranges | 2,086 |
| Sections without complete ranges, retained as NULL | 2,142 |
| Source spans | 25,945 |
| GROBID coordinate spans | 25,850 |
| Conservative text-alignment spans | 95 |
| Independent page-layer chunks | 3,954 |
| Scientific batch duration, including final resolution | 521.13 s |

The 248 parses produced 94 structured papers and 154 structured papers with warnings. The other 9 attempts failed: 7 invalid GROBID responses/HTTP errors and 2 PDFs over the 100 MB limit. With fallback enabled, these 9 papers retained basic scientific status and the error cause. All 257 contents remained indexed in the basic layer; their basic states were 242 ready and 15 with warnings. Scientific failure does not declare physical file unavailability.

These numbers represent automatic extraction and local resolution, without manual auditing of each metadata field, citation or coordinate box. A resolved reference represents a bibliographic occurrence; two occurrences may point to the same paper pair. A fuzzy candidate is excluded from edge counts. Some spans existing is insufficient to assign a section's complete range.

## Correction identified during validation

The first run produced the same 248 extractions, 9 failures, 10,773 references and 120 edges, but only 647 paginated sections and 2,462 spans. The JVM with a Portuguese locale serialized coordinates using decimal commas, ambiguous with attribute delimiters. The parser rejected these values and used only safe text alignment.

The startup script was changed to set `-Duser.language=en -Duser.country=US` in the Java process. The entire run was repeated in another database copy; final results are in the table above. No coordinates were invented, nor was the OS language or scientific content changed.

## Tests and checks

| Check | Result |
|---|---|
| pytest, old and new | **54 passed** |
| Ruff, project configuration | Passed |
| ESLint and TypeScript | Passed |
| Clippy with `-D warnings` | Passed |
| Frontend build | Passed |
| Playwright / Chromium | **3 tests passed** |
| macOS Tauri `.app` build | Passed, 55.47 MiB |
| Local signature `codesign --verify --deep --strict` | Passed |
| Packaged-engine smoke without development Python in PATH | Passed: 2 PDFs, FTS, page text and shutdown |
| Scientific parsing through the packaged engine and local GROBID | Passed in a temporary copy: job complete, 18 sections and 93 references |

Scientific tests cover invalid TEI/DTD, metadata, references, hierarchy, EN/PT methods headings, DOI/title, candidates and false-positive rejection, CITES direction, idempotence, migration 001→002, note/page preservation, queue/progress, unavailable GROBID/timeouts, stat cache, file changes, explicit integrity checks and availability providers. HTTP mocks are used only for the adapter; no test depends on an internet scientific service.

Playwright uses the real Python engine with controlled synthetic PDFs/TEI, substituting the IPC/dialog/file-opening boundary. It checks EN/PT-BR onboarding, immediate switching, preference after page recreation, pt-PT detection and other-locale fallback, local numbers, missing-key fallback, catalog parity, absence of hardcoded main JSX text, library/Settings, original structured content, references/filters/navigation, citation inspector and Light/Dark branding. It does not replace native WebView, OS menu or actual external PDF reader tests.

## Native manual check

A copy identified as **PETRUS Validation** opened with the database copy without replacing the user's application. Checks covered:

- English and Portuguese interface; switching to Portuguese updated the UI and native Arquivo/Editar/Janela menus without restarting.
- Dark and Light themes; in Light, Home and graph were visually inspected with the real library.
- Larger original logo in sidebar and Home. Onboarding, About and image proportions also have fixture screenshots/checks.
- Real graph with 257 papers and 120 connections, citations selected by default and other relationships disabled; inspector distinguished source paper, cited paper, number and original citation.
- Opening the source paper through the inspector; Content showed translated categories and original headings/text, known pages and unknown-mapping warnings.
- References showed ordered items, metadata, status and the In library filter; Open paper navigated to the correct cited paper.

Versioned screenshots in `docs/screenshots/` use only synthetic fixtures, without reproducing full text or sensitive content from the real library. They include EN/PT-BR onboarding, library, references, citations and About in Light/Dark. Manual checking was sampled, without claiming full review of all 257 papers or every language/theme combination.

The original PNG and UI asset share SHA-256: `a9b9375eae0f8181b3fc59b9bdf7657841decbeab1deebb6f1791999f59c7bb8`. The artwork was not redrawn.

## Reproduction

For local GROBID preparation/startup on Mac, see [grobid.md](grobid.md). Preparation has already run on this machine; `bash scripts/start_grobid.sh` starts the service when port 8070 is free. Initial installation downloads official tools; parsing and resolution run locally afterward.

To repeat the batch in a **new validation folder**:

```bash
PYTHONPATH=engine .venv/bin/python scripts/validate_grobid.py \
  --source-db "/caminho/do/banco/de-desenvolvimento/petrus.sqlite3" \
  --library "/caminho/da/biblioteca" \
  --data-dir "$PWD/.local-data/nova-validacao-0.2"
```

The destination database must differ from the source. The script writes counts to `summary.json`; logs and TEI remain local and must not be published with PDFs or scientific text. The recorded run used `.local-data/validation-0.2-coordinates/`.

## Remaining limitations

- Coordinates are those reported by GROBID; they do not certify scientific interpretation. Incomplete sections retain NULL pages and warnings. Alignment does not use approximate matching to invent pages.
- Automatic metadata may contain errors, such as editorial/access dates interpreted as publication years. No external enrichment or automatic internet correction.
- The opening contract accepts a page, but the default application provides no guaranteed portable operation to open at that page. PETRUS opens the PDF and reports the limitation.
- GROBID/JVM remain optional, external to `.app`; limits are 100 MB/PDF, 60 s/request and 30 MB/TEI. No manual job cancellation at this stage.
- In the full 257-node graph, titles are small in the fitted view; zoom and accessible lists allow individual inspection.
- No actual Windows/Linux build/test, Apple notarization or public-distribution validation.
- No LLM, embeddings, RAG, external queries or automatic article downloads implemented.

Migration 001 was preserved; changes use 002. With these checks complete, scope 0.2 is marked implemented in the roadmap.
