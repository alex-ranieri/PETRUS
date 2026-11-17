**English** · [Português (Brasil)](pt-BR/validation.md)

# Validation of this iteration

Date: 15 October 2026. Environment: macOS Apple Silicon (arm64).

## Results

| Check | Result |
|---|---|
| Engine pytest | 21 tests passed |
| Complete Playwright workflow | 1 end-to-end test passed |
| ESLint + TypeScript | No errors |
| Ruff | No errors |
| Rust Clippy `-D warnings` | No warnings/errors |
| Frontend build | Passed, graph in a separate chunk |
| Development Tauri build | PETRUS.app arm64, approximately 55 MB |
| Local signing | Ad hoc signature applied; `codesign --verify --deep --strict` passed |
| Packaged engine | Ingestion, FTS5 and page text passed with the embedded Python runtime |
| Logo | Asset SHA-256 identical to the original PNG |

The Playwright test uses real React and the Python engine, a temporary database and two synthetic PDFs. It substitutes the native IPC, dialog and file open/reveal boundary. It checks onboarding, ingestion, search, details/DOI, page content, notes, collection creation/association, graph rendering, session creation and recovery after restarting the engine. Open PDF/Reveal requests are checked at the IPC boundary; the test does not automate Preview or Finder.

Native validation opened the `.app` with the packaged engine, displayed onboarding with the logo, opened the directory picker, displayed progress and the real V-GEN Lab library, and ran a text search through the interface. Light/dark screens and the graph were rendered and inspected. System open/reveal uses the compiled `OSService`; viewing content in Preview/Finder is outside the automated evidence.

The PyInstaller executable smoke test removes development Python from PATH on POSIX systems, catalogs the two synthetic PDFs, queries FTS, reads page text and exits. This confirms that the sidecar and parser subprocess work without `.venv`. In the agent execution environment, the sandbox blocks the PyInstaller bootloader semaphore; the binary test was run outside that sandbox and passed. This is not an application user dependency.

## Real library — separate initial scan

The first development scan found **266 PDFs**, of which **43 were locally available and indexed**; **223 were marked by macOS as on demand** and recorded without forcing downloads. There were two extraction warnings among available files, in addition to cloud-only locations. Searching for `dengue` returned 26 papers and the graph received 43 nodes. These figures describe the initial scan; availability and results may change after OneDrive synchronization and rescanning.

Technical output from that scan remains only in `.local-data/real-validation/`, ignored by Git. No research PDF was copied into the repository. The real library is not used in automated tests. The native UI was exercised with another test database in `.local-data/native-smoke/`.

## Evidence limits

Windows/Linux builds, public distribution, notarization, OCR, GROBID, RAG, local models and external queries were not validated. These features are disabled or on the roadmap. The delivered build is a development build for local Mac use; it is not a 1.0 release.

Tests verify that synthetic files remain identical before/after ingestion and library removal. Real-data validation reads PDFs without an exhaustive before/after hash comparison across the whole research tree.
