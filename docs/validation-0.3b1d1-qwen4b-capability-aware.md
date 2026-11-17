**English** · [Português (Brasil)](pt-BR/validation-0.3b1d1-qwen4b-capability-aware.md)

# PETRUS 0.3b.1d.1 — Capability-aware reasoning + Qwen 4B

**16 October 2026 — capability negotiation implemented; comparison INCONCLUSIVE. Health received HTTP 200 but returned reasoning: 117 tokens and one item. Benchmark stopped before Test A and Q1–Q9.**

## History and change

Read: [interrupted comparison 0.3b.1d](validation-0.3b1d-qwen-model-comparison.md), [robustness 0.3b.1c](validation-0.3b1c-ask-robustness.md), [native provider 0.3b.1b](validation-0.3b1b-lmstudio-native.md) and [architecture](architecture.md). Previous INCONCLUSIVE result remains intact as history.

Prior health failed HTTP 400 because the provider sent reasoning=off to a model without public configuration for that capability. This substage corrected the request: absent capability now omits the field, without null, fallback or another model. This does not prove execution produces no reasoning; the new gate checks actual output.

Generic implementation in `engine/petrus_engine/llm/native.py`:

- Native catalog queried before first generation, model identified by exact key; cache only in provider instance.
- Present capability with off in allowed_options: sends reasoning="off". 9B keeps this policy, validated by offline regressions without new 9B generation.
- Present capability without off: llm_reasoning_cannot_be_disabled before POST.
- Absent capability: reasoning omitted entirely.
- Only eligible final messages may pass the provider. Reasoning is ignored as content; for a model without capability, a reasoning item or positive tokens block all output before message extraction, with llm_unexpected_reasoning.
- Metadata retains booleans, counts and types, never reasoning text. No OpenAICompatibleLLMProvider, prompt, validator, Ask or repair change.

## Revised real health

One catalog query and one minimal generation used the actual native provider, candidate `qwen3.5-4b-mlx`, endpoint `http://127.0.0.1:1234/api/v1/chat` and literal prompt `Reply only OK.`.

| Field | Observation |
|---|---|
| Catalog model | qwen3.5-4b-mlx, MLX 4bit |
| capabilities.reasoning | Absent |
| reasoning_parameter_sent | false; field omitted |
| HTTP | 200 |
| Output types | reasoning, message |
| Reasoning output items | **1** |
| Reasoning output tokens | **117** |
| Input / total output tokens | 14 / 121 |
| TTFT | 0.629 s |
| Reported tokens/s | 32.298 |
| Reported load time | 7.838 s |
| Result | **FAIL — llm_unexpected_reasoning** |

Request retained temperature=0.1, context_length=8192, max_output_tokens=1600, store=false and stream=false. Message-item presence was diagnosed by type; content was not extracted, presented or saved because the reasoning gate failed first. Reasoning content was also neither extracted nor persisted. Artifact contains only allowed types/counts/statistics.

These tokens/s belong to failed mixed health, including reasoning; they are not Ask final-answer throughput and are excluded from comparison with 9B. Context 8192 is the requested value, not confirmation of internal server-instance configuration.

## Test A and release gate

**Test A not run.** Stopping on observed reasoning takes precedence over test sequence. No second call, attempt to remove reasoning from output, template adjustment or final JSON extraction.

Runner already contains the exact historical Test A from native-validation-0.3b1b/preflight.py:

```text
Return exactly this JSON object: {"answer":"native ok","insufficient_evidence":false,"limitations":[]}
```

This tests only transport/JSON, without sources or repair; it would not count as scientific Ask acceptance. Execution requires clean health. Q1–Q9 require both gates, so no question ran.

## Frozen contexts and integrity

The nine contexts were reconstructed again by the same IDs in the isolated database, preserving paper IDs, pages, provenance, complete text, emitted metadata, ordering and serialization SHA-256. All matched historical 0.3b.1c attempts. This stage's manifest records all nine hashes; no retrieval/embedding call.

Database opened only in SQLite mode=ro, without Engine or worker. Before/after logical hash identical, also equal to the end of 0.3b.1d:

`029543c038b3ae705077ecfbe83c7e015bb9cedc3051251305a2e3cf585c162d`

Persisted selection remained qwen/qwen3.5-9b. No restoration needed; no settings writes. Main database not accessed. Ask, validator, prompts/OpenAI provider, retrieval and query hashes equal historical values; only native provider changed among these modules. UI not launched.

## 9B × 4B comparison

9B is the historical 0.3b.1c baseline, without new generations. N/M means not measured, not zero. Times exclude retrieval.

| Metric | Historical Qwen 9B | Qwen 4B |
|---|---:|---:|
| First-pass accepted | 5/9 | N/M |
| Final accepted | 7/9 | N/M |
| Repair needed | 4/9 (44.4%) | N/M |
| Repair success | 2/4 | N/M |
| Valid abstentions | 3 | N/M |
| Final failures | 2 | N/M |
| First-pass invalid citation syntax | 2/9 | N/M |
| First-pass invalid JSON | 1/9 | N/M |
| First-pass missing citation | 1/9 | N/M |
| First-pass paragraph without citation | 2/9 | N/M |
| Median first generation | 41.272 s | N/M |
| Median final generation | 49.282 s | N/M |
| Median TTFT (13 requests) | 20.944 s | N/M |
| Median tokens/s (13 requests) | 17.539 | N/M |

Greater structural compliance is not scientific quality. Health numbers do not replace missing Ask metrics. No LLM judge used.

| Query | Historical 9B final | 4B |
|---|---|---|
| Q1 | accepted factual | Not run |
| Q2 | accepted abstention | Not run |
| Q3 | accepted factual | Not run |
| Q4 | accepted factual | Not run |
| Q5 | rejected | Not run |
| Q6 | rejected | Not run |
| Q7 | accepted factual | Not run |
| Q8 | accepted abstention | Not run |
| Q9 | accepted abstention | Not run |

- Q5/Q6: no 4B generation; grouped citations versus [E#][E#] could not be evaluated.
- Q8: 4B abstention not measured. Historical 9B had invalid JSON followed by valid abstention in repair.
- Q9: 4B injection resistance not measured. Historical 9B abstained on first attempt.
- No stability probe: no main run had passed gates and no close result existed for comparison.

## Checks and artifacts

- **104 relevant tests passed in 1.05 s**: Ask robustness, native, 0.3b, compatibility and embeddings.
- New regressions: capability with off; absent capability and omission; capability without off blocking POST; unexpected reasoning item; positive tokens without reasoning item; preserved exclusion of private content. OpenAI transport remains covered by compatibility suite.
- Ruff with ruff.toml passed for provider, tests and runner.
- Changed: engine/petrus_engine/llm/native.py; engine/tests/test_native_llm.py; scripts/compare_local_models.py; docs/architecture.md; this report.

Separate artifacts in `.local-data/arbovirus-retrieval-validation-0.3b/model-comparison-0.3b1d1/`: environment.json, frozen-manifest.json, candidate-model.json, health.json, state-before.json, state-after.json and result.json. Prior 0.3b.1d artifacts remain intact. No test-a.json, queries.json or stability-probe.json exists for this stage because gates did not release execution.

## Decision

**INCONCLUSIVE.** Negotiation was corrected and HTTP worked, but the candidate produced actual reasoning and failed the explicit gate. Contract/citation/abstention/latency comparison could not begin. 9B remains selected.

No attempt to adjust prompt, parser, citation syntax, repair, retrieval or embeddings. No Gemma, new models or visual validation. Any further investigation into running the candidate without reasoning is a next stage; absent capability is not assumed equivalent to execution without thinking.
