**English** · [Português (Brasil)](pt-BR/roadmap.md)

# Current roadmap

| Stage | Status / scope |
|---|---|
| 0.1–0.2 | Implemented: library, scientific parsing, references, provenance, EN/PT-BR |
| 0.3 / 0.3.0-dev | Validated: embeddings, hybrid retrieval, Ask with validation/repair, optional semantic graph and development package |
| 0.3.1-dev | Validated: LM Studio model catalog and explicit selection |
| 0.4a | Validated in 0.4.0-dev: per-session snapshots, human decisions/notes, filters, origin and basic events; real workflow and reopening confirmed |
| 0.4b | Validated in 0.4.1-dev: per-session Research Trail, actors, immutable history, audited notes/removals; real workflow, native checks and reopening confirmed |
| 0.4c | Implemented; validation in progress: human claims, Supports/Contradicts/Context links, history, review and archiving |
| Remaining stages | Synthesis (0.4d), export and external discovery require their own scope and authorization |
| 1.0 | Stable macOS/Windows/Linux distribution, subject to validation of each platform |

[0.4a report](validation-0.4a-evidence-workspace.md). No future stage starts automatically.

## Planned work

Planning only: this documentation update does not implement these features, promise dates or assign future version numbers.

| Direction | Scope | Acceptance |
|---|---|---|
| PDF discovery agent | Question/topic/DOI search, reference expansion, candidate review, authorized open-access acquisition and indexing | Explicit opt-in to external search, approved downloads or bounded batch policy, source URL/date/identifiers/access metadata, PDF validation, SHA-256 deduplication, timeouts, cancellation, rate limits and visible failures; no paywall bypass |
| Ollama integration | Dedicated provider, explicit chat and embedding models, health/capability checks | Existing Ask citation/validation contract preserved; test EN/PT, failures, offline inference and local-only model execution; no silent cloud fallback |
| Model manager | Optional catalog, download/update/removal, storage and hardware guidance | Show model identity/version or digest, license, quantization, size and measured hardware profile; explicit consent, progress, cancellation and integrity checks where supported; embedding changes require explicit reindexing |
| Managed runtime | Evaluate PETRUS-managed inference and optional downloadable model packs | Compare separate Ollama installation with distributable runtime options; establish redistribution rights, process ownership, loopback controls, updates, uninstall behavior and tests per OS |
| Cross-platform distribution | macOS arm64, Windows x64, Linux x64; other architectures later | Native sidecar builds, fresh-machine install/launch/upgrade checks, file dialogs, PDF opening, database migrations, optional AI, documented signing and artifacts |
| Evidence export and reports | Portable evidence/claim/trail export and report building | Preserve source identity and provenance; distinguish exact source text, human writing and generated content |
| Scoped synthesis | A separately designed future assistive workflow | Human review and traceable citations; do not replace or auto-generate the current human-only Findings |
| Usability and extraction | OCR, metadata editing, job cancellation, accessibility | Preserve originals, record processing changes and expose extraction uncertainty |

### Proposed sequence

1. Complete real-corpus validation of existing human claims and consolidate the macOS package.
2. Publish a clearly labeled macOS prerelease with installation notes and reproducible release assets.
3. Add and validate the optional Ollama provider/model manager; evaluate a managed runtime separately.
4. Validate Windows and Linux in native build/test environments; introduce a CI build matrix after successful platform bring-up.
5. Implement external discovery and the PDF agent as an explicit online module, followed by exports/reports and separately scoped synthesis.

This ordering is a proposal, not an implementation commitment. Local library/search must remain usable without models, downloads or external search. Model/runtime redistribution is a separate decision from offering downloads. Offline use requires previously available PDFs, models and runtimes.

Ollama offers local and cloud APIs; a PETRUS local-only integration must select downloaded local models and test that inference does not leave the device. See [Ollama API](https://docs.ollama.com/api/introduction) and [model downloads](https://docs.ollama.com/api/pull).

## Historical planning

The table below records earlier planning, not current status. The optional semantic graph was implemented in the 0.3 series; session work was split into workspace 0.4a and trail 0.4b. Original future versions are not implementation or date commitments.

| Version | Scope |
|---|---|
| 0.1 — implemented | Local library, basic metadata, FTS5, initial graph, notes and session scaffold |
| 0.2 — implemented | Structured scientific parsing, GROBID, references, citation graph and English / Português (Brasil) interface |
| 0.3 | Embeddings, local RAG, evidence-level answers and links to PDF pages |
| 0.4 | Semantic graph: methods, results, limitations and datasets |
| 0.5 | Complete sessions, Evidence Cards, Research Trail and Report Builder |
| 0.6 | OpenAlex, citation expansion and open-access discovery |
| 0.7 | Research Agent, autonomous evidence search, authorized acquisition and reindexing |
| 1.0 | Stable macOS and Windows distribution |

Before public distribution: real builds/tests per platform, signing/notarization, update policy, dependency review, editable metadata and accessibility review. OCR, metadata correction and manual job cancellation are priority incremental improvements. No automatic date forecast is provided.

0.2 scope validation: [validation-0.2.md](validation-0.2.md).
