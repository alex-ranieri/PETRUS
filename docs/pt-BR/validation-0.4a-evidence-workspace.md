[English](../validation-0.4a-evidence-workspace.md) · **Português (Brasil)**

# PETRUS 0.4a — Scientific Evidence Workspace

Data: 16/10/2026. Base: estado validado 0.3.1-dev.

**Status: implementação, testes, fluxo real e reabertura nativa concluídos. Recomendação: CLOSE_0_4A. Versão 0.4.0-dev / Python 0.4.0.dev0 aplicada somente após a validação. Sem empacotamento/release final.**

## A. Migration

Nova migration aditiva `src-tauri/migrations/005_research_evidence.sql`. O ledger passa de quatro para cinco migrations; aplicação e reabertura idempotentes foram testadas. Tabelas de fontes, embeddings e settings não são reescritas pela migration.

A política anterior tem research_events vinculados à sessão com ON DELETE CASCADE e não oferece exclusão de sessão na UI/API. O workspace mantém essa política; a remoção de uma evidência registra evento antes do hard delete, na mesma transação. Não há undo/versionamento de snapshots nesta etapa.

## B. Schema SavedEvidence

Tabela `research_evidence`, distinta de paper, source_span, retrieval hit, embedding e resposta Ask:

- `id` AUTOINCREMENT, `session_id` obrigatório/FK, `evidence_fingerprint`.
- `paper_id` atual/opcional, `paper_sha256`, `paper_title_snapshot`, `paper_doi_snapshot` nullable.
- `evidence_unit_id` original, `source_span_id`, `section_id`, `section_heading_snapshot`, `evidence_role`, `provenance_level`.
- `page_start`, `page_end`, `supports_paginated_evidence`.
- `text_snapshot`, `text_sha256`, `source_identity_json`.
- `decision`, `user_note`.
- `origin_type`, `research_event_id` opcional, `question_snapshot`, `evidence_label_snapshot`.
- `created_at`, `updated_at` UTC.

FK de sessão usa CASCADE; paper/span/section/research_event usam SET NULL. As FKs atuais podem desaparecer sem apagar o snapshot. DOI/páginas/heading ausentes ficam NULL; não são inferidos. Origem, trecho da fonte e conteúdo humano são campos separados.

## C. Fingerprint e dedupe

SHA-256 de JSON canônico com SHA do paper/texto, páginas, provenance e identidade semântica da fonte/seção (heading, tipo, origem, offsets de subdivisão). Não depende apenas de `span:123` nem de IDs numéricos de seção. `UNIQUE(session_id,evidence_fingerprint)` garante idempotência. Duplicata retorna o item existente sem resetar decisão, nota ou origem e sem novo evento saved. A mesma fonte pode pertencer a sessões diferentes.

## D. Snapshot e verificação

`ResearchEvidenceService` reserva uma transação IMMEDIATE, verifica sessão e reconstrói a unidade atual pelo projetor existente, sem modificar retrieval. Confere paper, texto, páginas, provenance, papel e capacidade de paginação quando fornecidos. Texto arbitrário enviado pelo frontend é rejeitado ou ignorado em favor da reconstrução verificada; snapshots são produzidos no engine. Campo de snapshot não é editável pela operação update.

O handler Ask acrescenta somente um recibo opaco `response_id` após a execução preservada. Um registro volátil das últimas 16 respostas guarda pergunta, Evidence Cards e status final, sem answer gerada ou reasoning. Save verifica o pertencimento da unidade/rótulo àquela resposta e depois compara à fonte atual. Um evento Ask persistido também pode fundamentar a origem, com verificação de pertencimento. Recibos expiram ao reiniciar; somente cartões ainda não salvos precisam de uma nova pergunta. Itens já salvos continuam legíveis sem o recibo.

`ask_answer` identifica fonte de resposta aceita; `retrieved_source` identifica fonte recuperada nos demais casos. A origem é derivada pelo engine, não decidida pelo frontend. O primeiro contexto de origem é mantido no dedupe; não há trilha completa de todas as recuperações. `research_event_id` fica NULL quando o usuário não salvou um evento Ask correspondente. Rótulos E# são locais à pergunta; IDs de unidades também não são globais permanentes.

## E–F. Decisão e nota humanas

Default obrigatório `uncertain`, inclusive em fontes citadas por resposta aceita. Valores permitidos: included/excluded/uncertain. O endpoint save não aplica decisão/nota sugeridas pelo chamador; updates explícitos são usados para ações humanas. A UI só altera decisão após seleção e só salva nota com Save note. Não há notas geradas, preenchidas ou reescritas por LLM.

Notas preservam exatamente a string recebida, incluindo espaços, quebras de linha e Unicode; limite explícito de 100000 caracteres. Updates sem mudança não criam evento nem alteram updated_at. Trecho e nota possuem apresentação visual distinta.

## G. Ask → Save evidence

Cada Evidence Card tem ação Save evidence/Salvar evidência e estado Saved/Salva na sessão-alvo. O seletor pequeno permite escolher uma sessão existente ou criar outra. A validação humana identificou ambiguidade no botão genérico Save do seletor. O modo de escolher destino agora usa Choose target session e Use session, sem salvar cartão ou resposta. Save accepted answer to session fica disponível somente para resposta aceita e com destino explícito, reutilizando save_ask_event; não salva automaticamente evidências no workspace. Dois testes EN/PT-BR cobrem essa separação. Nenhuma sessão é escolhida por recência; a sessão-alvo é explícita e permanece apenas no estado da UI Ask, reutilizando uma sessão já aberta quando aplicável. Não há setting global novo nem auto-save de cartões, papers ou resposta.

Citation highlight e navegação existentes permanecem. Após a checagem humana, foi acrescentado um atalho junto à mensagem de geração rejeitada para rolar até as fontes recuperadas e suas ações explícitas de salvamento. Os testes verificam também a possibilidade de salvar fonte recuperada quando a resposta foi rejeitada. Falha de geração continua distinta de abstinência científica validada e não transforma fonte recuperada em resposta aceita.

## H. Research workspace

O detalhe da sessão mostra contagens total/included/excluded/uncertain, filtros e lista com salvamentos mais recentes primeiro. Cada item exibe título, heading, página quando conhecida, provenance, origem, trecho, pergunta/rótulo quando disponíveis, decisão e nota humana. Permite alterar decisão, salvar nota, remover e abrir fonte. Sem síntese automática, claims/findings, busca avançada ou Research Trail completo.

## I. Eventos

`evidence_saved`, `evidence_decision_changed`, `evidence_note_updated` e `evidence_removed` reutilizam research_events. Payload contém IDs, timestamp, fingerprint, paper ID e decisão anterior/nova quando necessário. Não duplica text_snapshot, texto de nota, answer ou reasoning. Remoção de evidência mantém seu evento na sessão; eventual exclusão da sessão remove seus eventos por CASCADE, conforme o schema existente.

## J–K. Persistência e navegação

Testes Python verificam reabertura do engine, FKs, exclusão/reprocessamento de fonte e imutabilidade de snapshot. O teste desktop existente com engine Python real foi preservado e ampliado: salva uma evidência sintética, define decisão/nota de fixture, reinicia o processo e confere os mesmos texto/hash/fingerprint/decisão/nota pela API e UI.

View paper, View in library e Open PDF usam o paper atual quando disponível. Paper ausente/FK nula ou disponibilidade registrada falsa deixam o snapshot visível e mostram Source currently unavailable. Disponibilidade segue o catálogo/último scan; não há novo scan ou detector de fonte alterada. Um snapshot nunca é reescrito silenciosamente por reprocessamento.

Em uma segunda cópia independente (`contract-smoke`), foi exercitado o protocolo JSON-lines real com uma unidade do corpus (`span:2042`): save reconstruído/verificado, snapshot/text hash exatos, duplicate save idempotente e get idêntico após encerrar/reiniciar o processo Python. O item de fixture permaneceu retrieved_source/uncertain e com nota vazia. Todas as tuplas de fontes/vetores/settings permaneceram iguais. Nenhuma chamada Ask/modelo foi feita nesse probe e nenhum item foi inserido por ele no workspace humano nativo. Evidência: `real-contract-smoke.json`. Isso valida engine/transporte/dados reais, sem substituir a checagem humana da GUI nativa.

Reabertura nativa real confirmada: o watcher Tauri encerrou e reiniciou app/engine no mesmo banco isolado; o SHA-256 das linhas completas de research_evidence antes/depois permaneceu idêntico. O usuário confirmou “Tudo funciona após reabrir; E2 está Uncertain”, incluindo dois itens, nota, filtro Included e paper/PDF. Inicialmente havia marcado ambos Included; essas escolhas foram preservadas no primeiro restart. Depois o próprio usuário alterou E2 para Uncertain. O bump posterior para 0.4.0-dev provocou nova reinicialização, também com linhas completas idênticas às capturadas antes do bump.

## L. Python

**242 passed (12,03 s)**, incluindo **30 testes novos** de workspace. Cobertura: migration, coordinate/exact_page_alignment/section_only/basic_page_text, NULLs, texto/hash, fingerprint e substituição de IDs numéricos, dedupe por sessão, decisões/notas exatas, filtros, eventos/no-op, remoção/FKs, fonte indisponível/excluída/reprocessada, campos falsificados, origin receipts e eventos Ask, membership, ausência de reasoning e proteção de snapshots. O teste antigo de migrations foi atualizado para esperar cinco migrations.

Ruff passou para engine, testes e scripts. Sem chamadas reais de modelo nesses testes.

## M. Frontend e builds

**17 testes Playwright passaram (27,8 s)**: 6 novos de workspace EN/PT-BR, 6 de model discovery, 2 de Ask com IPC simulado, 1 desktop com engine Python real e 2 de i18n/conteúdo científico. Novos testes cobrem escolha/criação de sessão, ausência de auto-save, Saved/dedupe, snapshot, filtros, três decisões, nota exata/manual, reload, origem retrieved_source, página NULL, fonte indisponível, PDF/biblioteca e remoção.

Screenshots de fixtures foram inspecionados para verificar o card completo e a separação visual entre fonte e nota humana. ESLint/TypeScript e `npm run build` passaram. Tauri dev compilou e abriu a cópia isolada, inclusive em 0.4.0-dev após o bump validado. Nenhum pacote/release final foi criado. Logo original preservada. Screenshots de fixtures podem ser atualizados pelos testes existentes.

## N. Validação real isolada

Banco: `.local-data/evidence-workspace-0.4a/native-smoke/petrus.sqlite3`, backup SQLite da base separada conhecida `.local-data/arbovirus-retrieval-validation-0.3b/petrus.sqlite3`. Usa a configuração 9B já presente nessa base, sem alterar settings. O banco 0.3.1 com seleção posterior 4B e a biblioteca principal não foram usados/mudados.

Sessão criada pelo usuário: **Arbovirus evidence workspace test**.

O usuário informou que Q3 (“What evidence of arbovirus adaptation is present in these papers?”) retornou **Generation failed / response rejected**. Uma imagem posterior mostrou também Q1 rejeitada por `missing_citations`. A imagem era do estado de geração, sem mostrar os cartões mais abaixo; não demonstrava falha da operação save. O atalho de navegação às fontes foi adicionado para tornar esse fluxo evidente, com 6 testes focados passando após a mudança. As falhas foram registradas; geração, validator, repair e modelos não foram alterados para forçar aceitação. O fluxo previsto permite salvar explicitamente uma fonte recuperada dessa Q3 como retrieved_source/uncertain. A leitura final e a confirmação humana validaram dois itens: E6 da Q1 como retrieved_source/included, com nota humana não vazia; E2 da repetição da Q3 como ask_answer/uncertain. A repetição foi parte do workflow solicitado, não um benchmark ou comparação de modelos. A primeira falha da Q3 e a rejeição da Q1 permanecem registradas neste relatório; nenhum validator foi relaxado para forçar aceitação. Filtros e abertura do paper/PDF foram confirmados após reabrir.

A validação se limita a persistência, provenance e workflow; não é benchmark ou avaliação científica extensa.

## O. Preservação

Verificação final confirmou igualdade integral das tuplas (incluindo blobs) antes/depois em papers (10), sections (180), source_spans (2255), embedding_index (2342) e settings (17). Hashes de todos os módulos existentes em rag, llm e graph também iguais. Nenhum PDF foi reprocessado, embedding reindexado ou setting AI alterado nesta etapa.

A migration naturalmente muda schema/digest do banco. Somente novas tabelas/itens de workspace e research_sessions/events recebem as ações desta etapa. Baseline documentada Qwen 9B, Nomic 768, temperatura 0,1, contexto 8192, 1600 tokens e 90 s preservados. Model discovery, QueryPlan, RRF, boost/seleção, validator, bounded repair, reasoning policy, grafo e prompts preservados.

## P. Arquivos

- Nova migration: `src-tauri/migrations/005_research_evidence.sql`.
- Novo domínio: `engine/petrus_engine/research.py`; dispatch/recibos em `engine/petrus_engine/service.py`; allowlist em `src-tauri/src/main.rs`.
- UI: novos `SaveEvidenceDialog.tsx` e `ResearchEvidenceWorkspace.tsx`; integração em `Ask.tsx`, `App.tsx`, types em `services/api.ts`, estilos em `styles/app.css`, traduções EN/PT-BR.
- Testes: novo `engine/tests/test_research_evidence.py`, novo `tests/research-evidence.spec.mjs`, teste real ampliado em `tests/desktop-ui.spec.mjs`, expectativa de migration em `engine/tests/test_engine.py`.
- Docs: README (preflight corrigiu limitação obsoleta de AI desativada), architecture, database, roadmap e este relatório. Histórico de versões/planejamento preservado e identificado.
- Versões, após validação: package.json/package-lock.json, src-tauri/tauri.conf.json, Cargo.toml/Cargo.lock (pacote petrus), engine/pyproject.toml e petrus_engine/__init__.py, label sidebar EN/PT-BR atualizados para 0.4.0-dev / Python 0.4.0.dev0. Metadata do editable install alinhada, sem baixar dependências.

## Q–R. Evidências e recomendação

Relatório: `docs/validation-0.4a-evidence-workspace.md`.

Evidências locais em `.local-data/evidence-workspace-0.4a/`: `core-before.json`, `data-before.json`, `copy-source.txt`, `preservation-latest.json`, `check_preservation.py`, logs de Python/lint/Ruff/build/dev, `ui/*tests*.log`, `real-contract-smoke.json`, `before-reopen.json`, `after-reopen.json`, `before-version.json`, `after-version.json`, `manual-confirmation.json` e `final-summary.json`. Nenhum conteúdo de reasoning é registrado pelo workspace.

**CLOSE_0_4A.** Definition of Done atendida para o workspace de desenvolvimento. App 0.4.0-dev permanece aberto com a cópia isolada; sem pacote/release final, síntese automática ou início da 0.4b. A validação de workflow não transforma uma resposta rejeitada em resposta científica aceita, nem comprova entailment das fontes.
