[English](../validation-0.3b-arbovirus.md) · **Português (Brasil)**

# Validação PETRUS 0.3b — Arbovirus_evolution

**Data: 15 de outubro de 2026.** Validação estrutural local; sem ground truth, sem tabela manual solicitada, sem accuracy inventada. Baseline: [validação 0.3a](retrieval-validation-arbovirus-0.3a.md).

## Escopo e isolamento

Corpus exclusivo: os mesmos 10 PDFs de `/Users/alexranieri/Library/CloudStorage/OneDrive-Pessoal/Butantan/V-GEN Lab/Arbovirus_evolution`. Banco 0.3b criado por backup SQLite em `.local-data/arbovirus-retrieval-validation-0.3b/`. O banco 0.3a, o banco normal do aplicativo e os PDFs não foram alterados. Não houve novo parsing GROBID, download de artigos/modelos ou processamento do restante da V-GEN Lab. Somente serviços locais de embeddings foram usados nesta rodada real.

## Implementação

- evidence_role por estrutura/ancestrais, sem LLM. Bibliografia/metadados ficam fora do retrieval padrão; `include_bibliography=true` permite descoberta. Parágrafos científicos com citações permanecem disponíveis.
- Subdivisão sem overlap, priorizando parágrafos/sentenças e fallback por caracteres. IDs filhos/offsets preservam paper, section, source span, páginas e provenance. Não há texto duplicado em nova tabela.
- Finalização: boost transparente 1,15 por intenção methods/results/limitations, seguido por diversidade round-robin (um por paper, depois até dois, preenchimento excedente se necessário). RRF=60, 30 candidatos por fonte e thresholds 0.2.2 preservados.
- QueryPlan original/normalizado/idioma/intenção; expansão inglesa local opcional e desligada por padrão, fundida com a query original. Idioma é heurístico EN/PT, sem promessa de detecção universal.
- Ask usa até oito fontes, prefere provenance paginada, deduplica fontes muito semelhantes por Jaccard de shingles de quatro palavras (≥0,92) e limita contexto serializado a 12.000 caracteres. Prompt evidence-only; valida JSON, IDs existentes e citações por parágrafo. Rejeita saída inválida em vez de apresentar referências inventadas.
- UI Ask/cards, clique em [E#], página desconhecida, navegação para artigo/biblioteca, Settings separados e gravação opcional em sessão ativa. Uso de JSON existente em research_events, com snapshot e timestamp.
- Nenhuma migration criada: papéis/children são projeções; embedding_index e research_events existentes bastam. Nenhuma dependência nova.

## BEFORE vs AFTER — Top-5 híbrido, 15 queries

Contagens representam ocorrências de unidades, com repetição entre queries. Antes: resultados registrados da rodada estruturada 0.3a. Depois: mesmas queries, corpus e modelo; sem avaliação de relevância humana.

| Diagnóstico | BEFORE 0.3a | AFTER 0.3b |
|---|---:|---:|
| Hits vinculados a referências/citações isoladas | 34/75 | 0/75 |
| Média de papers únicos no Top-5 | 2.07 | 4.60 |
| Hits com supports_paginated_evidence | 66/75 | 59/75 |
| Hits em Methods/descendentes nas 4 queries de método | 2/20 | 8/20 |
| Unidades acima de 6.000 caracteres sem subdivisão | 11 | 0 |
| Unidades brutas / unidades projetadas | 2326 | 2342 |
| Vetores atuais | 2315 | 2342 |

A redução de hits paginados não demonstra piora: antes havia bibliografia com coordenadas. A versão atual não atribui páginas a section_only. Mudanças combinadas alteram a composição; os números não isolam causalmente o efeito de cada intervenção nem demonstram melhor relevância científica.

### Diversidade e intenção, por query

| Query | Papers únicos antes → depois | Paginated H depois | Methods H depois |
|---|---|---:|---:|
| arbovirus evolution | 1 → 4 | 5 | 0 |
| recombination in arboviruses | 3 → 4 | 4 | 0 |
| phylogenetic analysis of arboviruses | 1 → 4 | 4 | 1 |
| genomic surveillance | 1 → 5 | 5 | 0 |
| evolutionary dynamics of arboviruses | 1 → 4 | 5 | 0 |
| evolução de arbovírus | 3 → 4 | 4 | 0 |
| recombinação em arbovírus | 4 → 5 | 4 | 0 |
| análise filogenética | 4 → 5 | 5 | 0 |
| vigilância genômica | 2 → 5 | 4 | 0 |
| dinâmica evolutiva dos arbovírus | 3 → 4 | 5 | 0 |
| phylogenetic reconstruction method | 1 → 5 | 3 | 2 |
| método de reconstrução filogenética | 3 → 5 | 0 | 4 |
| software used for phylogenetic analysis | 1 → 5 | 4 | 0 |
| software utilizado para análise filogenética | 2 → 5 | 3 | 2 |
| phylogenetic analysis | 1 → 5 | 4 | 0 |

Provenance AFTER: `coordinate`=59, `section_only`=16.

PT-BR: as sete queries continuam sem hits lexicais com a query original; semantic/hybrid retornaram Top-5 em 7/7. Expansão via LLM não foi ativada na validação real por falta de seleção de um modelo de chat. O suporte de expansão/RRF foi testado offline. Não se afirma equivalência de ranking EN/PT ou correção cross-lingual.

## Embeddings e invalidação

Provider `lmstudio:127.0.0.1:1234/v1`, modelo exato `text-embedding-nomic-embed-text-v1.5`, dimensão 768. Limite 6.000 caracteres. As 11 unidades grandes geraram **27 children**, sem perda textual; 2.342 unidades finais, zero oversized e zero erros de embedding.
Foram invalidados 2315 vetores antigos na cópia (novo papel/particionamento participa do fingerprint) e criados 2342 vetores compatíveis. Saldo de +27 vetores frente à 0.3a; não confundir esse saldo com as 2.342 chamadas/unidades reembeddadas. Envio em lotes de até 16 pela implementação HTTP existente. Bibliografia continua indexável para descoberta e grafo de citações, mas é filtrada antes de selecionar candidatos para Ask.
Tempo de indexação: **52.458 s**; queries comparativas: **5.168 s**. Cache de P1: 123 reutilizadas, 0 embeddings novos, sem warnings. Status final: 2342 current, 0 stale/incompatíveis.

## Semantic graph

**24 arestas SEMANTIC_SIMILARITY**, threshold **0.85** fixado antes da medição, sem ajuste ao corpus. Centroides: média de até 12 vetores unitários atuais por paper, normalizada; prioridade abstract/body/methods/results/discussion/conclusion. Bibliografia/metadados excluídos. Blocos de 128, até seis vizinhos por paper e 300 arestas; filtro OFF por padrão. Similaridade não significa concordância ou evidência científica.

## LLM e Ask real

Provider implementado: OpenAICompatibleLLMProvider / LM Studio; endpoint `http://127.0.0.1:1234/v1`, temperature padrão 0,1, provider padrão none. Health check testa modelo e resposta mínima sem papers. Somente loopback, sem tools/redirects/proxy.

O catálogo real anunciou três modelos de geração disponíveis:

- `google/gemma-4-e2b`
- `qwen3.5-4b-mlx`
- `qwen/qwen3.5-9b`

**Nenhum modelo de chat foi escolhido automaticamente.** Como não havia exatamente um candidato inequívoco, a geração real e o health check de geração permanecem pendentes de seleção em Settings → AI. Não houve envio do contexto científico a um chat model nesta validação. A geração e suas falhas foram testadas com FakeLLMProvider; não são apresentadas como validação de um modelo real.

As cinco perguntas solicitadas passaram pelo pipeline real de retrieval/seleção; geração desabilitada:

| Pergunta | Fontes selecionadas | Contexto serializado | Geração |
|---|---:|---:|---|
| What methods were used for phylogenetic reconstruction? | 6 | 10681 caracteres | Não executada: modelo não selecionado |
| Qual método foi utilizado para reconstrução filogenética? | 8 | 8798 caracteres | Não executada: modelo não selecionado |
| What evidence of arbovirus adaptation is present in these papers? | 7 | 10896 caracteres | Não executada: modelo não selecionado |
| O que estes artigos relatam sobre adaptação de arbovírus? | 8 | 11013 caracteres | Não executada: modelo não selecionado |
| Which papers discuss genomic surveillance? | 8 | 8211 caracteres | Não executada: modelo não selecionado |

Diagnósticos: **37 evidence IDs**, todos existentes; 37 papers/ocorrências válidos, 37 páginas válidas em 37 fontes com página; **0 fontes bibliography/metadata**. Contexto máximo observado 11013 caracteres. Nenhuma citação gerada real existe para validar (0 válidas/0 inválidas, pois não houve geração). Não interpretar isso como taxa de sucesso.
Sem fontes elegíveis, o serviço não chama LLM e usa mensagem de insuficiência EN/PT. Sem modelo configurado, informa a seleção necessária e pode mostrar as fontes recuperadas. Timeout, JSON malformado, citação desconhecida ou parágrafo sem citação resultam em abstinência/rejeição com código estruturado, nunca em reparação inventada.

## Testes e limites da verificação

- Engine: **98 testes passaram na suíte completa final em 5,34 s**. Inclui regressão HTTP sintética local, papéis/filtros, diversidade, boost, subdivisão/offsets, stale/idempotência, QueryPlan, RRF com expansão, centroides, citações válidas/inválidas, abstinência, timeout/JSON e snapshot de sessão.
- Playwright: **2 testes focados EN/PT passaram**, cobrindo tela/pergunta/resposta, cards, fonte original, página ausente, clique/destaque e filtro semântico OFF/inspector. IPC/LLM são simulados nesses testes; não comprovam geração nativa real.
- Ruff, ESLint, TypeScript e build frontend passaram. Não houve build Tauri/novo .app nem validação nativa de chat. O `.app` antigo continua com o engine anteriormente empacotado; os novos fluxos estão no código de desenvolvimento.
- Validar IDs e páginas verifica correspondência de origem, **não entailment, completude ou correção de cada frase**. Isso não é solucionado apenas pelo prompt. Os testes não recebem ground truth de artigos reais.
- Classificação por TEI/headings e intenção/idioma são heurísticas transparentes. Alguns artigos podem não ter seção Methods, especialmente reviews; oito hits rotulados Methods não significam oito respostas corretas.
- O modelo de embedding é Nomic Q4_K_M, não BGE-M3. O limite em caracteres não substitui tokenizer nem audita eventual tratamento interno de contexto do servidor.
- Ask é uma operação síncrona do engine com UI assíncrona, sem streaming/cancelamento/fila nova. Abertura direta de página depende do contrato do leitor padrão; o app informa a limitação.
- Não foram implementados agentes externos, OpenAlex, downloads, reranker neural ou Report Builder.

## Arquivos alterados

**Engine retrieval**: `engine/petrus_engine/rag/evidence.py`, `engine/petrus_engine/rag/index.py`, `engine/petrus_engine/rag/retrieval.py`, `engine/petrus_engine/rag/contracts.py`, `engine/petrus_engine/rag/query.py (novo)`, `engine/petrus_engine/rag/ask.py (novo)`.
**Providers e graph**: `engine/petrus_engine/llm/__init__.py`, `engine/petrus_engine/llm/local.py (novo)`, `engine/petrus_engine/graph/relatedness.py`, `engine/petrus_engine/graph/semantic.py (novo)`, `engine/petrus_engine/service.py`, `src-tauri/src/main.rs`.
**UI**: `app/src/components/Ask.tsx (novo)`, `app/src/components/AISettings.tsx (novo)`, `app/src/components/Settings.tsx`, `app/src/components/Graph.tsx`, `app/src/App.tsx`, `app/src/services/api.ts`, `app/src/styles/app.css`, `app/src/i18n/locales/en.json`, `app/src/i18n/locales/pt-BR.json`.
**Testes e docs**: `engine/tests/test_03b.py (novo)`, `engine/tests/test_embeddings.py`, `tests/ask-03b.spec.mjs (novo)`, `scripts/evaluate_retrieval.py`, `docs/architecture.md`, `README.md`, `docs/validation-0.3b-arbovirus.md (novo)`.

## Artefatos locais e próximos passos

Outputs em `.local-data/arbovirus-retrieval-validation-0.3b/`: summary.json, before/after-metrics.json, query-results.json/txt, semantic-edges.json, ask-diagnostics.json e ask-checks.json. Contêm diagnóstico e, nos resultados detalhados, excerpts curtos; não há texto integral dos artigos neste relatório. Baseline 0.3a preservada.

Próximo passo operacional: selecionar explicitamente um dos modelos locais em Settings → AI e executar Check connection; então validar uma pequena geração Ask com as fontes já disponíveis. Não se exige avaliação humana/tabela agora, nem se avança para agentes ou serviços externos.
