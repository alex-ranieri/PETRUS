**English** · [Português (Brasil)](pt-BR/validation-0.3b1a-thinking-diagnostic.md)

# PETRUS 0.3b.1a — thinking diagnostics / Qwen 9B

**Date: 15 October 2026. Result: Test C failed; no continuation to Q2–Q9 or UI.** Supplement to [LM Studio / provider compatibility](validation-0.3b1a-qwen9b-http-fix.md).

## Scope

Only model `qwen/qwen3.5-9b`, endpoint `http://127.0.0.1:1234/v1`. Temperature 0.1; max_tokens 1600; timeout 90 s; no streaming. Same explicit Ask JSON Schema: answer, insufficient_evidence and limitations. Same isolated `.local-data/arbovirus-retrieval-validation-0.3b/petrus.sqlite3` database, Arbovirus_evolution corpus and six Q1 EvidenceUnits. No model, embedding, context, retrieval, system prompt, schema or evidence selection changed. No PDF modified/reprocessed. No global template changed.

Local catalog in this run: Qwen 9B loaded, architecture qwen3_5, MLX 4bit, loaded_context_length=4096, max_context_length=262144. No reload or context increase.

## Real tests A–C

A and B used exactly the same small messages and schema as the preceding matrix. B's only extra field was:

```json
{"chat_template_kwargs":{"enable_thinking":false}}
```

C used the same extra field, original Ask system prompt, Q1 and original context. Question: “What methods were used for phylogenetic reconstruction?” Selection IDs and serialized size checked before calls.

| Test | HTTP | Time | Prompt tokens | Completion tokens | Reasoning tokens | Content chars | Reasoning chars* | Valid final JSON |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A_default | 200 | 11.829 s | 53 | 20 | 19 | 0 | 66 | No |
| B_thinking_off | 200 | 1.734 s | 53 | 20 | 19 | 0 | 66 | No |
| C_full_thinking_off | 200 | 27.835 s | 2555 | 175 | 174 | 0 | 805 | No |

*Only field size/presence, without persisting, displaying or interpreting reasoning content. All ended with finish_reason `stop`, without timeout or HTTP error. Final output for A, B and C: `content=""`.

## Passthrough interpretation

**Accepted without HTTP rejection: yes. Effective thinking disabling: not demonstrated.** B reproduced A's counts exactly: 53 prompt tokens, 20 completion tokens, 19 reasoning tokens, empty content. C also retained reasoning, 174 of 175 completion tokens. Evidence shows adding chat_template_kwargs at this endpoint did not resolve the observed behavior. HTTP 200 alone does not prove the field reached/was applied to the MLX template.

A was repeated in this run and matched the prior short baseline. B's shorter time does not establish a performance gain: order, warm-up/cache and a single sample were not controlled for benchmarking.

The distribution remains compatible with generation being consumed by reasoning, but does not prove that correct JSON appeared in that field. No semantic reading, parsing, promotion or fallback from reasoning to answer occurred.

## Test C / Q1

- HTTP 200, finish_reason stop; generation attempt 27.835 s.
- Retrieval before matrix: 2.375 s; 30 candidates, six EvidenceUnits, six papers.
- Serialized evidence context: 10,681 characters; total message content: 11,600 characters.
- Server-measured prompt: 2,555 tokens; completion tokens 175, reasoning tokens 174, total tokens 2,730.
- Final content: empty; valid JSON: no; Ask contract: not met.
- Generated citations: none; valid/invalid answer citations: not assessable. Do not treat 0/0 as success.
- Generated factual paragraphs without citation: not assessable because no final answer existed.
- All six units still exist and match database paper ID/pages/role; all coordinate, paginated and outside bibliography/metadata. Source checking does not prove entailment or scientific correctness.

Test C is a direct diagnostic call, not a final scientific PETRUS answer. Empty `content` would be rejected as llm_empty_response by the existing provider; no reasoning result was supplied to Ask. No scientific abstention was emitted for this technical failure.

## Alternative local route inspected — no new calls

Read-only inspection:

- Installed `tokenizer_config.json` for `lmstudio-community/Qwen3.5-9B-MLX-4bit` has Jinja condition `enable_thinking is defined and enable_thinking is false`; this branch closes the think block before generation. It confirms a template option, without proving /v1/chat/completions receives it.
- The already-installed official SDK in `.lmstudio/extensions/plugins/lmstudio/rag-v1/node_modules/@lmstudio/sdk/dist/index.d.ts` documents per-prediction `promptTemplate` and `LLMJinjaPromptTemplate.template`. Types mark this template interface deprecated/provisional.
- The smallest candidate route for later investigation is a per-prediction SDK template, binding enable_thinking=false to the original template in memory, without globally editing model files. Specific support/effect in the current MLX runtime **was not validated**. This is neither a confirmed fix nor an implementation.

Active investigation stopped after C as requested. No alternative generation experiment, new flag, global template modification or reasoning parser added.

## Provider and regressions

No provider-code/default change in this run. Adding llm_enable_thinking with default false was conditional on actual operation; because passthrough showed no effect, the setting was not added. There is therefore no configured effective support whose serialization/default can be claimed or tested as functional.

Regressions strengthened in `engine/tests/test_llm_compatibility.py`:

- Even if reasoning_content contains valid contract JSON, empty content still produces llm_empty_response.
- If content is invalid JSON and reasoning_content contains valid JSON, only content is returned and parsing fails. No fallback.
- The previous test for valid final content separate from reasoning remains.

`pytest engine/tests/test_llm_compatibility.py engine/tests/test_03b.py -q`: **30 passed in 0.52s**. Ruff for relevant Python files: **passed**. No UI change; no TypeScript/ESLint or package build.

## Stop and PRAXIS

- Q2–Q9 not resumed, including PT-BR, insufficient evidence and prompt injection; results remain unknown.
- `npm run desktop` not run and native UI not validated because Test C failed.
- 4B/Gemma not used. PRAXIS unchanged.
- No PRAXIS path was found in inspected PETRUS project files; no disk was searched to locate it, and its code/payload was not inspected.
- Conceptual comparison only: if PRAXIS uses text generation without response_format/json_schema, it exercises a different route from structured PETRUS generation and may behave differently. This is a conditional hypothesis; it proves neither that PRAXIS disables thinking nor that JSON Schema is the sole cause.

## Artifacts

`.local-data/arbovirus-retrieval-validation-0.3b/thinking-diagnostic-0.3b1a/`: `matrix.py`, `matrix.json`, `model-before.json`, `evidence-manifest.json`. Results store metadata/counts and final content only (empty), without reasoning or article text. Runner reconstructs evidence in memory from the isolated database. Manifest contains only metadata for the six sources.
