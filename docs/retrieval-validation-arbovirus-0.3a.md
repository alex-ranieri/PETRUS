**English** · [Português (Brasil)](pt-BR/retrieval-validation-arbovirus-0.3a.md)

# Real retrieval validation — Arbovirus_evolution / PETRUS 0.3a

Date: **October 15, 2026**. Final structured round, after the user initiates GROBID. Objective: evaluate retrieval, without generating responses, syntheses, or automatic relevance judgments.

## Scope and isolation

Single folder: `/Users/alexranieri/Library/CloudStorage/OneDrive-Pessoal/Butantan/V-GEN Lab/Arbovirus_evolution`.
Separate database: `.local-data/arbovirus-retrieval-validation/petrus.sqlite3`, with `PETRUS_DATA_DIR` defined only in validation processes. Only this library was registered; no main database, PDF, or search directory was altered. PDFs were read, without forcing cloud-only downloads.

Inventory before parsing: **10 PDFs, 10 locations, 10 unique contents by SHA-256, 0 duplicates, 0 cloud-only/unavailable**, 26,376,504 bytes (~25.16 MiB). The 14 existing embeddings/retrieval tests passed in 0.90 s before real validation.

## Parsing and provenance

Initially GROBID returned a refused connection in `127.0.0.1:8070`; a pypdf baseline was made. After the user started the service, the health check returned available and the same ten articles were processed. There was no installation, recompilation, or automatic start of GROBID.

| Metric | Final round |
|---|---:|
| Papers | 10 |
| Structured without warnings | 0 |
| Structured with warnings | 10 |
| Failed scientific attempts | 0 |
| Sections | 180 |
| References | 889 |
| Source spans | 2255 |
| Spans coordinate | 2252 |
| Spans exact alignment | 3 |
| EvidenceUnits coordinate | 2252 |
| EvidenceUnits exact_page_alignment | 3 |
| EvidenceUnits section_only | 71 |
| EvidenceUnits basic_page_text | 0 |

The ten articles registered `page_mapping_missing` and `page_mapping_partial`. Lack of mapping was not converted to a presumed page. Basic text per page remains preserved in the database, but, having structure, the projection uses spans/sections.

## Real embeddings

Provider: `lmstudio:127.0.0.1:1234/v1`. Endpoint: `http://127.0.0.1:1234/v1`. Exact model: **`text-embedding-nomic-embed-text-v1.5`**, dimension **768**, GGUF Q4_K_M. The endpoint `/api/v0/models` identified this model as embeddings; BGE-M3 was not listed. The other advertised models were not used. No model download nor LLM generation occurred.

The only small initial call used "Arbovirus evolution.": 1 finite vector, dimension 768 and compatible response. The server was active; the first call took 19.647 s, including possible initial model loading. It is not claimed that this time measures exclusively inference.

| Measure | Result |
|---|---:|
| Total EvidenceUnits | 2326 |
| Eligible (≤6,000 characters) | 2315 |
| Indexed in the round | 2315 |
| Cache reused in the first structured indexing | 0 |
| Skipped by size | 11 |
| Skipped by error | 0 |
| Current vectors in SQLite | 2315 |
| Stale baseline vectors removed | 90 |
| Payload float32 | 7,111,680 bytes |
| Embedding_index table via dbstat (without auxiliary indexes) | 9,506,816 bytes |
| Max batch / indexing calls | 16 / 145 |

No unit above 6,000 characters was truncated. The limit is of characters, not a tokenizer. The endpoint announced a maximum context of 2,048 tokens; in this round there were no rejections due to context, but internal truncation handling by the server was not audited. PETRUS did not truncate the accepted inputs. No model-specific prefixes/task instructions were added; this is the current provider's baseline.

## Times and cache

| Step | Time |
|---|---:|
| pypdf cataloging | 8.813 s |
| GROBID parsing of the 10 articles | 55.501 s |
| Total structured indexing | 110.055 s |
| Approximate average per indexed unit | 0.0475 s |
| Cache test | 0.185 s |
| 15 queries × 3 modes | 8.299 s |

Cache: paper P1, 120 units requested, 117 eligible, **117 cached, 0 new embeddings**, 3 size warnings. Hash/provider/model avoided new inference on eligible units.

## Paper identification

IDs are local to this database, not global identifiers. Titles/metadata below are the extracted ones, without external bibliographic validation.

| ID | Title | Vectors |
|---|---|---|
| P1 | Arboviral Diseases in a Changing World: Evolutionary Dynamics, Host-Vector Interactions, and Novel Control Strategies | 117 |
| P2 | Evolution and adaptation of dengue virus in response to high-temperature passaging in mosquito cells | 235 |
| P3 | Genome-Wide Patterns of Intrahuman Dengue Virus Diversity Reveal Associations with Viral Phylogenetic Clade and Interhost Diversity | 229 |
| P4 | Global Transmission and Evolution of Chikungunya Virus: Origins, Adaptive Mutations, and Intercontinental Spread of the Three Genotypes | 157 |
| P5 | Global epidemiology and evolutionary dynamics of arboviruses: A systematic review of surveillance, control strategies, and emerging threats | 295 |
| P6 | Host-adaptive mutations in Chikungunya virus genome | 221 |
| P7 | Human movement and environmental barriers shape the emergence of dengue | 208 |
| P8 | Insights into Arbovirus Evolution and Adaptation from Experimental Studies | 365 |
| P9 | Intrahost population dynamics of chikungunya virus in humans and naturally infected Aedes mosquitoes reveal transmission-driven diversity | 255 |
| P10 | Strengthening arbovirus surveillance: bridging gaps for global health preparedness | 233 |

## Comparison of the 15 queries

Each mode recorded Top 5. The table summarizes Top 1; the complete orders are in the following table and the short original snippets remain only in local files. `top5_overlap` = intersections of unit IDs (L∩S / L∩H / S∩H), without inference of accuracy. `paginated_hits` uses the `supports_paginated_evidence` policy, not just the existence of page number.

| Query | lexical_top1 | semantic_top1 | hybrid_top1 | top5_overlap L/S · L/H · S/H | paginated_hits H |
|---|---|---|---|---|---:|
| arbovirus evolution | P8 | P5 | P8 | 0 / 2 / 0 | 3 |
| recombination in arboviruses | P1 | P5 | P1 | 0 / 3 / 2 | 3 |
| phylogenetic analysis of arboviruses | P5 | P5 | P5 | 0 / 3 / 1 | 5 |
| genomic surveillance | P10 | P4 | P10 | 0 / 0 / 2 | 5 |
| evolutionary dynamics of arboviruses | P5 | P5 | P5 | 0 / 1 / 2 | 5 |
| evolução de arbovírus | — | P5 | P5 | 0 / 0 / 5 | 5 |
| recombinação em arbovírus | — | P5 | P5 | 0 / 0 / 5 | 5 |
| análise filogenética | — | P1 | P1 | 0 / 0 / 5 | 5 |
| vigilância genômica | — | P4 | P4 | 0 / 0 / 5 | 5 |
| dinâmica evolutiva dos arbovírus | — | P5 | P5 | 0 / 0 / 5 | 5 |
| phylogenetic reconstruction method | P4 | P7 | P4 | 1 / 2 / 2 | 4 |
| método de reconstrução filogenética | — | P4 | P4 | 0 / 0 / 5 | 3 |
| software used for phylogenetic analysis | P4 | P4 | P4 | 0 / 2 / 1 | 4 |
| software utilizado para análise filogenética | — | P7 | P7 | 0 / 0 / 5 | 5 |
| phylogenetic analysis | P4 | P7 | P4 | 0 / 2 / 2 | 4 |

| Query | Lexical Top 5 (order) | Semantic Top 5 (order) | Hybrid Top 5 (order) |
|---|---|---|---|
| arbovirus evolution | P8, P8, P8, P8, P8 | P5, P8, P2, P9, P9 | P8, P8, P8, P8, P8 |
| recombination in arboviruses | P1, P1, P1, P1, P1 | P5, P8, P8, P8, P8 | P1, P1, P5, P1, P8 |
| phylogenetic analysis of arboviruses | P5, P5, P5, P5, P5 | P5, P8, P8, P5, P5 | P5, P5, P5, P5, P5 |
| genomic surveillance | P10, P10, P10, P10, P10 | P4, P10, P10, P5, P10 | P10, P10, P10, P10, P10 |
| evolutionary dynamics of arboviruses | P5, P5, P5, P5, P5 | P5, P1, P8, P8, P5 | P5, P5, P5, P5, P5 |
| evolução de arbovírus | — | P5, P9, P7, P5, P5 | P5, P9, P7, P5, P5 |
| recombinação em arbovírus | — | P5, P5, P7, P8, P10 | P5, P5, P7, P8, P10 |
| análise filogenética | — | P1, P10, P10, P5, P9 | P1, P10, P10, P5, P9 |
| vigilância genômica | — | P4, P10, P10, P10, P10 | P4, P10, P10, P10, P10 |
| dinâmica evolutiva dos arbovírus | — | P5, P5, P2, P1, P5 | P5, P5, P2, P1, P5 |
| phylogenetic reconstruction method | P4, P4, P4, P4, P4 | P7, P4, P9, P4, P4 | P4, P4, P4, P4, P4 |
| método de reconstrução filogenética | — | P4, P7, P4, P7, P10 | P4, P7, P4, P7, P10 |
| software used for phylogenetic analysis | P4, P4, P4, P4, P4 | P4, P4, P2, P7, P4 | P4, P4, P4, P4, P4 |
| software utilizado para análise filogenética | — | P7, P7, P7, P9, P7 | P7, P7, P7, P9, P7 |
| phylogenetic analysis | P4, P4, P4, P4, P4 | P7, P4, P4, P4, P4 | P4, P4, P4, P4, P4 |

Top 5 means five **units**, with possibly several excerpts from the same paper. No diversity by paper or relevance threshold was added. FTS requires terms combined with AND and operates on papers; overlap chooses units. RRF continues k=60 and 30 candidates per source. Graph relations and thresholds were not changed.

### Provenance of Hybrid Top-5

| Provenance | Occurrences |
|---|---:|
| coordinate | 66 |
| exact_page_alignment | 0 |
| section_only | 9 |
| basic_page_text | 0 |

Total: 75 occurrences, with repetition between queries; **66** enabled for paginated evidence, **66** with known page. Coordinates indicate origin reported by the parser, do not guarantee scientific relevance or sufficiency of the excerpt.

Descriptive observations: lexical returned hits in **8/15 queries** (the eight queries in English), semantic and hybrid in **15/15**. In the seven PT-BR queries, the lexical source was empty. Among the 8 queries with lexical source, the Top-1 hybrid pointed to the same paper as the Top-1 lexical in 8; this does not indicate a scientific hit. **34/75 hybrid hits** came from spans linked to references/citations, a point to inspect in human evaluation. No filter was adjusted in response to this.

## EN × PT-BR Comparison

Paper intersection uses unique IDs present in each Top 5; unit intersection uses unit IDs. Orders preserve repetitions. Identity between languages is not expected.

| Pair | Mode | EN Order | PT-BR Order | Common Papers | Common Units | EN / PT Provenance |
|---|---|---|---|---:|---:|---|
| arbovirus evolution ↔ evolução de arbovírus | lexical | P8, P8, P8, P8, P8 | — | 0 | 0 | section_only:5 / — |
| arbovirus evolution ↔ evolução de arbovírus | semantic | P5, P8, P2, P9, P9 | P5, P9, P7, P5, P5 | 2 | 1 | coordinate:5 / coordinate:5 |
| arbovirus evolution ↔ evolução de arbovírus | hybrid | P8, P8, P8, P8, P8 | P5, P9, P7, P5, P5 | 0 | 0 | coordinate:3, section_only:2 / coordinate:5 |
| genomic surveillance ↔ vigilância genômica | lexical | P10, P10, P10, P10, P10 | — | 0 | 0 | coordinate:1, section_only:4 / — |
| genomic surveillance ↔ vigilância genômica | semantic | P4, P10, P10, P5, P10 | P4, P10, P10, P10, P10 | 2 | 4 | coordinate:5 / coordinate:5 |
| genomic surveillance ↔ vigilância genômica | hybrid | P10, P10, P10, P10, P10 | P4, P10, P10, P10, P10 | 1 | 2 | coordinate:5 / coordinate:5 |
| phylogenetic analysis ↔ análise filogenética | lexical | P4, P4, P4, P4, P4 | — | 0 | 0 | coordinate:2, section_only:3 / — |
| phylogenetic analysis ↔ análise filogenética | semantic | P7, P4, P4, P4, P4 | P1, P10, P10, P5, P9 | 0 | 0 | coordinate:5 / coordinate:5 |
| phylogenetic analysis ↔ análise filogenética | hybrid | P4, P4, P4, P4, P4 | P1, P10, P10, P5, P9 | 0 | 0 | coordinate:4, section_only:1 / coordinate:5 |

## Method-oriented Queries

The classification below is purely structural: the section or an ancestor has the methods category. It is not a judgment that the excerpt answers the query. References/spans without a section or with different headings remain visible in the detailed file.

| Query | Top 1 hybrid (paper, section, page) | Top-5 H in Methods/descendants |
|---|---|---:|
| phylogenetic reconstruction method | P4, Phylogenetic Analysis., 2–2 | 0 |
| método de reconstrução filogenética | P4, no section, 13–13 | 2 |
| software used for phylogenetic analysis | P4, Evolutionary Dynamics of Three Genotypes., 3–3 | 0 |
| software utilizado para análise filogenética | P7, no section, 14–14 | 0 |

## Human evaluation — fill by user

No correct/incorrect labels assigned or accuracy calculated. Questions are retrieval probes; papers may lack evidence for some of them.

| Query | Correct paper Top-1 | Correct evidence Top-1 | Relevant in Top-3 | Relevant in Top-5 | Notes |
|---|---|---|---|---|---|
| arbovirus evolution | | | | | |
| recombination in arboviruses | | | | | |
| phylogenetic analysis of arboviruses | | | | | |
| genomic surveillance | | | | | |
| evolutionary dynamics of arboviruses | | | | | |
| evolução de arbovírus | | | | | |
| recombinação em arbovírus | | | | | |
| análise filogenética | | | | | |
| vigilância genômica | | | | | |
| dinâmica evolutiva dos arbovírus | | | | | |
| phylogenetic reconstruction method | | | | | |
| método de reconstrução filogenética | | | | | |
| software used for phylogenetic analysis | | | | | |
| software utilizado para análise filogenética | | | | | |
| phylogenetic analysis | | | | | |

## Files and reproduction

- `scripts/evaluate_retrieval.py`: local CLI, lexical/semantic/hybrid/all modes, Top K and original excerpts up to 500 characters. Rejects databases outside `.local-data` or with a library other than the authorized folder.
- `.local-data/arbovirus-retrieval-validation/query-results.json` and `query-results.txt`: Top 5 per mode/query, unit IDs, sections, pages, provenance, scores/ranks and short excerpts. Local Git-ignored outputs; no complete article text in this report.
- `results-top5.csv`: same results in tabular form for human evaluation.
- `structured-summary.json`, `embedding-summary.json`, `catalog-summary.json`: counts/timings.
- `baseline-simple/`: preserved initial pypdf database/results. Baseline created 90 vectors from 138 units, skipped 48 oversized units and had no errors. All 75 hybrid hits were basic_page_text; none eligible for paginated evidence.

```bash
PETRUS_DATA_DIR="$PWD/.local-data/arbovirus-retrieval-validation" \
  .venv/bin/python scripts/evaluate_retrieval.py \
  --query "método de reconstrução filogenética" --mode all --top-k 5
```

LM Studio must keep serving the same model at the local endpoint. Evaluator does not download models, generate answers or modify PDFs. Reads existing index without reindexing. Script Ruff passed; lexical CLI also executed.

## Limitations and next steps

- Small ten-paper corpus, no ground truth. Scores/matches establish neither relevance, truth, agreement nor causation.
- Available model was Nomic, not BGE-M3. Cross-lingual performance needs human evaluation; do not generalize to BGE-M3. RRF, candidates, filters and thresholds not tuned to this sample.
- All papers have page-mapping warnings. section_only receives no artificial page. Citation/bibliography spans also belong to the current domain; short passages/references may produce coordinate hits without sufficient evidence. Evaluate before adding filters.
- Multiple units from one paper can dominate Top 5. Long semantically skipped units may still appear through lexical retrieval.
- Parser may misinterpret metadata/headings; no editorial correction or automatic translation applied.
- No engine/ranking change, Tauri build, new app, LLM generation, Ask PETRUS, semantic graph or processing of the rest of V-GEN Lab in this run.
- Next: user completes human evaluation; inspect pages/Methods and bibliography hits, decide whether to compare another local model, then plan improvements. Do not start Ask PETRUS automatically.
