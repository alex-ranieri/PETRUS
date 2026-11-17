**English** · [Português (Brasil)](pt-BR/validation-0.3b-arbovirus.md)

# PETRUS 0.3b validation — Arbovirus_evolution

**Date: 15 October 2026.** Local structural validation; no ground truth, no requested manual table, no invented accuracy. Baseline: [0.3a validation](retrieval-validation-arbovirus-0.3a.md).

## Scope and isolation

Exclusive corpus: the same 10 PDFs from `/Users/alexranieri/Library/CloudStorage/OneDrive-Pessoal/Butantan/V-GEN Lab/Arbovirus_evolution`. 0.3b database created through SQLite backup in `.local-data/arbovirus-retrieval-validation-0.3b/`. The 0.3a database, normal application database and PDFs were not changed. No new GROBID parsing, article/model download or processing of the rest of V-GEN Lab. Only local embedding services were used in this real run.

## Implementation

- evidence_role from structure/ancestors, without LLM. Bibliography/metadata excluded from default retrieval; `include_bibliography=true` enables discovery. Scientific paragraphs containing citations remain available.
- Non-overlapping subdivision, prioritizing paragraphs/sentences with character fallback. Child IDs/offsets preserve paper, section, source span, pages and provenance. No duplicated text in a new table.
- Finalization: transparent 1.15 boost for methods/results/limitations intent, followed by round-robin diversity (one per paper, then up to two, filling with extras if necessary). RRF=60, 30 candidates per source and 0.2.2 thresholds preserved.
- Original/normalized/language/intent QueryPlan; optional local English expansion disabled by default, fused with the original query. Language is an EN/PT heuristic, without a universal detection promise.
- Ask uses up to eight sources, prefers paginated provenance, deduplicates very similar sources with four-word-shingle Jaccard (≥0.92) and caps serialized context at 12,000 characters. Evidence-only prompt; validates JSON, existing IDs and paragraph citations. Rejects invalid output instead of presenting invented references.
- Ask/cards UI, [E#] clicks, unknown pages, paper/library navigation, separate Settings and optional saving in an active session. Uses existing research_events JSON with snapshot and timestamp.
- No new migration: roles/children are projections; existing embedding_index and research_events suffice. No new dependency.

## BEFORE vs AFTER — hybrid Top-5, 15 queries

Counts represent unit occurrences, repeated across queries. Before: recorded structured 0.3a results. After: same queries, corpus and model; no human relevance assessment.

| Diagnostic | BEFORE 0.3a | AFTER 0.3b |
|---|---:|---:|
| Hits linked to references/isolated citations | 34/75 | 0/75 |
| Mean unique papers in Top-5 | 2.07 | 4.60 |
| Hits with supports_paginated_evidence | 66/75 | 59/75 |
| Methods/descendant hits in the 4 methods queries | 2/20 | 8/20 |
| Units above 6,000 characters without subdivision | 11 | 0 |
| Raw units / projected units | 2326 | 2342 |
| Current vectors | 2315 | 2342 |

Fewer paginated hits do not demonstrate deterioration: bibliography previously had coordinates. The current version does not assign pages to section_only. Combined changes affect composition; the numbers neither causally isolate each intervention nor demonstrate better scientific relevance.

### Diversity and intent per query

The original query strings are preserved, including Portuguese inputs.

| Query | Unique papers before → after | Paginated H after | Methods H after |
|---|---|---:|---:|
| arbovirus evolution | 1 → 4 | 5 | 0 |
| recombination in arboviruses | 3 → 4 | 4 | 0 |
| phylogenetic analysis of arboviruses | 1 → 4 | 4 | 1 |
| genomic surveillance | 1 → 5 | 5 | 0 |
| evolutionary dynamics of arboviruses | 1 → 4 | 5 | 0 |
| evolução de arbovírus | 3 → 4 | 4 | 0 |
| recombinação em arbovírus | 4 → 5 | 4 | 0 |
| análise filogenética | 4 → 5 | 5 | 0 |
| vigilância genômica | 2 → 5 | 4 | 0 |
| dinâmica evolutiva dos arbovírus | 3 → 4 | 5 | 0 |
| phylogenetic reconstruction method | 1 → 5 | 3 | 2 |
| método de reconstrução filogenética | 3 → 5 | 0 | 4 |
| software used for phylogenetic analysis | 1 → 5 | 4 | 0 |
| software utilizado para análise filogenética | 2 → 5 | 3 | 2 |
| phylogenetic analysis | 1 → 5 | 4 | 0 |

AFTER provenance: `coordinate`=59, `section_only`=16.

PT-BR: all seven original queries still have no lexical hits; semantic/hybrid returned Top-5 in 7/7. LLM expansion was not enabled in real validation because no chat model had been selected. Expansion/RRF support was tested offline. No EN/PT ranking equivalence or cross-lingual correctness is claimed.

## Embeddings and invalidation

Provider `lmstudio:127.0.0.1:1234/v1`, exact model `text-embedding-nomic-embed-text-v1.5`, dimension 768. Limit 6,000 characters. The 11 large units generated **27 children**, without text loss; 2,342 final units, zero oversized units and zero embedding errors.
2315 old vectors were invalidated in the copy (new role/partitioning participates in the fingerprint), and 2342 compatible vectors created. Net +27 vectors over 0.3a; do not confuse this balance with the 2,342 re-embedded calls/units. Batches of up to 16 use the existing HTTP implementation. Bibliography remains indexable for discovery and citation graphs but is filtered before Ask candidate selection.
Indexing duration: **52.458 s**; comparative queries: **5.168 s**. P1 cache: 123 reused, 0 new embeddings, no warnings. Final status: 2342 current, 0 stale/incompatible.

## Semantic graph

**24 SEMANTIC_SIMILARITY edges**, threshold **0.85** fixed before measurement, without corpus tuning. Centroids: normalized mean of up to 12 current unit vectors per paper; priority abstract/body/methods/results/discussion/conclusion. Bibliography/metadata excluded. Blocks of 128, up to six neighbors per paper and 300 edges; filter OFF by default. Similarity does not mean agreement or scientific evidence.

## LLM and real Ask

Implemented provider: OpenAICompatibleLLMProvider / LM Studio; endpoint `http://127.0.0.1:1234/v1`, default temperature 0.1, default provider none. Health check tests model and minimal response without papers. Loopback only, without tools/redirects/proxy.

The actual catalog advertised three available generation models:

- `google/gemma-4-e2b`
- `qwen3.5-4b-mlx`
- `qwen/qwen3.5-9b`

**No chat model was selected automatically.** Since there was not exactly one unambiguous candidate, real generation and generation health checks remain pending selection in Settings → AI. Scientific context was not sent to a chat model in this validation. Generation and failures were tested with FakeLLMProvider; these are not presented as real-model validation.

The five requested questions passed through actual retrieval/selection with generation disabled. Original question text is preserved:

| Question | Selected sources | Serialized context | Generation |
|---|---:|---:|---|
| What methods were used for phylogenetic reconstruction? | 6 | 10681 characters | Not run: model not selected |
| Qual método foi utilizado para reconstrução filogenética? | 8 | 8798 characters | Not run: model not selected |
| What evidence of arbovirus adaptation is present in these papers? | 7 | 10896 characters | Not run: model not selected |
| O que estes artigos relatam sobre adaptação de arbovírus? | 8 | 11013 characters | Not run: model not selected |
| Which papers discuss genomic surveillance? | 8 | 8211 characters | Not run: model not selected |

Diagnostics: **37 evidence IDs**, all existing; 37 valid paper occurrences, 37 valid pages in 37 paginated sources; **0 bibliography/metadata sources**. Maximum observed context 11013 characters. No actual generated citation exists to validate (0 valid/0 invalid, because generation did not run). Do not interpret this as a success rate.
Without eligible sources, the service does not call an LLM and uses the EN/PT insufficiency message. Without a configured model, it requests selection and may show retrieved sources. Timeout, malformed JSON, unknown citations or uncited paragraphs result in abstention/rejection with a structured code, never invented repair.

## Tests and verification limits

- Engine: **98 tests passed in the final full suite in 5.34 s**. Includes local synthetic HTTP regression, roles/filters, diversity, boost, subdivision/offsets, stale/idempotence, QueryPlan, RRF with expansion, centroids, valid/invalid citations, abstention, timeout/JSON and session snapshots.
- Playwright: **2 focused EN/PT tests passed**, covering screen/question/answer, cards, original source, missing pages, click/highlight and semantic filter OFF/inspector. IPC/LLM are mocked; these do not prove actual native generation.
- Ruff, ESLint, TypeScript and frontend build passed. No Tauri build/new .app or native chat validation. The old `.app` retains its previously packaged engine; new workflows are in development source.
- ID/page validation checks source correspondence, **not entailment, completeness or correctness of each sentence**. Prompting alone does not solve this. Tests receive no real-paper ground truth.
- TEI/heading classification and intent/language are transparent heuristics. Some papers lack a Methods section, especially reviews; eight Methods-labeled hits do not mean eight correct answers.
- Embedding model is Nomic Q4_K_M, not BGE-M3. Character limits do not replace a tokenizer or audit the server's internal context handling.
- Ask is a synchronous engine operation with asynchronous UI, without streaming/cancellation/new queue. Exact-page opening depends on the default reader contract; the app reports this limitation.
- No external agents, OpenAlex, downloads, neural reranker or Report Builder implemented.

## Changed files

**Engine retrieval**: `engine/petrus_engine/rag/evidence.py`, `engine/petrus_engine/rag/index.py`, `engine/petrus_engine/rag/retrieval.py`, `engine/petrus_engine/rag/contracts.py`, `engine/petrus_engine/rag/query.py (novo)`, `engine/petrus_engine/rag/ask.py (novo)`.
**Providers and graph**: `engine/petrus_engine/llm/__init__.py`, `engine/petrus_engine/llm/local.py (novo)`, `engine/petrus_engine/graph/relatedness.py`, `engine/petrus_engine/graph/semantic.py (novo)`, `engine/petrus_engine/service.py`, `src-tauri/src/main.rs`.
**UI**: `app/src/components/Ask.tsx (novo)`, `app/src/components/AISettings.tsx (novo)`, `app/src/components/Settings.tsx`, `app/src/components/Graph.tsx`, `app/src/App.tsx`, `app/src/services/api.ts`, `app/src/styles/app.css`, `app/src/i18n/locales/en.json`, `app/src/i18n/locales/pt-BR.json`.
**Tests and docs**: `engine/tests/test_03b.py (novo)`, `engine/tests/test_embeddings.py`, `tests/ask-03b.spec.mjs (novo)`, `scripts/evaluate_retrieval.py`, `docs/architecture.md`, `README.md`, `docs/validation-0.3b-arbovirus.md (novo)`.

The original inline file annotations `(novo)` mean “new”; paths/annotations are retained for correspondence with the original record.

## Local artifacts and next steps

Outputs in `.local-data/arbovirus-retrieval-validation-0.3b/`: summary.json, before/after-metrics.json, query-results.json/txt, semantic-edges.json, ask-diagnostics.json and ask-checks.json. They contain diagnostics and short excerpts in detailed results; no full paper text appears in this report. 0.3a baseline preserved.

Next operational step: explicitly select a local model in Settings → AI and run Check connection; then validate a small Ask generation with available sources. No human evaluation/table is required now, nor advancement to agents or external services.
