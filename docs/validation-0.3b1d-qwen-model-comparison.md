**English** · [Português (Brasil)](pt-BR/validation-0.3b1d-qwen-model-comparison.md)

# PETRUS 0.3b.1d — Controlled local model comparison

**16 October 2026 — INCONCLUSIVE. Comparison stopped at mandatory health; no Q1–Q9 sent to 4B.**

## Result and reason for stopping

Exact candidate `qwen3.5-4b-mlx` is in the native local LM Studio catalog. Only health attempt used existing `LMStudioNativeLLMProvider` and `POST http://127.0.0.1:1234/api/v1/chat`, with `reasoning=off`, `temperature=0.1`, `context_length=8192`, `max_output_tokens=1600`, `store=false` and `stream=false`.

Server rejected the request with HTTP 400:

```text
Model 'qwen3.5-4b-mlx' does not expose reasoning configuration.
```

Transport code: `llm_http_400`; server type: `invalid_request`; server code: `invalid_value`.

This is candidate/server incompatibility with the required experimental configuration, not JSON/citation failure or a model-quality measurement. Instruction “Se falhar: PARAR” (“If it fails: STOP”) applied. No removal of `reasoning`, alternative transport/model, repeated health, query or probe. No basis to assume omitting `reasoning` guarantees reasoning disabled.

## Environment and health

- Observed environment: `macOS-27.0.1-arm64-arm-64bit`; Python `3.12.10`.
- Local catalog: MLX candidate, 4bit, 3,061,129,077 bytes; exact key `qwen3.5-4b-mlx`, no advertised capabilities.reasoning. 9B advertises reasoning options; no new 9B generation run.
- Health: one minimal generation requested through existing `status()` after catalog query. Input: `Reply only OK.`. Result: HTTP 400, without useful message.
- Reasoning tokens, TTFT, tokens/s and load time: **not provided**. Missing metrics do not mean zero reasoning.
- Requested context: 8192; effective inference context unconfirmed because call rejected.

## Frozen retrieval and integrity

Nine 0.3b.1c selections reconstructed from current unit IDs in the isolated database. Database opened only through SQLite `mode=ro` URI, without Engine/worker. No new retrieval, embedding call, alternative selection, reindexing, parsing or main-database access.

For each unit, all fields emitted in original context were checked: evidence ID, unit ID, paper ID/title, section, pages, provenance, evidence role and paginated-evidence support. Complete text reconstructed; SHA-256 of the full list serialized with `json.dumps(..., ensure_ascii=False, sort_keys=True)` matched every historical attempt for that query. Order preserved. Additional provenance fields are recorded as a current snapshot; no historical comparison claimed for fields absent from old artifacts.

**9/9 contexts reproduced exactly; 66 unit occurrences.** No query needed replacement. This verifies replay input, not execution of 4B generation.

| Query | Units | Context SHA-256 (identical to baseline) |
|---|---:|---|
| Q1 | 6 | `4c283c657c95999ecc504c23000f2001c21c4542b12f4f2256c2ab2251f2e37d` |
| Q2 | 8 | `07a58204202c66311851910bc9a941f4f638cddb1213650f0282e6268480c67c` |
| Q3 | 7 | `b241efe60c64ca96dc03b29cd72bca384c1210c169e7e27d1d9f57153559c919` |
| Q4 | 8 | `8b189a4d22c81d5f3c5de39cc3a8830834029b0fe6e9b4841dd26d05236c62d9` |
| Q5 | 8 | `07ea4386b4d2a47e58221afa5d66803fa3aae94d56865127177e31f3e7ec2c0d` |
| Q6 | 8 | `cdd11af853c954271f38335753379586458f1b075a34fcce1e622d5db435b192` |
| Q7 | 8 | `70d0d65b8ffc3f9697051746518f1bdf8d3d20efb6146f6574f9bba068189ae7` |
| Q8 | 6 | `691f4532771750ba6a4a627a8ebfdb399c32392982994f5f53df01131d2acc4d` |
| Q9 | 7 | `e9657e9e1bf24d33c0d060c390495bd998b07238cb421f6475e730752408fedc` |

Full database logical hashes before/after identical:

`029543c038b3ae705077ecfbe83c7e015bb9cedc3051251305a2e3cf585c162d`

Selected configuration remained `qwen/qwen3.5-9b`; no temporary settings writes, so no restoration needed. Ask, validator, prompts/native provider, retrieval and query hashes also unchanged. Main database and UI not opened.

## 9B × 4B comparison

Baseline reused from 0.3b.1c artifacts without repeating nine 9B questions. Both sides' times exclude retrieval; 4B column remains unmeasured. N/M means neither zero nor Ask-contract rejection.

| Metric | Historical Qwen 9B | Qwen 4B |
|---|---:|---:|
| Queries run | 9 | 0 (blocked by health) |
| First-pass accepted | 5/9 (55.6%) | N/M |
| Final accepted | 7/9 (77.8%) | N/M |
| Repair needed | 4/9 (44.4%) | N/M |
| Repair success | 2/4 (50.0%) | N/M |
| Valid abstentions | 3 (Q2/Q8/Q9) | N/M |
| Final failures | 2 (Q5/Q6) | N/M |
| First-pass invalid citation syntax | 2/9 (22.2%) | N/M |
| First-pass JSON failure | 1/9 (11.1%) | N/M |
| First-pass missing citation | 1/9 (11.1%) | N/M |
| First-pass paragraph without citation | 2/9 (22.2%) | N/M |
| Median first generation | 41.272 s | N/M |
| Median final generation (original + repair) | 49.282 s | N/M |
| Median TTFT (13 requests) | 20.944 s | N/M |
| Median tokens/s (13 requests) | 17.539 | N/M |

Error categories may overlap; rates must not be summed. Invalid citation rate here is the proportion of questions with `invalid_citation_syntax` on the first attempt. 9B had four attempts with this error among 13 requests, eight invalid-group occurrences across attempts and four in the last rejected candidate. Accepted final answers had 15 citation occurrences, zero invalid IDs presented and zero uncited factual paragraphs. This measures structural discipline, not entailment.

Previous report gives final median 50.926 s including retrieval. Here final **generation** median is 49.282 s, recalculated per query as first_generation_seconds + repair_generation_seconds before taking the median. Do not subtract one median from another. Historical median repair generation: 42.617 s; historical median retrieval + first generation: 43.995 s.

TTFT/tokens/s use 13 historical attempts (nine originals + four repairs), without weighted mean or overall-throughput estimate. Per-attempt input/output tokens, load time and other metrics remain in historical artifacts. Rejected 4B call provided none.

## Per-query result

| Query | 9B final | 4B final | 9B attempts | 4B attempts | 9B generation time | 4B generation time |
|---|---|---|---:|---:|---:|---:|
| Q1 | accepted factual | not run | 1 | 0 | 40.289 s | N/M |
| Q2 | accepted abstention | not run | 1 | 0 | 38.883 s | N/M |
| Q3 | accepted factual | not run | 1 | 0 | 49.282 s | N/M |
| Q4 | accepted factual | not run | 1 | 0 | 48.144 s | N/M |
| Q5 | rejected | not run | 2 | 0 | 94.864 s | N/M |
| Q6 | rejected | not run | 2 | 0 | 124.704 s | N/M |
| Q7 | accepted factual | not run | 2 | 0 | 80.244 s | N/M |
| Q8 | accepted abstention | not run | 2 | 0 | 73.146 s | N/M |
| Q9 | accepted abstention | not run | 1 | 0 | 34.286 s | N/M |

## Q5/Q6, Q8, Q9 and stability

- Q5/Q6: 9B repeated grouped citations after repair and stayed rejected. 4B never reached those questions; no evidence of canonical/grouped syntax preference.
- Q8: 9B first attempt invalid_json, then valid abstention after repair. 4B behavior unmeasured.
- Q9: 9B valid first-attempt abstention, resisting injection in that sample. 4B behavior unmeasured; no therapeutic recommendation generated here.
- Stability probe not run. Health gate failed before main run; no close comparative result justifying a probe.

## Scripts and checks

- New `scripts/compare_local_models.py`: preflight/health/run/probe modes; explicit provider, read-only database, hash-based context replay and capture only of final messages/metrics. Generation modes require available health with content and explicitly zero reasoning_output_tokens. Prevents silently overwriting an existing run.
- Runner uses real Ask without product changes. Only in-memory replay substitutes frozen retrieval/selection; generation, serialization, validator and bounded repair are existing implementations. Each call would verify the hash before sending. run/probe modes not executed.
- Ruff: `--config ruff.toml scripts/compare_local_models.py` passed.
- Relevant smoke/regressions: `engine/tests/test_native_llm.py` + `engine/tests/test_ask_robustness.py`: **53 passed in 1.17s**. Full 97-test suite not repeated because product unchanged.
- No new visual test; previous stage's native manual check remains separate.

Artifacts in `.local-data/arbovirus-retrieval-validation-0.3b/model-comparison-0.3b1d/`: `environment.json`, `frozen-manifest.json`, `health.json`, `state-before.json`, `state-after.json`, `baseline-summary.json` and `result.json`. No candidate queries.json or Q1–Q9 output because none executed.

## Decision and limits

**INCONCLUSIVE.** Models cannot be ranked on requested criteria without candidate Ask results. 9B remains selected. Failure shows only that current candidate/server combination rejects health with mandatory reasoning=off; not scientific or contractual inferiority of 4B.

Continuation would require explicitly resolving reasoning-disabled candidate compatibility and repeating the gate before benchmarking. No such change in this stage. No reasoning-free comparison, model switch, prompt/validator/retrieval adjustment, LLM judge or Gemma test. 9B run is historical, from another day under uncontrolled load; even a future compatible 4B run must state this limitation.
