[English](../validation-0.3b1d-qwen-model-comparison.md) · **Português (Brasil)**

# PETRUS 0.3b.1d — Controlled local model comparison

**16 de outubro de 2026 — INCONCLUSIVE. Comparação interrompida no health obrigatório; nenhuma Q1–Q9 foi enviada ao 4B.**

## Resultado e motivo da interrupção

O candidato exato `qwen3.5-4b-mlx` está no catálogo nativo local do LM Studio. A única tentativa de health utilizou o provider existente `LMStudioNativeLLMProvider` e `POST http://127.0.0.1:1234/api/v1/chat`, com `reasoning=off`, `temperature=0.1`, `context_length=8192`, `max_output_tokens=1600`, `store=false` e `stream=false`.

O servidor recusou esse request com HTTP 400:

```text
Model 'qwen3.5-4b-mlx' does not expose reasoning configuration.
```

Código de transporte: `llm_http_400`; tipo do servidor: `invalid_request`; código do servidor: `invalid_value`.

Isso é incompatibilidade do candidato/servidor com a configuração exigida para este experimento, não falha de JSON/citações nem medida da qualidade do modelo. A instrução “Se falhar: PARAR” foi aplicada. Não foi removido `reasoning`, tentado outro transporte/modelo, repetido o health ou iniciada qualquer query/probe. Não há fundamento para supor que omitir `reasoning` garantiria reasoning desligado.

## Ambiente e health

- Ambiente observado: `macOS-27.0.1-arm64-arm-64bit`; Python `3.12.10`.
- Catálogo local: candidato MLX, quantização 4bit, 3.061.129.077 bytes; chave exata `qwen3.5-4b-mlx` e sem capabilities.reasoning anunciada. O 9B anuncia opções de reasoning; não foi executada nova geração 9B.
- Health: uma geração mínima solicitada pelo método `status()` existente, após consulta do catálogo. Input: `Reply only OK.`. Resultado: HTTP 400, sem message útil.
- Reasoning tokens, TTFT, tokens/s e load time: **não fornecidos**. Não interpretar ausência de métricas como zero reasoning.
- Contexto solicitado: 8192; contexto efetivo de inferência não confirmado porque a chamada foi recusada.

## Retrieval congelado e integridade

As nove seleções da 0.3b.1c foram reconstruídas pelos unit IDs atuais do banco isolado. O banco foi aberto exclusivamente por URI SQLite `mode=ro`, sem criar Engine/worker. Não houve novo retrieval, chamada de embedding, seleção alternativa, reindexação, parsing ou acesso ao banco principal.

Para cada unidade foram conferidos todos os campos emitidos no contexto original: evidence ID, unit ID, paper ID/título, seção, páginas, provenance, evidence role e suporte a evidência paginada. O texto foi reconstruído integralmente e o SHA-256 da lista completa serializada com `json.dumps(..., ensure_ascii=False, sort_keys=True)` coincidiu com todas as tentativas históricas da query. A ordenação foi preservada. Campos adicionais de provenance são registrados como snapshot atual; não se alega comparação histórica de campos que o artefato anterior não armazenou.

**9/9 contextos reproduzidos exatamente; 66 ocorrências de unidades.** Nenhuma query precisou de substituição. Isso verifica a entrada do replay, mas não significa que uma geração 4B tenha ocorrido.

| Query | Unidades | SHA-256 do contexto (igual ao baseline) |
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

Os hashes lógicos completos do banco antes/depois são idênticos:

`029543c038b3ae705077ecfbe83c7e015bb9cedc3051251305a2e3cf585c162d`

A configuração selecionada permaneceu `qwen/qwen3.5-9b`; não houve escrita temporária de settings, portanto nenhuma restauração foi necessária. Os hashes dos módulos de Ask, validator, prompts/provider nativo, retrieval e query também permaneceram idênticos. O banco principal e a UI não foram abertos.

## Comparação 9B × 4B

Baseline reutilizado dos artefatos da 0.3b.1c, sem repetir as nove perguntas do 9B. Tempos abaixo excluem retrieval em ambos os lados; a coluna 4B permanece não medida. N/M não significa zero nem uma rejeição do contrato Ask.

| Métrica | Qwen 9B histórico | Qwen 4B |
|---|---:|---:|
| Queries executadas | 9 | 0 (health bloqueou) |
| First-pass accepted | 5/9 (55,6%) | N/M |
| Final accepted | 7/9 (77,8%) | N/M |
| Repair needed | 4/9 (44,4%) | N/M |
| Repair success | 2/4 (50,0%) | N/M |
| Valid abstentions | 3 (Q2/Q8/Q9) | N/M |
| Final failures | 2 (Q5/Q6) | N/M |
| First-pass invalid citation syntax | 2/9 (22,2%) | N/M |
| First-pass JSON failure | 1/9 (11,1%) | N/M |
| First-pass missing citation | 1/9 (11,1%) | N/M |
| First-pass paragraph without citation | 2/9 (22,2%) | N/M |
| Median first generation | 41.272 s | N/M |
| Median final generation (original + repair) | 49.282 s | N/M |
| Median TTFT (13 requests) | 20.944 s | N/M |
| Median tokens/s (13 requests) | 17.539 | N/M |

Categorias de erro podem se sobrepor; suas taxas não devem ser somadas. Invalid citation rate nesta tabela é a proporção de perguntas com `invalid_citation_syntax` na primeira tentativa. O 9B teve quatro tentativas com esse erro entre 13 requests, oito ocorrências de grupos inválidos no conjunto de tentativas e quatro no último candidato rejeitado. Nas respostas finais aceitas houve 15 ocorrências de citações, zero IDs inválidos apresentados e zero parágrafos factuais sem citação. Isso mede disciplina estrutural, sem provar entailment.

O relatório anterior informa mediana final de 50,926 s incluindo retrieval. Para esta comparação, a mediana de **geração** final é 49,282 s, recalculada por query como first_generation_seconds + repair_generation_seconds antes de tomar a mediana. Não se subtrai uma mediana da outra. Custo histórico mediano de geração de reparo: 42,617 s; mediana histórica retrieval + primeira geração: 43,995 s.

TTFT/tokens/s usam as 13 tentativas históricas (nove originais + quatro reparos), sem média ponderada ou estimativa de throughput global. Valores de input/output tokens, load time e demais métricas por tentativa continuam nos artefatos históricos. A consulta 4B recusada não forneceu essas métricas.

## Resultado por query

| Query | 9B final | 4B final | 9B attempts | 4B attempts | 9B generation time | 4B generation time |
|---|---|---|---:|---:|---:|---:|
| Q1 | accepted factual | não executada | 1 | 0 | 40.289 s | N/M |
| Q2 | accepted abstention | não executada | 1 | 0 | 38.883 s | N/M |
| Q3 | accepted factual | não executada | 1 | 0 | 49.282 s | N/M |
| Q4 | accepted factual | não executada | 1 | 0 | 48.144 s | N/M |
| Q5 | rejected | não executada | 2 | 0 | 94.864 s | N/M |
| Q6 | rejected | não executada | 2 | 0 | 124.704 s | N/M |
| Q7 | accepted factual | não executada | 2 | 0 | 80.244 s | N/M |
| Q8 | accepted abstention | não executada | 2 | 0 | 73.146 s | N/M |
| Q9 | accepted abstention | não executada | 1 | 0 | 34.286 s | N/M |

## Q5/Q6, Q8, Q9 e estabilidade

- Q5/Q6: o 9B repetiu grouped citations após reparo e permaneceu rejeitado. O 4B não chegou a essas perguntas; não há evidência de preferência por sintaxe canônica ou agrupada.
- Q8: 9B teve invalid_json na primeira tentativa e abstinência válida após reparo. Comportamento do 4B não medido.
- Q9: 9B apresentou abstinência válida na primeira tentativa, resistindo à injeção naquela amostra. Comportamento do 4B não medido; nenhuma recomendação terapêutica foi gerada nesta etapa.
- Stability probe: não executada. O gate de health falhou antes da rodada principal; não existe resultado comparativo próximo que justifique probe.

## Scripts e verificações

- Novo `scripts/compare_local_models.py`: modos preflight/health/run/probe; provider explícito, banco read-only, reprodução de contexto com hashes e captura somente de final messages/métricas. Os modos de geração exigem health disponível com conteúdo e reasoning_output_tokens explicitamente zero. Evita sobrescrever silenciosamente uma rodada existente.
- O runner usa o Ask real sem modificar produto. Somente no replay em memória substitui a recuperação/seleção pela lista congelada; geração, serialização, validator e bounded repair são os existentes. Cada chamada conferiria o hash antes de enviá-la. Os modos run/probe não foram executados.
- Ruff: `--config ruff.toml scripts/compare_local_models.py` passou.
- Smoke/regressões relevantes: `engine/tests/test_native_llm.py` + `engine/tests/test_ask_robustness.py`: **53 passed in 1.17s**. A suíte completa de 97 não foi repetida porque não houve alteração de produto.
- Nenhum teste visual novo; checagem manual nativa da etapa anterior continua separada.

Artefatos em `.local-data/arbovirus-retrieval-validation-0.3b/model-comparison-0.3b1d/`: `environment.json`, `frozen-manifest.json`, `health.json`, `state-before.json`, `state-after.json`, `baseline-summary.json` e `result.json`. Não há queries.json do candidato nem saídas de Q1–Q9, pois nenhuma foi executada.

## Decisão e limites

**INCONCLUSIVE.** Não é possível ordenar os modelos pelos critérios pedidos sem resultados Ask do candidato. O 9B permanece selecionado. A falha demonstra apenas que a combinação atual candidato/servidor não aceita o request de health com reasoning=off obrigatório; não demonstra inferioridade científica nem contratual do 4B.

Uma continuação exigiria resolver explicitamente a compatibilidade do candidato com reasoning desligado e repetir o gate antes do benchmark. Essa mudança não foi feita nesta etapa. Não houve comparação sem reasoning, troca de modelo, ajuste de prompt/validator/retrieval, LLM judge ou teste Gemma. A rodada 9B é histórica, de outro dia e sob condições de carga não controladas; mesmo uma futura rodada 4B compatível deverá manter essa limitação explícita.
