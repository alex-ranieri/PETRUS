[English](../validation-0.3b1a-thinking-diagnostic.md) · **Português (Brasil)**

# PETRUS 0.3b.1a — diagnóstico de thinking / Qwen 9B

**Data: 15 de outubro de 2026. Resultado: Test C falhou; nenhuma continuação Q2–Q9 ou UI.** Complemento de [LM Studio / provider compatibility](validation-0.3b1a-qwen9b-http-fix.md).

## Escopo

Modelo único `qwen/qwen3.5-9b`, endpoint `http://127.0.0.1:1234/v1`. Temperatura 0,1; max_tokens 1600; timeout 90 s; sem streaming. Mesmo JSON Schema explícito Ask: answer, insufficient_evidence e limitations. Mesmo banco isolado `.local-data/arbovirus-retrieval-validation-0.3b/petrus.sqlite3`, mesmo corpus Arbovirus_evolution e mesmas seis EvidenceUnits da Q1. Nenhum modelo, embedding, contexto, retrieval, prompt de sistema, schema ou seleção de evidências foi alterado. Nenhum PDF modificado ou reprocessado. Nenhum template global alterado.

Catálogo local nesta rodada: Qwen 9B loaded, arquitetura qwen3_5, MLX 4bit, loaded_context_length=4096, max_context_length=262144. Nenhum reload ou aumento de contexto.

## Testes reais A–C

A e B usaram exatamente os mesmos messages pequenos e o mesmo schema da matriz anterior. O único campo adicional de B foi:

```json
{"chat_template_kwargs":{"enable_thinking":false}}
```

C usou o mesmo campo adicional, o system prompt Ask original, Q1 e o contexto original. Pergunta: “What methods were used for phylogenetic reconstruction?” IDs e tamanho serializado da seleção foram conferidos antes das chamadas.

| Teste | HTTP | Tempo | Prompt tokens | Completion tokens | Reasoning tokens | Content chars | Reasoning chars* | JSON final válido |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A_default | 200 | 11.829 s | 53 | 20 | 19 | 0 | 66 | Não |
| B_thinking_off | 200 | 1.734 s | 53 | 20 | 19 | 0 | 66 | Não |
| C_full_thinking_off | 200 | 27.835 s | 2555 | 175 | 174 | 0 | 805 | Não |

*Somente tamanho/presença do campo, sem conteúdo de reasoning persistido, exibido ou interpretado. Todos terminaram com finish_reason `stop`, sem timeout e sem erro HTTP. Final output de A, B e C: `content=""`.

## Interpretação do passthrough

**Aceito sem rejeição HTTP: sim. Desativação efetiva do thinking: não demonstrada.** B reproduziu exatamente as contagens de A: 53 prompt tokens, 20 completion tokens, 19 reasoning tokens, content vazio. C também manteve reasoning, 174 de 175 completion tokens. A evidência mostra que adicionar chat_template_kwargs neste endpoint não resolveu o comportamento observado. HTTP 200 sozinho não comprova que o campo foi encaminhado/aplicado ao template MLX.

A foi reproduzido nesta rodada e coincidiu com a baseline curta anterior. O menor tempo de B não comprova ganho de performance: ordem, aquecimento/cache e amostra única não foram controlados para benchmark.

A distribuição continua compatível com a hipótese de geração consumida pelo reasoning, mas não prova que um JSON correto apareceu nesse campo. Não houve leitura semântica, parsing, promoção ou fallback de reasoning para answer.

## Test C / Q1

- HTTP 200, finish_reason stop; tentativa de geração 27.835 s.
- Retrieval anterior à matriz: 2.375 s; 30 candidatos, seis EvidenceUnits, seis papers.
- Contexto serializado de evidências: 10.681 caracteres; conteúdo total dos messages: 11.600 caracteres.
- Prompt medido pelo servidor: 2.555 tokens; completion tokens 175, reasoning tokens 174, total tokens 2.730.
- Content final: vazio; JSON válido: não; contrato Ask: não atingido.
- Citações geradas: nenhuma; citações válidas/inválidas de uma resposta: não avaliável. Não tratar 0/0 como sucesso.
- Parágrafos factuais gerados sem citation: não avaliável, pois não houve resposta final.
- As seis unidades continuam existentes e correspondem a paper ID/páginas/papel no banco; todas coordinate, paginadas e fora de bibliography/metadata. Essa conferência de origem não prova entailment ou correção científica.

O Test C é uma chamada diagnóstica direta, não uma resposta científica final do PETRUS. `content` vazio seria rejeitado por llm_empty_response no provider já existente; nenhum resultado de reasoning foi fornecido ao Ask. Não foi emitida abstinência científica para essa falha técnica.

## Via local alternativa inspecionada — sem novas chamadas

Inspeção somente de leitura:

- O `tokenizer_config.json` instalado de `lmstudio-community/Qwen3.5-9B-MLX-4bit` possui condição Jinja `enable_thinking is defined and enable_thinking is false`; nesse ramo fecha o bloco think antes da geração. Isso confirma que o template possui a opção, sem provar que /v1/chat/completions a recebe.
- O SDK oficial já instalado em `.lmstudio/extensions/plugins/lmstudio/rag-v1/node_modules/@lmstudio/sdk/dist/index.d.ts` documenta `promptTemplate` por predição e `LLMJinjaPromptTemplate.template`. A tipagem marca essa interface de template como deprecated/provisória.
- A menor via candidata identificada para uma investigação posterior é usar um template por predição via SDK, vinculando enable_thinking=false ao template original em memória, sem editar globalmente arquivos do modelo. O suporte/efeito específico desta via no runtime MLX atual **não foi validado**. Não é apresentada como correção confirmada, nem foi implementada.

A investigação ativa parou depois de C, conforme solicitado. Nenhum experimento de geração alternativo, flag nova, alteração global de template ou parser de reasoning foi acrescentado.

## Provider e regressões

Nenhuma alteração no código do provider ou nos defaults nesta rodada. A inclusão de llm_enable_thinking e default false era condicionada ao funcionamento real; como o passthrough não demonstrou efeito, essa configuração não foi adicionada. Logo não há suporte efetivo configurado cuja serialização/default possa ser afirmada ou testada como funcional.

Regressões em `engine/tests/test_llm_compatibility.py` reforçadas:

- Mesmo se reasoning_content contiver JSON válido do contrato, content vazio continua produzindo llm_empty_response.
- Se content for JSON inválido e reasoning_content trouxer JSON válido, somente content é devolvido e seu parsing falha. Não há fallback.
- O teste anterior de content final válido separado de reasoning continua presente.

`pytest engine/tests/test_llm_compatibility.py engine/tests/test_03b.py -q`: **30 passed in 0.52s**. Ruff dos arquivos Python relevantes: **passou**. Nenhuma UI alterada; não houve TypeScript/ESLint ou build de pacote.

## Parada e PRAXIS

- Q2–Q9 não retomadas, incluindo PT-BR, insufficient evidence e prompt injection; resultados continuam desconhecidos.
- `npm run desktop` não executado e UI nativa não validada, pois Test C não passou.
- Modelo 4B/Gemma não usado. PRAXIS não modificado.
- Não foi encontrado caminho PRAXIS nos arquivos do projeto PETRUS consultados; nenhum disco foi varrido para localizá-lo e seu código/payload não foi inspecionado.
- Comparação apenas conceitual: se PRAXIS usa geração textual sem response_format/json_schema, exerce uma rota distinta da geração estruturada PETRUS e pode se comportar de modo diferente. Isso é hipótese condicional; não comprova que PRAXIS desliga thinking nem que JSON Schema seja a única causa.

## Artefatos

`.local-data/arbovirus-retrieval-validation-0.3b/thinking-diagnostic-0.3b1a/`: `matrix.py`, `matrix.json`, `model-before.json`, `evidence-manifest.json`. Os resultados guardam metadados/contagens e apenas content final (vazio), sem reasoning ou textos de artigos. O runner reconstrói as evidências em memória a partir do banco isolado. O manifesto contém somente metadados das seis fontes.
