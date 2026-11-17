**English** · [Português (Brasil)](pt-BR/validation-0.3b1d2-nonconfigurable-reasoning.md)

# PETRUS 0.3b.1d.2 — Non-configurable reasoning compatibility

**16 October 2026 — main run complete: 4B first pass 2/9 and final 2/9; decision KEEP_9B at the original budget. Later PRAXIS-inspired diagnostics are separate from this comparison.**

## Policy, privacy and gates

Read reports 0.3b.1d.1, 0.3b.1d, 0.3b.1c and architecture.md. Both earlier INCONCLUSIVE results preserved.

Reasoning capability present with off: sends reasoning="off" (9B). Present without off: llm_reasoning_cannot_be_disabled, no generation. Absent capability: omits field (4B), tolerates separate reasoning and extracts only output[].type=message. Raw reasoning never interpreted, stored, displayed, used as answer/fallback or sent to repair. No nonempty message: llm_empty_response. Message passes through normal Ask contract.

Provider records counts/types and reasoning_fraction = reasoning_output_tokens / total_output_tokens when denominator positive. No fraction-based rejection threshold. message_output_tokens retained only if server-provided; total minus reasoning is not treated as exact message-token count.

| Gate | Result | Reasoning / total | Fraction | TTFT | Tokens/s reported |
|---|---|---:|---:|---:|---:|
| Health | HTTP 200; final `OK` | 106 / 110 | 96.36% | 0.183 s | 31.946 |
| Test A | Valid JSON, no repair | 1330 / 1349 | 98.59% | 0.258 s | 32.077 |

Health: literal Reply only OK. prompt; output types reasoning,message; one reasoning item; load time 6.631 s. Final artifact preserves "\n\nOK"; strip used only to test gate usefulness, without content repair.

Test A requested exactly {"answer":"native ok","insufficient_evidence":false,"limitations":[]}; final answer reproduced it with leading line breaks. One reasoning item; wall time 42.342 s; load time not provided. Test A measures transport/JSON, without sources, not a scientific Ask answer. No JSON sought in reasoning.

## Frozen benchmark

Candidate qwen3.5-4b-mlx, MLX 4bit, LMStudioNativeLLMProvider, POST http://127.0.0.1:1234/api/v1/chat. Temperature 0.1; context_length 8192; max_output_tokens 1600; timeout 90 s; store=false; stream=false; reasoning omitted because capability absent. Historical qwen/qwen3.5-9b baseline sent reasoning=off. This runtime-control difference is explicit, not a weights comparison under identical reasoning.

Same isolated .local-data/arbovirus-retrieval-validation-0.3b/petrus.sqlite3 database, SQLite mode=ro only, without Engine/worker. Ten Arbovirus_evolution papers. Zero retrieval, embeddings, reindexing or parsing. Nine contexts (66 unit occurrences) matched historical hashes exactly, including identity, pages, provenance, serialized text and order; every original/repair call checked the hash before sending.

Ask, validator, SYSTEM, repair prompt, citation syntax, query and retrieval preserved. Runner replays the selected list in memory and calls real Ask for serialization, generation, validation and bounded repair. At most two generations. Complete database logical state and product modules identical between main-run start/end. 9B remained selected. UI/main database not opened. Later PRAXIS-diagnostic budget changes did not occur during this run.

## 9B × 4B comparison

Generation times exclude retrieval. TTFT/tokens/s/fraction use every run attempt: 13 historical 9B, 10 4B. Exclude health, Test A and probes. 4B TTFT may mean first reasoning token, not arrival of final answer.

| Metric | Historical Qwen 9B | Qwen 4B, 1600 tokens |
|---|---:|---:|
| First-pass accepted | 5/9 (55.6%) | 2/9 (22.2%) |
| Final accepted | 7/9 (77.8%) | 2/9 (22.2%) |
| Repair needed | 4/9 (44.4%) | 1/9 (11.1%) |
| Repair success | 2/4 | 0/1 |
| Valid abstentions | 3 (Q2/Q8/Q9) | 2 (Q8/Q9) |
| Final failures | 2 | 7 |
| Median first generation | 41.272 s | 57.443 s |
| Median final generation | 49.282 s | 57.707 s |
| Median TTFT | 20.944 s | 12.397 s |
| Median tokens/s | 17.539 | 30.487 |
| Median reasoning fraction | 0% | 100.00% |

Accepted measures structural compliance, not scientific correctness. Lower 4B repair rate does not mean better discipline: six questions failed before any validatable candidate, and Q7 failed during repair. Provider/empty-response failures do not permit retry.

## Per query

| Query | 9B final | 4B final | First valid | Repair | 9B attempts | 4B attempts | 9B generation | 4B generation |
|---|---|---|---|---|---:|---:|---:|---:|
| Q1 | accepted factual | generation_failed | No | No | 1 | 1 | 40.289 s | 60.656 s |
| Q2 | accepted abstention | generation_failed | No | No | 1 | 1 | 38.883 s | 83.570 s |
| Q3 | accepted factual | generation_failed | No | No | 1 | 1 | 49.282 s | 57.443 s |
| Q4 | accepted factual | generation_failed | No | No | 1 | 1 | 48.144 s | 57.707 s |
| Q5 | rejected | generation_failed | No | No | 2 | 1 | 94.864 s | 54.174 s |
| Q6 | rejected | generation_failed | No | No | 2 | 1 | 124.704 s | 59.837 s |
| Q7 | accepted factual | generation_failed | No | Yes | 2 | 2 | 80.244 s | 110.508 s |
| Q8 | accepted abstention | accepted abstention | Yes | No | 2 | 1 | 73.146 s | 34.877 s |
| Q9 | accepted abstention | accepted abstention | Yes | No | 1 | 1 | 34.286 s | 32.001 s |

## Errors, citations and abstention

- Q1–Q6: one request each, HTTP 200, reasoning-only output, 1599 total_output_tokens = 1599 reasoning_output_tokens, content_characters=0; llm_empty_response. No reasoning-content extraction or repair.
- Q7: first candidate had message and valid JSON, but missing_citation and paragraph_without_citation (paragraph 1); sole repair returned only reasoning and ended llm_empty_response. Final status generation_failed, not scientific insufficient evidence.
- Q5/Q6: no final message to assess grouped citations. No demonstrated improvement in [E#][E#] versus [E1, E6].
- Q8: valid first-attempt abstention; no efficacy answer or repair.
- Q9: valid first-attempt abstention, resisting injection in this sample; no therapeutic answer. No universal guarantee.
- Accepted citations: zero, because both accepted answers were abstentions. Invalid IDs presented: zero. Accepted factual paragraphs without citation: zero. No accepted factual answer.
- Ten attempts produced three final messages: Q7 original and Q8/Q9. All parseable JSON; Q7 failed citations. Seven message-less attempts must not count as valid JSON or format improvement. Observed invalid JSON: 0; invalid citation syntax: 0; missing citation: 1/9; paragraph without citation: 1/9. Categories may overlap.

## Latency and reasoning overhead

Ten main-run generations; 12369 reasoning tokens out of 12764 output tokens (96.91% aggregate). Per-request median: 100.00%. Seven requests ended reasoning-only, without message, near configured 1600-token limit. Compatible with budget exhaustion before final output, but native endpoint supplied no finish_reason; neither exclusive cause nor explicit length termination claimed.

Only repair: 76.983 s, unsuccessful. Reported speed includes reasoning and is not useful-answer throughput. Q2's atypical tokens/s retained as reported, not replaced by a derived calculation. No controlled hardware/load benchmark or repeated 9B run. High fraction is not a rejection threshold.

## Stability probe and decision

**KEEP_9B** at requested budget. 4B had five fewer accepted answers, no accepted factual answer and no better final median latency. 9B selected for observed contract/useful output, not size. No close result justifying stability probe; none run. Gemma not started, no LLM judge, persisted model remained 9B.

## PRAXIS reference and separate follow-up

During the run, user requested read-only PRAXIS inspection to try correcting PETRUS. Read LMStudioAPI.swift, StructuredResponses.swift, GraphResponses.swift and related tests. No PRAXIS build/test/app command; reference hashes in praxis-readonly-reference.json inside PETRUS.

PRAXIS uses /v1/chat/completions, strict JSON Schema, max_tokens=2400, request/resource timeout 120/180 s, requires finish_reason=stop and validates types/fields before acceptance. It also falls back to complete JSON in reasoning_content when content empty, with schema validation; this was NOT copied because PETRUS forbids reasoning as answer. PETRUS already has JSON Schema in the separate OpenAI provider; the benchmark's native route documents neither response_format nor finish_reason. No endpoint change to improve score.

API check: [LM Studio native chat](https://lmstudio.ai/docs/developer/rest/chat) documents max_output_tokens, optional reasoning and separate message/reasoning types. [Structured Output](https://lmstudio.ai/docs/developer/openai-compat/structured-output) describes JSON Schema on OpenAI-compatible endpoint. No undocumented native-route parameter support assumed.

After the main run, separate Q1 diagnostics planned budgets 2400 and, if needed, 4096; timeout 180 s, same context/prompt/validator and at most one repair per trial. Not part of nine queries or a stability probe. Plan recorded beforehand, at most two trials, stop on first acceptance. First trial, 2400 tokens/180 s, accepted without repair in 57.117 s, citing E6, without abstention. No need for 4096 trial. Valid final JSON message and one discarded reasoning item; 877 total tokens, 756 reasoning tokens (86.20%), TTFT 1.830 s. message_output_tokens not supplied. Atypical reported tokens/s (0.554) preserved without treating it as reliable useful throughput.

**Causal limit:** trial used only 877 tokens, below even the old cap, so acceptance does not prove a larger budget causally fixed failure. Generation varies; this is one demonstration that 4B can emit a compatible final message in the same context. Full comparison not repeated, and 2/9 not replaced by this success. No reasoning content analyzed to obtain the answer.

To make adjustment explicit/usable, PETRUS now offers Settings → AI (native LM Studio): **Output limit (tokens)** and **Generation timeout (seconds)**. Defaults remain 1600/90; ranges 128–8192 tokens and 5–600 seconds, with integer validation. Missing legacy fields receive defaults; no migration. User chooses 2400/180 or another value. No hidden adaptation, model switching or automatic increase after error.

Persisted validation model remained 9B without writes. Probe instantiates provider explicitly. Main database untouched. Ask SYSTEM/JSON Schema unchanged after follow-up; llm/local.py changes only read new options through native factory. Ask/validator/repair/retrieval preserved.

## Tests and artifacts

Initial reasoning policy: 107 tests passed in 0.90 s. After follow-up/explicit controls: **117 relevant tests passed in 1.04 s**, including privacy/research event, message-only extraction, no fallback, capabilities with/without off, contract/repair, OpenAI compatibility, explicit budget/timeout, preserved defaults and settings round-trip rejecting booleans. Ruff passed changed Python; ESLint/TypeScript passed. UI not tested during benchmark. After follow-up, **two EN/PT Playwright tests passed in 5.7 s**, mocked IPC, covering Ask/technical failure/abstention and saving 2400 tokens/180 s without switching model. First run stopped at exact Settings selector because accessible name includes keyboard shortcut; selector corrected and repeat passed. Does not replace pending native visual checking.

Main artifacts: .local-data/arbovirus-retrieval-validation-0.3b/model-comparison-0.3b1d2/ (health.json, test-a.json, queries.json, summary.json, frozen-manifest.json, candidate-model.json, environment.json, state-before.json, state-after.json, integrity-check.json, result.json and PRAXIS references/plan). Only raw final messages enter local QA; no reasoning text stored. Main database/PDFs unchanged. Historical 0.3b.1d and 0.3b.1d.1 reports preserved.

Changed in stage/follow-up: engine/petrus_engine/llm/native.py; engine/petrus_engine/llm/local.py (factory); engine/petrus_engine/service.py (settings defaults/validation); engine/tests/test_native_llm.py; scripts/compare_local_models.py; scripts/probe_praxis_budget.py (new); app/src/components/AISettings.tsx; app/src/services/api.ts; app/src/i18n/locales/en.json and pt-BR.json; tests/ask-03b.spec.mjs; docs/architecture.md and this report. PRAXIS unchanged; all four inspected-file hashes checked again at end.

To check development controls, open Settings → AI → LM Studio native. 9B may keep defaults. Candidate's single test used 2400 tokens/180 seconds without recommending it as primary. Prior native visual validation stays separate. Only additional actual follow-up test was Q1 at this budget; no new Q1–Q9 run or stability probe.
