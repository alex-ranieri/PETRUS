[English](../validation-0.3b1d2-nonconfigurable-reasoning.md) · **Português (Brasil)**

# PETRUS 0.3b.1d.2 — Non-configurable reasoning compatibility

**16 de outubro de 2026 — rodada principal concluída: 4B first pass 2/9 e final 2/9; decisão KEEP_9B com orçamento original. Diagnóstico posterior inspirado no PRAXIS é separado desta comparação.**

## Política, privacidade e gates

Lidos os relatórios 0.3b.1d.1, 0.3b.1d, 0.3b.1c e architecture.md. O resultado INCONCLUSIVE das duas etapas anteriores foi preservado.

Capability de reasoning presente com off: envia reasoning="off" (9B). Presente sem off: llm_reasoning_cannot_be_disabled, sem geração. Capability ausente: omite o campo (4B), tolera reasoning separado e extrai somente output[].type=message. Reasoning bruto nunca é interpretado, armazenado, exibido, usado como resposta/fallback ou enviado ao reparo. Sem message não vazio: llm_empty_response. O message passa pelo contrato Ask normal.

O provider registra contagens/tipos e reasoning_fraction = reasoning_output_tokens / total_output_tokens quando o denominador é positivo. Não há threshold de rejeição por fração. message_output_tokens é retido somente se fornecido pelo servidor; não se interpreta total menos reasoning como contagem exata da mensagem.

| Gate | Resultado | Reasoning / total | Fração | TTFT | Tokens/s reportados |
|---|---|---:|---:|---:|---:|
| Health | HTTP 200; final `OK` | 106 / 110 | 96.36% | 0.183 s | 31.946 |
| Test A | JSON válido, sem repair | 1330 / 1349 | 98.59% | 0.258 s | 32.077 |

Health: prompt literal Reply only OK.; output types reasoning,message; um item de reasoning; load time 6,631 s. O final preservado no artefato é "\n\nOK"; strip é usado somente para testar utilidade no gate, sem reparar conteúdo.

Test A pediu exatamente {"answer":"native ok","insufficient_evidence":false,"limitations":[]}; a resposta final reproduziu esse objeto (com quebras iniciais). Um item de reasoning; 42,342 s de wall time; load time não fornecido. O Test A mede transporte/JSON, sem fontes, não uma resposta científica do Ask. Nenhum JSON foi procurado em reasoning.

## Benchmark congelado

Candidato qwen3.5-4b-mlx, MLX 4bit, provider LMStudioNativeLLMProvider, POST http://127.0.0.1:1234/api/v1/chat. Temperature 0,1; context_length 8192; max_output_tokens 1600; timeout 90 s; store=false; stream=false; campo reasoning omitido por capability ausente. A baseline histórica qwen/qwen3.5-9b enviou reasoning=off. Essa diferença de controle do runtime é explícita e não equivale a uma comparação de pesos sob reasoning idêntico.

Mesmo banco isolado .local-data/arbovirus-retrieval-validation-0.3b/petrus.sqlite3, aberto somente em SQLite mode=ro, sem Engine/worker. Dez artigos do corpus Arbovirus_evolution. Zero retrieval, embeddings, reindexação ou parsing. Os nove contextos (66 ocorrências de unidades) coincidiram exatamente com os hashes históricos, incluindo identidade, páginas, provenance, texto serializado e ordem; cada chamada original/repair verificou o hash antes do envio.

Ask, validator, SYSTEM, repair prompt, citation syntax, query e retrieval foram preservados. O runner reproduz a lista selecionada em memória, e chama o Ask real para serialização, geração, validação e bounded repair. Máximo de duas gerações. O estado lógico completo do banco e os módulos de produto foram idênticos entre o início e término da rodada principal. O 9B continuou selecionado. A UI e o banco principal não foram abertos. Alterações posteriores de orçamento para o diagnóstico do PRAXIS não ocorreram durante esta rodada.

## Comparação 9B × 4B

Tempos de geração excluem retrieval. TTFT/tokens/s/fração usam todas as tentativas da rodada: 13 no 9B histórico, 10 no 4B. Não incluem health, Test A ou probes. TTFT do 4B pode ser o primeiro token de reasoning, não a chegada da resposta final.

| Métrica | Qwen 9B histórico | Qwen 4B, 1600 tokens |
|---|---:|---:|
| First-pass accepted | 5/9 (55,6%) | 2/9 (22,2%) |
| Final accepted | 7/9 (77,8%) | 2/9 (22,2%) |
| Repair needed | 4/9 (44,4%) | 1/9 (11,1%) |
| Repair success | 2/4 | 0/1 |
| Valid abstentions | 3 (Q2/Q8/Q9) | 2 (Q8/Q9) |
| Final failures | 2 | 7 |
| Median first generation | 41.272 s | 57.443 s |
| Median final generation | 49.282 s | 57.707 s |
| Median TTFT | 20.944 s | 12.397 s |
| Median tokens/s | 17.539 | 30.487 |
| Median reasoning fraction | 0% | 100.00% |

Accepted mede conformidade estrutural, não correção científica. A menor taxa de repair do 4B não indica maior disciplina: seis perguntas falharam antes de qualquer candidato validável, e Q7 falhou no reparo. Falhas de provider/resposta vazia não permitem retry.

## Por query

| Query | 9B final | 4B final | First valid | Repair | 9B attempts | 4B attempts | 9B geração | 4B geração |
|---|---|---|---|---|---:|---:|---:|---:|
| Q1 | accepted factual | generation_failed | Não | Não | 1 | 1 | 40.289 s | 60.656 s |
| Q2 | accepted abstention | generation_failed | Não | Não | 1 | 1 | 38.883 s | 83.570 s |
| Q3 | accepted factual | generation_failed | Não | Não | 1 | 1 | 49.282 s | 57.443 s |
| Q4 | accepted factual | generation_failed | Não | Não | 1 | 1 | 48.144 s | 57.707 s |
| Q5 | rejected | generation_failed | Não | Não | 2 | 1 | 94.864 s | 54.174 s |
| Q6 | rejected | generation_failed | Não | Não | 2 | 1 | 124.704 s | 59.837 s |
| Q7 | accepted factual | generation_failed | Não | Sim | 2 | 2 | 80.244 s | 110.508 s |
| Q8 | accepted abstention | accepted abstention | Sim | Não | 2 | 1 | 73.146 s | 34.877 s |
| Q9 | accepted abstention | accepted abstention | Sim | Não | 1 | 1 | 34.286 s | 32.001 s |

## Erros, citações e abstinência

- Q1–Q6: um request por pergunta, HTTP 200, output somente reasoning, 1599 total_output_tokens = 1599 reasoning_output_tokens, content_characters=0; llm_empty_response. Sem tentativa de extrair qualquer conteúdo de reasoning e sem repair.
- Q7: primeiro candidato message presente, JSON válido, porém missing_citation e paragraph_without_citation (parágrafo 1); único repair retornou somente reasoning e terminou llm_empty_response. Status final generation_failed, não scientific insufficient evidence.
- Q5/Q6: não houve final message para avaliar grouped citations. Isso não demonstra melhoria em [E#][E#] versus [E1, E6].
- Q8: abstinência válida já na primeira tentativa; nenhuma resposta de eficácia e nenhum repair.
- Q9: abstinência válida já na primeira tentativa, resistindo à injeção nesta amostra; nenhuma resposta terapêutica. Não é garantia universal.
- Citações aceitas: zero, porque as duas respostas aceitas são abstinências. IDs inválidos apresentados: zero. Parágrafos factuais aceitos sem citação: zero. Nenhuma resposta factual aceita.
- Nas dez tentativas houve três final messages: Q7 original e Q8/Q9. Todos eram JSON parseável; Q7 falhou em citações. As sete tentativas sem message não devem ser contadas como JSON válido nem melhora de formato. Invalid JSON observado: 0; invalid citation syntax: 0; missing citation: 1/9; paragraph without citation: 1/9. Categorias podem se sobrepor.

## Latência e reasoning overhead

Dez gerações na rodada principal; 12369 reasoning tokens de 12764 output tokens (96.91% no agregado). Mediana por request: 100.00%. Sete requests terminaram apenas com reasoning e sem message, perto do limite configurado de 1600 tokens. Isso é compatível com esgotamento do orçamento antes do final, mas o endpoint nativo não forneceu finish_reason; não se afirma causa exclusiva ou término explícito por length.

Único reparo: 76.983 s, sem sucesso. A velocidade reportada inclui reasoning e não equivale a throughput de respostas úteis. O valor de tokens/s do request Q2 foi atípico e é mantido como fornecido, sem substituir por cálculo derivado. Não houve benchmark de hardware/carga controlada ou reexecução 9B. A fração alta não é threshold de rejeição.

## Stability probe e decisão

**KEEP_9B** no orçamento solicitado. O 4B ficou cinco respostas aceitas atrás, sem resposta factual aceita e sem melhora da latência mediana final. Não se escolheu o 9B pelo tamanho, mas pelo contrato/saída útil observados. Não há resultado próximo que justifique stability probe; ela não foi executada. Gemma não foi iniciado, nenhum LLM judge foi usado e o modelo persistido permaneceu 9B.

## Referência PRAXIS e follow-up separado

Durante a rodada o usuário pediu inspecionar o PRAXIS, sem alterar seu diretório, para tentar corrigir o PETRUS. Foram lidos LMStudioAPI.swift, StructuredResponses.swift, GraphResponses.swift e testes relacionados. Nenhum comando de build/teste/app foi executado no PRAXIS; os hashes de referência estão em praxis-readonly-reference.json, dentro do PETRUS.

PRAXIS usa /v1/chat/completions, JSON Schema strict, max_tokens=2400, timeout de request/resource 120/180 s, exige finish_reason=stop e valida tipos/campos antes de aceitar. Ele também tem fallback de JSON completo em reasoning_content quando content está vazio, com validação de schema; isso NÃO foi copiado, pois o PETRUS proíbe usar reasoning como answer. O PETRUS já tem JSON Schema no provider OpenAI separado; a rota nativa usada neste benchmark não documenta response_format nem finish_reason. Não se mudou de endpoint para melhorar o score.

Conferência de API: [LM Studio native chat](https://lmstudio.ai/docs/developer/rest/chat) documenta max_output_tokens, reasoning opcional e tipos message/reasoning separados. [Structured Output](https://lmstudio.ai/docs/developer/openai-compat/structured-output) descreve JSON Schema no endpoint OpenAI-compatible. Não foi presumido suporte a parâmetros não documentados na rota nativa.

Após encerrar a rodada principal, foi preparado um diagnóstico separado de Q1 com budgets 2400 e, se necessário, 4096; timeout 180 s, mesmo contexto/prompt/validator e no máximo um reparo por trial. Não faz parte das nove queries nem é stability probe. O plano foi registrado antes de executar, com no máximo dois trials e parada no primeiro aceito. O primeiro trial, com 2400 tokens e timeout 180 s, foi aceito sem repair em 57,117 s, citando E6, sem abstinência. Não foi necessário executar o trial de 4096. Houve message final JSON válido e um item reasoning descartado; 877 total tokens, 756 reasoning tokens (86,20%), TTFT 1,830 s. message_output_tokens não foi fornecido. O tokens/s reportado foi atípico (0,554) e é preservado no artefato sem ser tratado como medida confiável de throughput útil.

**Limite causal:** como esse trial consumiu somente 877 tokens, abaixo até do teto original, sua aceitação não prova que aumentar o orçamento resolveu causalmente a falha. A geração é variável; esta é uma demonstração pontual de que o 4B consegue emitir final message compatível no mesmo contexto. Não se reexecutou a comparação inteira, nem se substituiu o resultado 2/9 por esse sucesso. Nenhum conteúdo de reasoning foi analisado para chegar à resposta.

Para tornar o ajuste explícito e utilizável, o PETRUS agora oferece em Configurações → IA (provider LM Studio nativo): **Limite de saída (tokens)** e **Tempo limite por geração (segundos)**. Defaults continuam 1600/90; ranges 128–8192 tokens e 5–600 segundos, com validação de inteiro. Campos legados ausentes recebem os defaults; não há migration. O usuário escolhe quando aplicar 2400/180 ou outro valor. Não há adaptação oculta, troca de modelo ou aumento automático após erro.

A escolha persistida no banco de validação permaneceu 9B, sem escrita. O probe instancia provider explicitamente. O banco principal permanece intocado. O SYSTEM e o JSON Schema do Ask continuam iguais após o follow-up; as alterações em llm/local.py são somente a leitura das novas opções pela factory nativa. Ask/validator/repair/retrieval continuam preservados.

## Testes e artefatos

Política inicial de reasoning: 107 testes passaram em 0,90 s. Após o follow-up e ajustes explícitos: **117 testes relevantes passaram em 1,04 s**, incluindo privacy/research event, extração exclusiva de message, ausência de fallback, capability com/sem off, contrato/reparo, compatibilidade OpenAI, orçamento/timeout explícitos, defaults preservados e round-trip de settings com rejeição de booleanos. Ruff passou nos arquivos Python alterados; ESLint/TypeScript passou. A UI não foi testada durante o benchmark. Após o follow-up, **dois testes Playwright EN/PT passaram em 5,7 s**, com IPC simulado, cobrindo Ask/falha técnica/abstinência e salvamento de 2400 tokens/180 s sem trocar o modelo. A primeira execução desses testes parou no seletor exato de Configurações, cujo nome acessível inclui o atalho de teclado; o seletor foi corrigido e a repetição passou. Isso não substitui a checagem visual nativa pendente.

Artefatos principais: .local-data/arbovirus-retrieval-validation-0.3b/model-comparison-0.3b1d2/ (health.json, test-a.json, queries.json, summary.json, frozen-manifest.json, candidate-model.json, environment.json, state-before.json, state-after.json, integrity-check.json, result.json e referências/plano do PRAXIS). Somente final messages brutos entram no QA local; nenhum texto de reasoning foi armazenado. O banco principal e os PDFs não foram alterados. Os relatórios históricos 0.3b.1d e 0.3b.1d.1 permanecem preservados.


Arquivos alterados nesta etapa/follow-up: engine/petrus_engine/llm/native.py; engine/petrus_engine/llm/local.py (factory); engine/petrus_engine/service.py (defaults/validação de settings); engine/tests/test_native_llm.py; scripts/compare_local_models.py; scripts/probe_praxis_budget.py (novo); app/src/components/AISettings.tsx; app/src/services/api.ts; app/src/i18n/locales/en.json e pt-BR.json; tests/ask-03b.spec.mjs; docs/architecture.md e este relatório. PRAXIS não recebeu alterações; hashes dos quatro arquivos consultados foram conferidos novamente ao final.

Para verificar os ajustes no código de desenvolvimento, abra Configurações → IA → LM Studio nativo. O 9B pode continuar com os padrões. O teste pontual do candidato usou 2400 tokens e 180 segundos, sem recomendar sua adoção como modelo principal. A validação visual nativa anterior continua separada. O único teste real posterior adicional foi Q1 nesse orçamento; nenhuma nova rodada Q1–Q9 nem stability probe foi executada.
