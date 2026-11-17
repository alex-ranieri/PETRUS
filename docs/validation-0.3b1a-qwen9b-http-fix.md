**English** · [Português (Brasil)](pt-BR/validation-0.3b1a-qwen9b-http-fix.md)

# PETRUS 0.3b.1a — LM Studio / Qwen 9B provider compatibility

**Later thinking diagnostics:** [tests A–C with enable_thinking=false](validation-0.3b1a-thinking-diagnostic.md). Field accepted without HTTP rejection but did not observably disable reasoning; Q1 still had empty content.

**Date: 15 October 2026. Result: HTTP 400 cause confirmed and corrected in the request; Ask validation stopped again at Q1 because final content was absent.**

Supplements [0.3b.1 validation](validation-0.3b1-real-ask-qwen9b.md), read before modification. Does not replace that run's historical results.

## Preserved scope

- Only model: `qwen/qwen3.5-9b`, local LM Studio at `http://127.0.0.1:1234/v1`, temperature 0.1, max_tokens 1600, no streaming, existing 90 s timeout.
- Final index check: 2,342 current vectors, zero stale/incompatible; no reindexing.
- Embedding unchanged: `text-embedding-nomic-embed-text-v1.5`, 768 dimensions.
- Isolated database: `.local-data/arbovirus-retrieval-validation-0.3b/petrus.sqlite3`.
- Exclusive corpus: `/Users/alexranieri/Library/CloudStorage/OneDrive-Pessoal/Butantan/V-GEN Lab/Arbovirus_evolution`, 10 papers.
- No PDF change, new GROBID processing, reindexing, download, other model or normal app database use.
- RRF=60, 30 candidates per source, boost=1.15, existing diversity, bibliography/metadata exclusion, up to eight units, serialized context up to 12,000 characters and semantic threshold=0.85 preserved; LLM expansion off.

## HTTP 400 body and confirmed cause

Historical 0.3b.1 error body cannot be recovered: previous provider discarded it. Here original Q1 request was **reproduced before changing format**, with identical six units and context. Preserved sanitized error:

```json
{
  "code": "llm_http_400",
  "status": 400,
  "provider_message": "'response_format.type' must be 'json_schema' or 'text'",
  "provider_type": null,
  "provider_code": null,
  "truncated": false
}
```

Small Test 2 reproduced exactly that message. **Confirmed HTTP 400 cause: this server rejects `response_format.type=json_object`; accepted type values are `json_schema` or `text`.** Explains protocol failure, not automatically later empty-output/timeouts.

Original Q1 reproduction: retrieval 1.886 s; HTTP attempt 9.089 s; total 10.976 s. No scientific answer received.

## Loaded model and budget

Before/after GET `/api/v0/models` and `lms ps --json` confirmed:

| Field | Value |
|---|---|
| Model / instance identifier | `qwen/qwen3.5-9b` |
| State | loaded; instance observed processingPrompt/generating during calls |
| Architecture | `qwen3_5` |
| Quantization | 4bit |
| Format/runtime | safetensors / MLX (vlm model) |
| Configured/loaded context reported by APIs | 4.096 |
| Model-advertised maximum | 262.144 |
| Final configured context | 4.096 — unchanged/no reload |

Server logs internal auto-fit with effective target 60,928 for this instance, although APIs advertise 4,096 configured context. PETRUS did not request auto-fit, load a 60k context or change LM Studio configuration. Do not equate catalog value with observed effective internal limit.

Q1: six evidence sources, serialized context 10,681 characters; full-test message content 11600 characters; output budget 1,600 tokens. Server measured **2,555 prompt tokens** in Test 5 and corrected Q1. Input + output budget = 4,155 tokens; actual corrected Q1 use was 2,769 tokens. No tokenizer created. Full structured requests received HTTP 200 without context overflow, so no basis for reloading at 8,192/16,384 tokens.

## Minimal Test 1–5 matrix

All tests used the same existing model, temperature, max_tokens and timeout. Tests 1–3: identical small messages explicitly requesting existing contract JSON. Tests 4–5: original Ask system prompt, Q1 and six original sources, checked by unit ID/serialized size.

| Test | Input chars* | Format | HTTP / result | Time | Final output |
|---|---:|---|---|---:|---|
| 1 — control | 173 | without response_format | not received; timeout | 90.003 s | not received |
| 2 — current json_object | 173 | json_object | 400; format rejected | 0.015 s | not received |
| 3 — JSON Schema | 173 | json_schema | 200 | 2.623 s | empty (`content=""`) |
| 4 — full Q1 unstructured | 11600 | without response_format | not received; timeout | 90.004 s | not received |
| 5 — full Q1 structured | 11600 | json_schema | 200 | 11.114 s | empty (`content=""`) |

*Sum of message-content characters, not equivalent to tokens or total JSON request size.

Test 2: sanitized body above. Test 3: HTTP 200, finish_reason `stop`, empty content; 53 prompt tokens, 20 completion tokens, 19 reasoning tokens. Test 5: HTTP 200, finish_reason `stop`, empty content; 2,555 prompt tokens, 162 completion tokens, 161 reasoning tokens. Only reasoning field names/sizes recorded, not content. HTTP 200 not counted as JSON/Ask compliance.

Tests 1 and 4 reached 90 s read timeout; client received no response status or final output to evaluate. Does not establish free-form works, and timeout was not increased. Calls were client-sequential, but timeout/disconnection does not guarantee immediate cancellation of server work; matrix is not a comparative speed benchmark.

## Applied correction

File: `engine/petrus_engine/llm/local.py`.

1. `LLMProviderError(ValueError)` preserves code/status, useful sanitized message, server type/code when available and truncated indicator. `str(error)` remains stable `llm_http_N`.
2. Non-2xx HTTP reads at most 16 KiB + one truncation-detection byte; only diagnostic fields retained. Final message capped at 2,048 characters, type/code at 128. Invalid/truncated JSON resembling a JSON payload omitted. Text cleans control characters and redacts message fragments, sources and reasoning tags. No raw error body persisted.
3. `json_object` replaced with explicit `json_schema`, `strict=true`, name `petrus_ask_response`, properties `answer:string`, `insufficient_evidence:boolean`, `limitations:array[string]`, all required and `additionalProperties:false`. These are existing expected model fields, without duplicated EvidenceUnits or redundant citations field.
4. Existing optional expansion uses separate `queries:array[string]` schema; not enabled/run here. Health still omits response_format.
5. Post-generation JSON/ID/paragraph validation unchanged. No automatic free-text fallback, output repair, reasoning extraction or model change.

New format **accepted by protocol**, but instance supplied no useful final content in tests. Fix removes confirmed 400 cause without asserting end-to-end compatibility. No thinking/template adjustment because internal empty-content cause undetermined.

## Q1 after engine correction

| Field | Result |
|---|---|
| Question | What methods were used for phylogenetic reconstruction? |
| QueryPlan | language en; intent methods; no expansion |
| HTTP / finish_reason | 200 / stop |
| Retrieval / HTTP generation / total Ask | 0.971 s / 37.177 s / 38.150 s |
| Candidates / units / papers | 30 / 6 / 6 |
| Serialized context | 10.681 characters |
| Final model output | empty content; no final JSON |
| Provider error | llm_empty_response |
| Result Ask | rejection + technical fallback; limitation llm_response_rejected |
| Generated / invalid citations | no generated answer; discipline not assessable |
| Generated uncited paragraphs | not assessable; zero generated paragraphs |

Service answer, not model answer: “I could not find sufficient evidence in the indexed library to answer this confidently.” Caused by technical failure. **Not scientific abstention.**

Endpoint returned separate reasoning_content: only presence/size (1,109 characters) and aggregate usage recorded. Reported use: 2,555 prompt tokens, 214 completion tokens, 213 reasoning tokens. No semantic reading or JSON recovery from that field; not inserted into answer, research event or report.

### Sources and structural grounding

| Evidence | Unit | Paper | Section | Role | Pages | Provenance |
|---|---|---:|---|---|---|---|
| E1 | `span:2042` | 10 | Genomic surveillance: | body | 3–3 | coordinate |
| E2 | `span:353` | 3 | DENV cDNA amplification and sequencing. | body | 3–3 | coordinate |
| E3 | `span:1431` | 8 | Rhabdoviruses | body | 6–6 | coordinate |
| E4 | `span:724` | 5 | Search strategy | body | 2–2 | coordinate |
| E5 | `span:9` | 1 | Data extraction and thematic categorization | body | 4–4 | coordinate |
| E6 | `span:574` | 4 | Phylogenetic Analysis. | body | 2–2 | coordinate |

Papers:

- 10: Strengthening arbovirus surveillance: bridging gaps for global health preparedness.
- 3: Genome-Wide Patterns of Intrahuman Dengue Virus Diversity Reveal Associations with Viral Phylogenetic Clade and Interhost Diversity.
- 8: Insights into Arbovirus Evolution and Adaptation from Experimental Studies.
- 5: Global epidemiology and evolutionary dynamics of arboviruses: A systematic review of surveillance, control strategies, and emerging threats.
- 1: Arboviral Diseases in a Changing World: Evolutionary Dynamics, Host-Vector Interactions, and Novel Control Strategies.
- 4: Global Transmission and Evolution of Chikungunya Virus: Origins, Adaptive Mutations, and Intercontinental Spread of the Three Genotypes.

Six sources exist exactly in current_units and match selected context; paper IDs, text and pages match; corpus members with coordinate provenance and known pages, no bibliography/metadata. Checks establish structure/origin, not relevance, entailment or scientific correctness. No final model answer: citations, external sources/URLs/DOIs, paragraph support and answer language remain unassessable. No correctness score or LLM judge.

## Stop, Q2–Q9 and UI

Q1 produced no valid answer after correction. Stopped under the request's explicit condition.

- Q2–Q7: not run; EN/PT-BR comparison pending.
- Q8 (RTS,S): not run. Its evidence selected/LLM called/abstained states unknown, not confused with Q1 technical fallback.
- Q9 (prompt injection): not run; resistance undetermined.
- Actual UI through `npm run desktop`: not run, dependent on valid engine Q1. No new native card/citation/navigation validation.
- No 4B/Gemma comparison started. No additional feature implemented.

## Tests and files

`pytest engine/tests/test_llm_compatibility.py engine/tests/test_03b.py engine/tests/test_embeddings.py -q`: **43 passed in 0.83s**. Ruff for changed Python: **passed**. UI unchanged; TypeScript/ESLint not repeated.

New `engine/tests/test_llm_compatibility.py`: preserved HTTP status/body, JSON/top-level/text errors, limits/truncation, system/evidence/excerpt redaction, controls/thinking, serialized Ask schema, expansion schema, content separate from ignored reasoning, rejected empty content and retained citation/paragraph validation. Prior suite remains. Offline tests do not replace actual matrix results.

Artifacts in `.local-data/arbovirus-retrieval-validation-0.3b/provider-compatibility-0.3b1a/`: `matrix.py`, `matrix.json`, `model-before.json`, `model-after.json`, `instances.json`, `retest_q1.py`, `q1-before-fix.json`, `q1-after-fix.json`, `index-after.json`. Result JSON stores text-free sources, metadata/diagnostics, no reasoning or full prompts. Scripts reconstruct isolated-database context in memory.

## Conclusion and later comparison

Resolved: useful HTTP diagnostics and 400 cause (H — provider/HTTP). Remaining: empty JSON Schema content (C — output contract; internal cause undetermined) and 90 s timeouts without structured output (B — latency). No evidence of insufficient memory or context overflow. Qwen 9B not yet a validated Ask baseline.

Separate controlled `qwen3.5-4b-mlx` comparison may help distinguish model/runtime behavior and latency while retaining schema/corpus. Does not guarantee resolving empty content. Require valid final content in each model before comparing quality. No automatic switch/comparison performed.
