[English](../validation-0.3b1d1-qwen4b-capability-aware.md) · **Português (Brasil)**

# PETRUS 0.3b.1d.1 — Capability-aware reasoning + Qwen 4B

**16 de outubro de 2026 — negociação de capabilities implementada; INCONCLUSIVE para a comparação. O health recebeu HTTP 200, mas retornou reasoning: 117 tokens e um item. Benchmark interrompido antes de Test A e Q1–Q9.**

## Histórico e alteração

Lidos: [comparação interrompida 0.3b.1d](validation-0.3b1d-qwen-model-comparison.md), [robustez 0.3b.1c](validation-0.3b1c-ask-robustness.md), [provider nativo 0.3b.1b](validation-0.3b1b-lmstudio-native.md) e [arquitetura](architecture.md). O resultado INCONCLUSIVE anterior permanece intacto como histórico.

O health anterior falhou HTTP 400 porque o provider enviava reasoning=off para um modelo sem configuração pública dessa capability. Nesta subetapa o request foi corrigido: a ausência da capability passa a causar omissão do campo, sem null, fallback ou modelo alternativo. Isso não comprova que a execução não produzirá reasoning; o novo gate verifica o output real.

Implementação genérica em `engine/petrus_engine/llm/native.py`:

- Catálogo nativo consultado antes da primeira geração, com modelo identificado pela chave exata; cache somente na instância do provider.
- Capability presente e allowed_options contendo off: envia reasoning="off". O 9B mantém essa política, validada por regressões offline, sem nova geração 9B.
- Capability presente sem off: llm_reasoning_cannot_be_disabled antes do POST.
- Capability ausente: reasoning omitido inteiramente.
- Somente mensagens finais elegíveis podem atravessar o provider. Reasoning é ignorado como conteúdo; para modelo sem capability, item reasoning ou tokens positivos bloqueiam toda a saída antes da extração de mensagens, com llm_unexpected_reasoning.
- Metadados retêm booleanos, contagens e tipos, nunca texto de reasoning. Não há alteração no OpenAICompatibleLLMProvider, prompts, validator, Ask ou repair.

## Health real revisado

Foi feita uma consulta ao catálogo e uma única geração mínima, com o provider nativo real, candidato `qwen3.5-4b-mlx`, endpoint `http://127.0.0.1:1234/api/v1/chat` e prompt literal `Reply only OK.`.

| Campo | Observado |
|---|---|
| Modelo no catálogo | qwen3.5-4b-mlx, MLX 4bit |
| capabilities.reasoning | Ausente |
| reasoning_parameter_sent | false; campo omitido |
| HTTP | 200 |
| Output types | reasoning, message |
| Reasoning output items | **1** |
| Reasoning output tokens | **117** |
| Input / total output tokens | 14 / 121 |
| TTFT | 0,629 s |
| Tokens/s reportados | 32,298 |
| Load time reportado | 7,838 s |
| Resultado | **FAIL — llm_unexpected_reasoning** |

O request conservou temperature=0.1, context_length=8192, max_output_tokens=1600, store=false e stream=false. A presença do item message foi diagnosticada pelo tipo; seu conteúdo não foi extraído, apresentado ou salvo, porque o gate de reasoning falhou antes dessa etapa. Conteúdo de reasoning também não foi extraído nem persistido. O artefato contém apenas tipos/contagens/estatísticas permitidas.

Os tokens/s acima pertencem ao health misto que falhou, incluindo reasoning; não são throughput de resposta final do Ask e não entram na comparação com o 9B. Contexto 8192 é o valor solicitado, não uma confirmação de configuração interna de instância pelo servidor.

## Test A e liberação

**Test A não executado.** A regra de parada ao observar reasoning tem precedência sobre a sequência de testes. Não houve segunda chamada, tentativa de remover reasoning do output, ajuste de template ou extração do JSON final.

O runner já contém o Test A histórico exato, recuperado de native-validation-0.3b1b/preflight.py:

```text
Return exactly this JSON object: {"answer":"native ok","insufficient_evidence":false,"limitations":[]}
```

Esse teste mede somente transporte/JSON, sem fontes e sem reparo; não seria contabilizado como aceitação científica do Ask. Sua execução está condicionada a health limpo. Q1–Q9 exigem ambos os gates, portanto nenhuma pergunta foi executada.

## Contextos congelados e integridade

Os nove contextos foram novamente reconstruídos pelos mesmos IDs no banco isolado, preservando paper IDs, páginas, provenance, texto completo, metadados emitidos, ordenação e SHA-256 de serialização. Todos coincidiram com as tentativas históricas da 0.3b.1c. O manifest desta etapa registra os nove hashes; nenhum retrieval/embedding foi chamado.

Banco aberto exclusivamente em SQLite mode=ro, sem Engine ou worker. Hash lógico antes/depois idêntico, também igual ao término da 0.3b.1d:

`029543c038b3ae705077ecfbe83c7e015bb9cedc3051251305a2e3cf585c162d`

A escolha persistida permaneceu qwen/qwen3.5-9b. Nenhuma restauração foi necessária; não houve escrita de settings. O banco principal não foi acessado. Hashes de Ask, validator, prompts/OpenAI provider, retrieval e query são iguais aos históricos; somente o provider nativo mudou entre esses módulos. A UI não foi iniciada.

## Comparação 9B × 4B

9B é baseline histórica da 0.3b.1c, sem novas gerações. N/M significa não medido, não zero. Tempos excluem retrieval.

| Métrica | Qwen 9B histórico | Qwen 4B |
|---|---:|---:|
| First-pass accepted | 5/9 | N/M |
| Final accepted | 7/9 | N/M |
| Repair needed | 4/9 (44,4%) | N/M |
| Repair success | 2/4 | N/M |
| Valid abstentions | 3 | N/M |
| Final failures | 2 | N/M |
| First-pass invalid citation syntax | 2/9 | N/M |
| First-pass invalid JSON | 1/9 | N/M |
| First-pass missing citation | 1/9 | N/M |
| First-pass paragraph without citation | 2/9 | N/M |
| Median first generation | 41,272 s | N/M |
| Median final generation | 49,282 s | N/M |
| Median TTFT (13 requests) | 20,944 s | N/M |
| Median tokens/s (13 requests) | 17,539 | N/M |

Não se transforma maior conformidade estrutural em qualidade científica. Os números do health não substituem as métricas ausentes do Ask. Nenhum LLM judge foi usado.

| Query | 9B final histórico | 4B |
|---|---|---|
| Q1 | accepted factual | Não executada |
| Q2 | accepted abstention | Não executada |
| Q3 | accepted factual | Não executada |
| Q4 | accepted factual | Não executada |
| Q5 | rejected | Não executada |
| Q6 | rejected | Não executada |
| Q7 | accepted factual | Não executada |
| Q8 | accepted abstention | Não executada |
| Q9 | accepted abstention | Não executada |

- Q5/Q6: nenhuma geração do 4B; grouped citations versus [E#][E#] não puderam ser avaliadas.
- Q8: abstinência do 4B não medida. O 9B histórico teve JSON inválido e abstinência válida no reparo.
- Q9: resistência do 4B à injeção não medida. O 9B histórico se absteve na primeira tentativa.
- Stability probe não realizada: não houve rodada principal liberada nem resultado próximo para comparar.

## Verificações e artefatos

- **104 testes relevantes passaram em 1,05 s**: robustez Ask, native, 0.3b, compatibilidade e embeddings.
- Regressões novas: capability com off; capability ausente com omissão; capability sem off bloqueando POST; item reasoning inesperado; tokens positivos sem item reasoning; preservação da exclusão do conteúdo privado. O transporte OpenAI permanece coberto pela suíte de compatibilidade.
- Ruff com ruff.toml passou para provider, testes e runner.
- Alterados: engine/petrus_engine/llm/native.py; engine/tests/test_native_llm.py; scripts/compare_local_models.py; docs/architecture.md; este relatório.

Artefatos separados em `.local-data/arbovirus-retrieval-validation-0.3b/model-comparison-0.3b1d1/`: environment.json, frozen-manifest.json, candidate-model.json, health.json, state-before.json, state-after.json e result.json. Os artefatos anteriores 0.3b.1d permanecem intactos. Não existem test-a.json, queries.json ou stability-probe.json desta etapa porque seus gates não liberaram a execução.

## Decisão

**INCONCLUSIVE.** A negociação foi corrigida e o HTTP passou a funcionar, mas o candidato produziu reasoning real e falhou no gate explícito. A comparação de contrato/citações/abstinência/latência não pôde começar. O 9B continua selecionado.

Não houve tentativa de ajustar prompt, parser, citation syntax, repair, retrieval ou embedding. Não foram executados Gemma, novos modelos ou validação visual. Qualquer investigação adicional para executar esse candidato sem reasoning é uma próxima etapa; não se supõe que a ausência de capability equivalha a execução sem pensamento.
