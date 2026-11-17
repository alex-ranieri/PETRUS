[English](../validation-0.2.md) · **Português (Brasil)**

# Validação do PETRUS 0.2

Data: 15 de outubro de 2026. Plataforma: macOS / Apple Silicon. Build Tauri de desenvolvimento, com assinatura ad hoc local. A versão 0.1 continua registrada em [validation.md](validation.md).

## Resultado na biblioteca real

A validação usou um backup SQLite separado do banco de desenvolvimento e somente leitura dos PDFs na biblioteca solicitada. O script abriu o banco de origem em modo read-only, fez backup pela API SQLite e executou migrations/reprocessamento apenas na cópia. Não editou PDFs nem solicitou download de arquivos cloud-only. Na rodada final, todos os 266 caminhos encontrados já estavam disponíveis localmente. Esse estado é um retrato do momento da execução; difere da disponibilidade registrada na validação 0.1.

| Medida | Resultado |
|---|---:|
| Localizações PDF encontradas e locais | 266 |
| Localizações cloud-only/indisponíveis | 0 |
| Conteúdos únicos por SHA-256 tentados | 257 |
| Localizações adicionais de conteúdo duplicado | 9 |
| Processados pelo GROBID | 248 |
| Tentativas científicas que falharam | 9 |
| Referências extraídas | 10.773 |
| Referências resolvidas localmente | 120 |
| Correspondências candidatas, sem criar CITES | 24 |
| Arestas direcionais CITES | 120 |
| Seções extraídas | 4.228 |
| Seções com intervalo completo de páginas | 2.086 |
| Seções sem intervalo completo, mantido NULL | 2.142 |
| Source spans | 25.945 |
| Spans por coordenadas GROBID | 25.850 |
| Spans por alinhamento textual conservador | 95 |
| Chunks da camada independente de páginas | 3.954 |
| Tempo do lote científico, incluindo resolução final | 521,13 s |

Os 248 processamentos produziram 94 artigos estruturados e 154 estruturados com avisos. As outras 9 tentativas falharam: 7 respostas inválidas/erro HTTP do GROBID e 2 PDFs acima do limite de 100 MB. Com fallback habilitado, esses 9 artigos conservaram status científico básico e a causa do erro. Os 257 conteúdos continuaram indexados na camada básica; seus estados básicos eram 242 prontos e 15 com avisos. Uma falha científica não declara o arquivo fisicamente indisponível.

Os números representam extração automática e resolução local, sem auditoria manual de cada metadado, citação ou caixa de coordenadas. Uma referência resolvida representa uma ocorrência bibliográfica; duas ocorrências podem apontar para o mesmo par de artigos. Um candidato fuzzy não entra no total de arestas. A existência de alguns spans não basta para atribuir o intervalo completo de uma seção.

## Correção identificada durante a validação

A primeira rodada produziu as mesmas 248 extrações, 9 falhas, 10.773 referências e 120 arestas, mas apenas 647 seções com páginas e 2.462 spans. A JVM com locale português serializou coordenadas com vírgulas decimais, ambíguas com os delimitadores do atributo. O parser recusou esses valores e usou somente alinhamento textual seguro.

O script de início passou a definir `-Duser.language=en -Duser.country=US` no processo Java. A rodada completa foi repetida em outra cópia do banco; os resultados finais são os da tabela acima. Não foram inventadas coordenadas nem alterados o idioma do SO ou o conteúdo científico.

## Testes e verificações

| Verificação | Resultado |
|---|---|
| pytest, antigos e novos | **54 passaram** |
| Ruff, configuração do projeto | Passou |
| ESLint e TypeScript | Passaram |
| Clippy com `-D warnings` | Passou |
| Build frontend | Passou |
| Playwright / Chromium | **3 testes passaram** |
| Build Tauri macOS `.app` | Passou, 55,47 MiB |
| Assinatura local `codesign --verify --deep --strict` | Passou |
| Smoke do engine empacotado sem Python de desenvolvimento no PATH | Passou: 2 PDFs, FTS, texto por página e encerramento |
| Parsing científico pelo engine empacotado e GROBID local | Passou em cópia temporária: job concluído, 18 seções e 93 referências |

Os testes científicos cobrem TEI inválido/DTD, metadados, referências, hierarquia, headings de métodos em EN/PT, DOI/título, candidatos e rejeição de falsos positivos, direção de CITES, idempotência, migração 001→002, preservação de notas/páginas, fila/progresso, GROBID indisponível/timeout, cache stat, alterações de arquivos, verificação explícita de integridade e providers de disponibilidade. HTTP mock é usado apenas para o adapter; nenhum teste depende de serviço científico na internet.

Playwright usa o engine Python real com PDFs/TEI sintéticos controlados, substituindo a fronteira IPC/diálogo/abertura de arquivos. Verifica onboarding EN/PT-BR, troca imediata, preferência após recriar a página, detecção pt-PT e fallback de outros locales, números locais, fallback de chave ausente, paridade dos catálogos, ausência de texto JSX principal hardcoded, biblioteca/Settings, conteúdo estruturado original, referências/filtros/navegação, citation inspector e branding em Light/Dark. Não substitui testes do WebView nativo, menus do SO ou abertura real em outro leitor de PDF.

## Conferência manual nativa

Uma cópia identificada como **PETRUS Validation** foi aberta com a cópia do banco, sem substituir o aplicativo do usuário. Foram conferidos:

- Interface em inglês e português; a mudança para português atualizou a interface e os menus nativos Arquivo/Editar/Janela sem reiniciar.
- Temas Dark e Light; no Light, Home e grafo foram inspecionados visualmente com a biblioteca real.
- Logo original maior na sidebar e Home. Onboarding, About e proporção da imagem também têm screenshots e verificações com fixtures.
- Grafo real com 257 artigos e 120 conexões, citações selecionadas por padrão e demais relações desligadas; inspector diferenciou artigo de origem, artigo citado, número e citação original.
- Abertura do artigo de origem pelo inspector; Content mostrou categorias traduzidas e headings/texto originais, páginas conhecidas e avisos de mapeamento desconhecido.
- References mostrou itens ordenados, metadados, status e filtro Na biblioteca; Abrir artigo navegou para o artigo citado correto.

Screenshots versionados em `docs/screenshots/` usam somente fixtures sintéticos, sem reproduzir texto integral ou conteúdo sensível da biblioteca real. Incluem onboarding EN/PT-BR, biblioteca, referências, citações e About em Light/Dark. A conferência manual foi amostral, sem alegar revisão integral dos 257 artigos ou de todas as combinações de idioma/tema.

O SHA-256 do PNG original e do asset utilizado na interface coincide: `a9b9375eae0f8181b3fc59b9bdf7657841decbeab1deebb6f1791999f59c7bb8`. A arte não foi redesenhada.

## Reprodução

Para preparar/iniciar o GROBID local no Mac, veja [grobid.md](grobid.md). Nesta máquina a preparação já foi executada; `bash scripts/start_grobid.sh` inicia o serviço quando a porta 8070 estiver livre. A instalação inicial baixa ferramentas oficiais; parsing e resolução operam localmente depois disso.

Para repetir o lote em uma **nova pasta de validação**:

```bash
PYTHONPATH=engine .venv/bin/python scripts/validate_grobid.py \
  --source-db "/caminho/do/banco/de-desenvolvimento/petrus.sqlite3" \
  --library "/caminho/da/biblioteca" \
  --data-dir "$PWD/.local-data/nova-validacao-0.2"
```

O banco de destino deve ser diferente do de origem. O script grava contagens em `summary.json`; logs e TEI ficam locais e não devem ser publicados com PDFs ou textos científicos. A execução registrada usou `.local-data/validation-0.2-coordinates/`.

## Limites restantes

- Coordenadas são as reportadas pelo GROBID; não certificam interpretação científica. Seções incompletas conservam páginas NULL e avisos. Alinhamento não usa correspondência aproximada para inventar páginas.
- Metadados automáticos podem conter erros, como datas editoriais/de acesso interpretadas como ano de publicação. Não há enriquecimento externo nem correção automática pela internet.
- O contrato de abertura recebe página, mas o aplicativo padrão não oferece uma operação portável garantida para abrir nela. O PETRUS abre o PDF e informa essa limitação.
- GROBID/JVM permanecem opcionais, externos ao `.app`; há limites de 100 MB/PDF, 60 s/requisição e 30 MB/TEI. Não há cancelamento manual de jobs nesta fase.
- No grafo completo com 257 nós, títulos ficam pequenos na visão ajustada; zoom e listas acessíveis permitem inspeção individual.
- Não houve build/teste real de Windows ou Linux, notarização Apple ou validação para distribuição pública.
- Não foram implementados LLM, embeddings, RAG, consultas externas ou download automático de artigos.

A migration 001 permaneceu preservada; as alterações usam 002. Com as verificações acima concluídas, o escopo 0.2 é marcado como implementado no roadmap.
