[English](../validation-0.3b1a-qwen9b-http-fix.md) · **Português (Brasil)**

# PETRUS 0.3b.1a — LM Studio / Qwen 9B provider compatibility

**Diagnóstico posterior de thinking:** [testes A–C com enable_thinking=false](validation-0.3b1a-thinking-diagnostic.md). O campo foi aceito sem rejeição HTTP, mas não desativou reasoning de forma observável; Q1 continuou com content vazio.

**Data: 15 de outubro de 2026. Resultado: causa do HTTP 400 confirmada e corrigida no request; validação Ask interrompida novamente na Q1 por ausência de final content.**

Este documento complementa [a validação 0.3b.1](validation-0.3b1-real-ask-qwen9b.md), lida antes da alteração. Não substitui os resultados históricos daquela rodada.

## Escopo preservado

- Modelo único: `qwen/qwen3.5-9b`, LM Studio local em `http://127.0.0.1:1234/v1`, temperatura 0,1, max_tokens 1600, sem streaming, timeout existente 90 s.
- Índice conferido ao final: 2.342 vetores atuais, zero stale/incompatíveis; sem reindexação.
- Embedding inalterado: `text-embedding-nomic-embed-text-v1.5`, 768 dimensões.
- Banco isolado: `.local-data/arbovirus-retrieval-validation-0.3b/petrus.sqlite3`.
- Corpus exclusivo: `/Users/alexranieri/Library/CloudStorage/OneDrive-Pessoal/Butantan/V-GEN Lab/Arbovirus_evolution`, 10 papers.
- Nenhum PDF alterado, novo processamento GROBID, reindexação, download, outro modelo ou uso do banco normal do app.
- RRF=60, 30 candidatos por fonte, boost=1,15, diversidade existente, exclusão de bibliography/metadata, até oito unidades, contexto serializado até 12.000 caracteres e threshold semântico=0,85 preservados; expansão LLM desligada.

## Corpo do HTTP 400 e causa confirmada

O corpo da falha histórica da 0.3b.1 não pode ser recuperado: o provider anterior o descartou. Nesta etapa, a requisição original da Q1 foi **reproduzida antes da mudança de formato**, com as mesmas seis unidades e o mesmo contexto. O erro sanitizado preservado foi:

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

O Test 2 pequeno reproduziu exatamente a mesma mensagem. **Causa confirmada do HTTP 400: este servidor rejeita `response_format.type=json_object`; aceita como valores de tipo `json_schema` ou `text`.** Isso explica a falha de protocolo. Não explica automaticamente as falhas posteriores de output vazio ou timeout.

Reprodução original Q1: retrieval 1.886 s; tentativa HTTP 9.089 s; total 10.976 s. Nenhuma resposta científica recebida.

## Modelo carregado e orçamento

GET `/api/v0/models` antes/depois e `lms ps --json` confirmaram:

| Campo | Valor |
|---|---|
| Model / instance identifier | `qwen/qwen3.5-9b` |
| Estado | loaded; instância observada processingPrompt/generating durante chamadas |
| Arquitetura | `qwen3_5` |
| Quantização | 4bit |
| Formato/runtime | safetensors / MLX (modelo vlm) |
| Contexto configurado/carregado informado pelas APIs | 4.096 |
| Máximo anunciado pelo modelo | 262.144 |
| Contexto final configurado | 4.096 — sem alteração/reload |

O servidor registra auto-fit interno com alvo efetivo 60.928 nesta instância, embora as APIs anunciem 4.096 como contexto configurado. PETRUS não solicitou esse auto-fit, não carregou contexto 60k e não alterou a configuração do LM Studio. Não equiparar o valor do catálogo ao limite efetivo interno observado.

Q1: seis evidências, contexto serializado 10.681 caracteres; conteúdo total dos messages no teste completo 11600 caracteres; orçamento de saída 1.600 tokens. O servidor mediu **2.555 prompt tokens** no Test 5 e na Q1 corrigida. Input + output budget = 4.155 tokens; o consumo efetivo na Q1 corrigida foi 2.769 tokens. Não foi criado tokenizer. As requisições completas estruturadas receberam HTTP 200, sem erro de context overflow. Portanto não houve base para recarregar o modelo com 8.192/16.384 tokens.

## Matriz mínima Test 1–5

Todos os testes usaram o mesmo modelo, temperatura, max_tokens e timeout existentes. Testes 1–3: mesmos messages pequenos pedindo explicitamente JSON do contrato existente. Testes 4–5: system prompt original Ask, Q1 e as seis evidências originais, conferidas por unit ID e tamanho serializado.

| Test | Input chars* | Formato | HTTP / resultado | Tempo | Final output |
|---|---:|---|---|---:|---|
| 1 — control | 173 | sem response_format | não recebido; timeout | 90.003 s | não recebido |
| 2 — current json_object | 173 | json_object | 400; formato rejeitado | 0.015 s | não recebido |
| 3 — JSON Schema | 173 | json_schema | 200 | 2.623 s | vazio (`content=""`) |
| 4 — full Q1 unstructured | 11600 | sem response_format | não recebido; timeout | 90.004 s | não recebido |
| 5 — full Q1 structured | 11600 | json_schema | 200 | 11.114 s | vazio (`content=""`) |

*Soma dos caracteres dos conteúdos dos messages; não equivale a tokens nem ao tamanho total do request JSON.

Test 2: body sanitizado mostrado acima. Test 3: HTTP 200, finish_reason `stop`, content vazio; 53 prompt tokens, 20 completion tokens, 19 reasoning tokens. Test 5: HTTP 200, finish_reason `stop`, content vazio; 2.555 prompt tokens, 162 completion tokens, 161 reasoning tokens. Foram registrados somente os nomes/tamanhos dos campos de reasoning, sem seu conteúdo. HTTP 200 não foi contado como conformidade JSON/Ask.

Testes 1 e 4 atingiram timeout de leitura a 90 s; não há status de resposta recebido pelo cliente nem final output para avaliar. Não se conclui que free-form funciona, e não se aumenta timeout nesta etapa. Chamadas foram sequenciais no cliente, mas timeout/desconexão não garante cancelamento imediato do trabalho interno do servidor; a matriz não é um benchmark comparativo de velocidade.

## Correção aplicada

Arquivo: `engine/petrus_engine/llm/local.py`.

1. `LLMProviderError(ValueError)` preserva code/status, mensagem útil sanitizada, type/code do servidor quando disponíveis e indicador truncated. `str(error)` continua sendo o código estável `llm_http_N`.
2. Erros HTTP não-2xx leem no máximo 16 KiB + um byte de detecção de truncamento; somente campos diagnósticos são retidos. Mensagem final limitada a 2.048 caracteres e type/code a 128. JSON inválido/truncado com aparência de payload JSON é omitido. Texto passa por limpeza de controles e redaction de fragments dos messages, fontes e tags de reasoning. Nenhum raw error body é persistido.
3. `json_object` foi substituído por `json_schema` explícito com `strict=true`, nome `petrus_ask_response`, propriedades `answer:string`, `insufficient_evidence:boolean`, `limitations:array[string]`, todas obrigatórias e `additionalProperties:false`. Esses são os campos já esperados do modelo, sem EvidenceUnits duplicadas e sem campo citations redundante.
4. A expansão opcional existente usa seu próprio schema `queries:array[string]`; não foi ligada ou executada nesta rodada. Health check segue sem response_format.
5. Validação pós-geração de JSON, IDs e parágrafos permanece intacta. Não há fallback automático para texto livre, reparação de output, extração de reasoning ou mudança de modelo.

O formato novo é **aceito pelo protocolo**, mas a instância não forneceu conteúdo final utilizável nos testes. Esta correção elimina a causa confirmada do 400 sem afirmar compatibilidade end-to-end. Nenhum ajuste de thinking/template foi feito, pois a causa interna de content vazio não foi determinada.

## Q1 após correção no engine

| Campo | Resultado |
|---|---|
| Question | What methods were used for phylogenetic reconstruction? |
| QueryPlan | idioma en; intenção methods; sem expansão |
| HTTP / finish_reason | 200 / stop |
| Retrieval / geração HTTP / total Ask | 0.971 s / 37.177 s / 38.150 s |
| Candidatos / unidades / papers | 30 / 6 / 6 |
| Contexto serializado | 10.681 caracteres |
| Output final do modelo | content vazio; sem JSON final |
| Erro do provider | llm_empty_response |
| Resultado Ask | rejeição + fallback técnico; limitação llm_response_rejected |
| Citações geradas / inválidas | nenhuma resposta gerada; disciplina não avaliável |
| Parágrafos gerados sem citação | não avaliável; zero parágrafos gerados |

Resposta do serviço, não do modelo: “I could not find sufficient evidence in the indexed library to answer this confidently.” Essa mensagem decorre de falha técnica. **Não conta como abstention científica.**

O endpoint retornou reasoning_content separado: somente presença/tamanho (1.109 caracteres) e uso agregado foram registrados. Uso reportado: 2.555 prompt tokens, 214 completion tokens, 213 reasoning tokens. Não foi lido semanticamente ou recuperado JSON desse campo; ele não foi inserido em answer, research event ou relatório.

### Fontes e grounding estrutural

| Evidence | Unit | Paper | Seção | Role | Páginas | Provenance |
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

As seis fontes existem exatamente em current_units e correspondem ao contexto selecionado; paper IDs, textos e páginas coincidem; são membros do corpus, com provenance coordinate e páginas conhecidas, sem bibliography/metadata. As checagens são de estrutura/origem, sem comprovar relevância, entailment ou correção científica. Não houve resposta final do modelo: citações, fontes externas/URLs/DOIs, suporte por parágrafo e idioma de resposta permanecem não avaliáveis. Nenhum score de correctness ou LLM juiz foi usado.

## Parada, Q2–Q9 e UI

Q1 não gerou resposta válida após a correção. A execução foi interrompida conforme a condição explícita da solicitação.

- Q2–Q7: não executadas; comparação EN/PT-BR pendente.
- Q8 (RTS,S): não executada. evidence selected/LLM called/abstained do teste são desconhecidos, não confundidos com o fallback técnico Q1.
- Q9 (prompt injection): não executada; resistência não determinada.
- UI real via `npm run desktop`: não executada, pois dependia de Q1 válida no engine. Não há nova validação nativa de cards/citações/navegação.
- Nenhuma comparação 4B/Gemma iniciada. Nenhuma feature adicional implementada.

## Testes e arquivos

`pytest engine/tests/test_llm_compatibility.py engine/tests/test_03b.py engine/tests/test_embeddings.py -q`: **43 passed in 0.83s**. Ruff dos arquivos Python alterados: **passou**. UI não mudou; TypeScript/ESLint não repetidos.

Novo `engine/tests/test_llm_compatibility.py`: status/body HTTP preservados, error JSON/top-level/text, limite/truncamento, redaction de system/evidence/excertos, controles/thinking, schema Ask serializado, schema da expansão, conteúdo separado de reasoning ignorado, content vazio rejeitado e validação de citações/parágrafos mantida. A suíte anterior permanece presente. Os testes são offline e não substituem os resultados reais da matriz.

Artefatos em `.local-data/arbovirus-retrieval-validation-0.3b/provider-compatibility-0.3b1a/`: `matrix.py`, `matrix.json`, `model-before.json`, `model-after.json`, `instances.json`, `retest_q1.py`, `q1-before-fix.json`, `q1-after-fix.json`, `index-after.json`. Os JSON de resultado guardam fontes sem texto, metadados e diagnósticos, sem reasoning ou prompts completos. Os scripts reconstruem o contexto do banco isolado em memória.

## Conclusão e comparação posterior

Resolvido: diagnóstico HTTP útil e causa do 400 (H — provider/HTTP). Persistem: content vazio em JSON Schema (C — output contract; causa interna não determinada) e timeouts de 90 s sem structured output (B — latência). Não há evidência de memória insuficiente ou overflow de contexto. O Qwen 9B ainda não pode ser considerado baseline Ask validado.

Uma comparação controlada separada com `qwen3.5-4b-mlx` pode ser útil para distinguir comportamento do modelo/runtime e latência, mantendo o schema e o mesmo corpus. Não garante resolver content vazio. Antes de comparar qualidade, exigir final content válido em cada modelo. Nenhuma troca ou comparação automática foi executada.
