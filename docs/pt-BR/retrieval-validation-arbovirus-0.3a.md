[English](../retrieval-validation-arbovirus-0.3a.md) · **Português (Brasil)**

# Validação real de retrieval — Arbovirus_evolution / PETRUS 0.3a

Data: **15 de outubro de 2026**. Rodada final estruturada, após o usuário iniciar o GROBID. Objetivo: avaliar retrieval, sem gerar respostas, sínteses ou juízos automáticos de relevância.

## Escopo e isolamento

Pasta única: `/Users/alexranieri/Library/CloudStorage/OneDrive-Pessoal/Butantan/V-GEN Lab/Arbovirus_evolution`.
Banco separado: `.local-data/arbovirus-retrieval-validation/petrus.sqlite3`, com `PETRUS_DATA_DIR` definido somente nos processos de validação. Apenas essa biblioteca foi cadastrada; nenhum banco principal, PDF ou diretório de pesquisa foi alterado. PDFs foram lidos, sem forçar downloads cloud-only.

Inventário antes do parsing: **10 PDFs, 10 locais, 10 conteúdos únicos por SHA-256, 0 duplicados, 0 cloud-only/indisponíveis**, 26.376.504 bytes (~25,16 MiB). Os 14 testes existentes de embeddings/retrieval passaram em 0,90 s antes da validação real.

## Parsing e proveniência

Inicialmente GROBID retornou conexão recusada em `127.0.0.1:8070`; foi feita uma baseline pypdf. Após o usuário iniciar o serviço, o health check retornou available e os mesmos dez artigos foram processados. Não houve instalação, recompilação ou início automático do GROBID.

| Medida | Rodada final |
|---|---:|
| Papers | 10 |
| Structured sem avisos | 0 |
| Structured com avisos | 10 |
| Tentativas científicas com falha | 0 |
| Seções | 180 |
| Referências | 889 |
| Source spans | 2255 |
| Spans coordinate | 2252 |
| Spans exact alignment | 3 |
| EvidenceUnits coordinate | 2252 |
| EvidenceUnits exact_page_alignment | 3 |
| EvidenceUnits section_only | 71 |
| EvidenceUnits basic_page_text | 0 |

Os dez artigos registraram `page_mapping_missing` e `page_mapping_partial`. Falta de mapeamento não foi convertida em página presumida. Texto básico por página continua preservado no banco, mas, havendo estrutura, a projeção usa spans/seções.

## Embeddings reais

Provider: `lmstudio:127.0.0.1:1234/v1`. Endpoint: `http://127.0.0.1:1234/v1`. Modelo exato: **`text-embedding-nomic-embed-text-v1.5`**, dimensão **768**, GGUF Q4_K_M. O endpoint `/api/v0/models` identificou esse modelo como embeddings; BGE-M3 não estava listado. Os outros modelos anunciados não foram usados. Não houve download de modelo nem geração LLM.
A única chamada pequena inicial usou “Arbovirus evolution.”: 1 vetor finito, dimensão 768 e resposta compatível. O servidor estava ativo; a primeira chamada levou 19,647 s, incluindo o possível carregamento inicial do modelo. Não se afirma que esse tempo mede exclusivamente inferência.

| Medida | Resultado |
|---|---:|
| EvidenceUnits totais | 2326 |
| Elegíveis (≤6.000 caracteres) | 2315 |
| Indexadas na rodada | 2315 |
| Cache reutilizado na primeira indexação estruturada | 0 |
| Puladas por tamanho | 11 |
| Puladas por erro | 0 |
| Vetores atuais no SQLite | 2315 |
| Vetores stale da baseline removidos | 90 |
| Payload float32 | 7,111,680 bytes |
| Tabela embedding_index via dbstat (sem índices auxiliares) | 9,506,816 bytes |
| Lote máximo / chamadas de indexação | 16 / 145 |

Nenhuma unidade acima de 6.000 caracteres foi cortada. O limite é de caracteres, não um tokenizer. O endpoint anunciou contexto máximo de 2.048 tokens; nesta rodada não houve rejeições por contexto, mas não foi auditado eventual tratamento interno de truncamento pelo servidor. O PETRUS não truncou os inputs aceitos. Não foram adicionados prefixos/task instructions específicos do modelo; este é o baseline do provider atual.

## Tempos e cache

| Etapa | Tempo |
|---|---:|
| Catalogação pypdf | 8.813 s |
| Parsing GROBID dos 10 artigos | 55.501 s |
| Indexação estruturada total | 110.055 s |
| Média aproximada por unidade indexada | 0.0475 s |
| Teste de cache | 0.185 s |
| 15 queries × 3 modos | 8.299 s |

Cache: paper P1, 120 unidades solicitadas, 117 elegíveis, **117 cached, 0 novos embeddings**, 3 avisos de tamanho. Hash/provider/model evitaram nova inferência nas unidades elegíveis.

## Identificação dos papers

IDs são locais a este banco, não identificadores globais. Títulos/metadados abaixo são os extraídos, sem validação bibliográfica externa.

| ID | Título | Vetores |
|---|---|---:|
| P1 | Arboviral Diseases in a Changing World: Evolutionary Dynamics, Host-Vector Interactions, and Novel Control Strategies | 117 |
| P2 | Evolution and adaptation of dengue virus in response to high-temperature passaging in mosquito cells | 235 |
| P3 | Genome-Wide Patterns of Intrahuman Dengue Virus Diversity Reveal Associations with Viral Phylogenetic Clade and Interhost Diversity | 229 |
| P4 | Global Transmission and Evolution of Chikungunya Virus: Origins, Adaptive Mutations, and Intercontinental Spread of the Three Genotypes | 157 |
| P5 | Global epidemiology and evolutionary dynamics of arboviruses: A systematic review of surveillance, control strategies, and emerging threats | 295 |
| P6 | Host-adaptive mutations in Chikungunya virus genome | 221 |
| P7 | Human movement and environmental barriers shape the emergence of dengue | 208 |
| P8 | Insights into Arbovirus Evolution and Adaptation from Experimental Studies | 365 |
| P9 | Intrahost population dynamics of chikungunya virus in humans and naturally infected Aedes mosquitoes reveal transmission-driven diversity | 255 |
| P10 | Strengthening arbovirus surveillance: bridging gaps for global health preparedness | 233 |

## Comparação das 15 queries

Cada modo registrou Top 5. A tabela resume Top 1; as ordens completas estão na tabela seguinte e os trechos originais curtos ficam somente nos arquivos locais. `top5_overlap` = interseções de unit IDs (L∩S / L∩H / S∩H), sem inferência de accuracy. `paginated_hits` usa a política `supports_paginated_evidence`, não apenas existência de número de página.

| Query | lexical_top1 | semantic_top1 | hybrid_top1 | top5_overlap L/S · L/H · S/H | paginated_hits H |
|---|---|---|---|---|---:|
| arbovirus evolution | P8 | P5 | P8 | 0 / 2 / 0 | 3 |
| recombination in arboviruses | P1 | P5 | P1 | 0 / 3 / 2 | 3 |
| phylogenetic analysis of arboviruses | P5 | P5 | P5 | 0 / 3 / 1 | 5 |
| genomic surveillance | P10 | P4 | P10 | 0 / 0 / 2 | 5 |
| evolutionary dynamics of arboviruses | P5 | P5 | P5 | 0 / 1 / 2 | 5 |
| evolução de arbovírus | — | P5 | P5 | 0 / 0 / 5 | 5 |
| recombinação em arbovírus | — | P5 | P5 | 0 / 0 / 5 | 5 |
| análise filogenética | — | P1 | P1 | 0 / 0 / 5 | 5 |
| vigilância genômica | — | P4 | P4 | 0 / 0 / 5 | 5 |
| dinâmica evolutiva dos arbovírus | — | P5 | P5 | 0 / 0 / 5 | 5 |
| phylogenetic reconstruction method | P4 | P7 | P4 | 1 / 2 / 2 | 4 |
| método de reconstrução filogenética | — | P4 | P4 | 0 / 0 / 5 | 3 |
| software used for phylogenetic analysis | P4 | P4 | P4 | 0 / 2 / 1 | 4 |
| software utilizado para análise filogenética | — | P7 | P7 | 0 / 0 / 5 | 5 |
| phylogenetic analysis | P4 | P7 | P4 | 0 / 2 / 2 | 4 |

| Query | Lexical Top 5 (ordem) | Semantic Top 5 (ordem) | Hybrid Top 5 (ordem) |
|---|---|---|---|
| arbovirus evolution | P8, P8, P8, P8, P8 | P5, P8, P2, P9, P9 | P8, P8, P8, P8, P8 |
| recombination in arboviruses | P1, P1, P1, P1, P1 | P5, P8, P8, P8, P8 | P1, P1, P5, P1, P8 |
| phylogenetic analysis of arboviruses | P5, P5, P5, P5, P5 | P5, P8, P8, P5, P5 | P5, P5, P5, P5, P5 |
| genomic surveillance | P10, P10, P10, P10, P10 | P4, P10, P10, P5, P10 | P10, P10, P10, P10, P10 |
| evolutionary dynamics of arboviruses | P5, P5, P5, P5, P5 | P5, P1, P8, P8, P5 | P5, P5, P5, P5, P5 |
| evolução de arbovírus | — | P5, P9, P7, P5, P5 | P5, P9, P7, P5, P5 |
| recombinação em arbovírus | — | P5, P5, P7, P8, P10 | P5, P5, P7, P8, P10 |
| análise filogenética | — | P1, P10, P10, P5, P9 | P1, P10, P10, P5, P9 |
| vigilância genômica | — | P4, P10, P10, P10, P10 | P4, P10, P10, P10, P10 |
| dinâmica evolutiva dos arbovírus | — | P5, P5, P2, P1, P5 | P5, P5, P2, P1, P5 |
| phylogenetic reconstruction method | P4, P4, P4, P4, P4 | P7, P4, P9, P4, P4 | P4, P4, P4, P4, P4 |
| método de reconstrução filogenética | — | P4, P7, P4, P7, P10 | P4, P7, P4, P7, P10 |
| software used for phylogenetic analysis | P4, P4, P4, P4, P4 | P4, P4, P2, P7, P4 | P4, P4, P4, P4, P4 |
| software utilizado para análise filogenética | — | P7, P7, P7, P9, P7 | P7, P7, P7, P9, P7 |
| phylogenetic analysis | P4, P4, P4, P4, P4 | P7, P4, P4, P4, P4 | P4, P4, P4, P4, P4 |

Top 5 significa cinco **unidades**, podendo haver vários trechos do mesmo paper. Nenhuma diversidade por paper ou threshold de relevância foi acrescentado. FTS exige termos combinados com AND e opera sobre papers; overlap escolhe unidades. RRF continua k=60 e 30 candidatos por fonte. Relações do grafo e thresholds não foram alterados.

### Proveniência dos Top-5 híbridos

| Provenance | Ocorrências |
|---|---:|
| coordinate | 66 |
| exact_page_alignment | 0 |
| section_only | 9 |
| basic_page_text | 0 |

Total: 75 ocorrências, com repetição entre queries; **66** habilitadas para evidência paginada, **66** com página conhecida. Coordenadas indicam origem reportada pelo parser, não garantem relevância ou suficiência científica do trecho.

Observações descritivas: lexical retornou hits em **8/15 queries** (as oito queries em inglês), semantic e hybrid em **15/15**. Nas sete queries PT-BR, a fonte lexical ficou vazia. Entre as 8 queries com fonte lexical, o Top-1 híbrido apontou para o mesmo paper do Top-1 lexical em 8; isso não indica acerto científico. **34/75 hits híbridos** vieram de spans vinculados a referências/citações, um ponto a inspecionar na avaliação humana. Nenhum filtro foi ajustado em resposta a isso.

## Comparação EN × PT-BR

Interseção de papers usa IDs únicos presentes em cada Top 5; interseção de unidades usa unit IDs. Ordens preservam repetições. Não se espera identidade entre idiomas.

| Par | Modo | Ordem EN | Ordem PT-BR | Papers em comum | Unidades em comum | Provenance EN / PT |
|---|---|---|---|---:|---:|---|
| arbovirus evolution ↔ evolução de arbovírus | lexical | P8, P8, P8, P8, P8 | — | 0 | 0 | section_only:5 / — |
| arbovirus evolution ↔ evolução de arbovírus | semantic | P5, P8, P2, P9, P9 | P5, P9, P7, P5, P5 | 2 | 1 | coordinate:5 / coordinate:5 |
| arbovirus evolution ↔ evolução de arbovírus | hybrid | P8, P8, P8, P8, P8 | P5, P9, P7, P5, P5 | 0 | 0 | coordinate:3, section_only:2 / coordinate:5 |
| genomic surveillance ↔ vigilância genômica | lexical | P10, P10, P10, P10, P10 | — | 0 | 0 | coordinate:1, section_only:4 / — |
| genomic surveillance ↔ vigilância genômica | semantic | P4, P10, P10, P5, P10 | P4, P10, P10, P10, P10 | 2 | 4 | coordinate:5 / coordinate:5 |
| genomic surveillance ↔ vigilância genômica | hybrid | P10, P10, P10, P10, P10 | P4, P10, P10, P10, P10 | 1 | 2 | coordinate:5 / coordinate:5 |
| phylogenetic analysis ↔ análise filogenética | lexical | P4, P4, P4, P4, P4 | — | 0 | 0 | coordinate:2, section_only:3 / — |
| phylogenetic analysis ↔ análise filogenética | semantic | P7, P4, P4, P4, P4 | P1, P10, P10, P5, P9 | 0 | 0 | coordinate:5 / coordinate:5 |
| phylogenetic analysis ↔ análise filogenética | hybrid | P4, P4, P4, P4, P4 | P1, P10, P10, P5, P9 | 0 | 0 | coordinate:4, section_only:1 / coordinate:5 |

## Queries orientadas a método

A classificação abaixo é apenas estrutural: a seção ou um ancestral possui categoria methods. Não é julgamento de que o trecho responde à query. Referências/spans sem seção ou headings diferentes continuam visíveis no arquivo detalhado.

| Query | Top 1 hybrid (paper, seção, página) | Top-5 H em Methods/descendentes |
|---|---|---:|
| phylogenetic reconstruction method | P4, Phylogenetic Analysis., 2–2 | 0 |
| método de reconstrução filogenética | P4, sem seção, 13–13 | 2 |
| software used for phylogenetic analysis | P4, Evolutionary Dynamics of Three Genotypes., 3–3 | 0 |
| software utilizado para análise filogenética | P7, sem seção, 14–14 | 0 |

## Avaliação humana — preencher pelo usuário

Não foram atribuídos rótulos de correto/incorreto nem calculada accuracy. As perguntas são sondas de retrieval; os artigos podem não conter evidência para algumas delas.

| Query | Correct paper Top-1 | Correct evidence Top-1 | Relevant in Top-3 | Relevant in Top-5 | Notes |
|---|---|---|---|---|---|
| arbovirus evolution | | | | | |
| recombination in arboviruses | | | | | |
| phylogenetic analysis of arboviruses | | | | | |
| genomic surveillance | | | | | |
| evolutionary dynamics of arboviruses | | | | | |
| evolução de arbovírus | | | | | |
| recombinação em arbovírus | | | | | |
| análise filogenética | | | | | |
| vigilância genômica | | | | | |
| dinâmica evolutiva dos arbovírus | | | | | |
| phylogenetic reconstruction method | | | | | |
| método de reconstrução filogenética | | | | | |
| software used for phylogenetic analysis | | | | | |
| software utilizado para análise filogenética | | | | | |
| phylogenetic analysis | | | | | |

## Arquivos e reprodução

- `scripts/evaluate_retrieval.py`: CLI local, modos lexical/semantic/hybrid/all, Top K e excerpts originais de até 500 caracteres. Recusa banco fora de `.local-data` ou com biblioteca diferente da pasta autorizada.
- `.local-data/arbovirus-retrieval-validation/query-results.json` e `query-results.txt`: Top 5 por modo/query, unit IDs, seções, páginas, provenance, scores/ranks e excerpts curtos. São outputs locais, ignorados pelo Git; não há texto integral neste relatório.
- `results-top5.csv`: mesmos resultados em formato tabular para avaliação humana.
- `structured-summary.json`, `embedding-summary.json`, `catalog-summary.json`: contagens e tempos.
- `baseline-simple/`: banco/resultados da rodada inicial pypdf, preservados para comparação. A baseline criou 90 vetores de 138 unidades, pulou 48 por tamanho e não teve erros. Todos os seus 75 hits híbridos eram basic_page_text e zero habilitados para evidência paginada.

```bash
PETRUS_DATA_DIR="$PWD/.local-data/arbovirus-retrieval-validation" \
  .venv/bin/python scripts/evaluate_retrieval.py \
  --query "método de reconstrução filogenética" --mode all --top-k 5
```

LM Studio precisa continuar servindo o mesmo modelo no endpoint local. O avaliador não baixa modelos, não gera respostas e não modifica PDFs. Ele lê o índice existente; não reindexa a biblioteca. Ruff do script passou, e o CLI lexical também foi executado.

## Limitações e próximos passos

- Corpus pequeno de dez papers, sem ground truth. Scores e coincidências não demonstram relevância, verdade, concordância ou causalidade.
- Modelo disponível era Nomic, não BGE-M3. Cross-lingual precisa de avaliação humana; não generalizar estes resultados para BGE-M3. Não se ajustaram RRF, candidatos, filtros ou thresholds com base nesta amostra.
- Todos os artigos têm avisos de page mapping. section_only não recebe página artificial. Spans de citação/bibliografia também entram no domínio atual; trechos curtos ou referências podem produzir hits com coordenadas sem constituir evidência suficiente. Avaliar isso antes de adicionar filtros.
- Múltiplas unidades do mesmo paper podem dominar Top 5. Unidades longas puladas semanticamente ainda podem aparecer pela fonte lexical.
- O parser pode interpretar metadados/headings incorretamente; nenhuma correção editorial ou tradução automática foi aplicada.
- Não houve alteração no engine/ranking nesta rodada, build Tauri, novo app, geração por LLM, Ask PETRUS, semantic graph ou reprocessamento do restante da V-GEN Lab.
- Próximo passo: usuário preencher a avaliação humana; inspecionar páginas/Methods e hits bibliográficos, decidir se compara outro modelo local e só então planejar melhorias. Não iniciar Ask PETRUS automaticamente.
