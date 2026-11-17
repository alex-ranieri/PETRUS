[English](../validation-0.4c-findings-claims.md) · **Português (Brasil)**

# PETRUS 0.4c — Scientific Findings & Claims

19/10/2026. Base validada: 0.4.1-dev. Implementação em andamento; sem bump antecipado.

## Preflight

Lidos os relatórios 0.4a/0.4b, README, architecture, database e roadmap. Schema real 005/006 e serviços/API/UI inspecionados. `research_evidence` representa snapshots atuais independentes, com dedupe por sessão/fingerprint, decisões e notas humanas. `research_events` é o log canônico v1, protegido por triggers append-only, com payload máximo 2,5 MB e fronteira antiga única. CASCADE de sessão é preservado; não há exclusão de sessão na UI. Eventos novos usarão o mesmo writer/transação e ator user, sem segundo histórico ou entidade Finding.

A nova migration 007 criará apenas research_claims e research_claim_evidence. Claim será afirmação humana; Findings será a terceira aba. Vínculos terão fingerprint/metadata imutáveis e referência a snapshot durável já existente; para fontes legadas ainda sem snapshot durável, o primeiro vínculo explícito preservará uma cópia no novo evento de link. Remover SavedEvidence usará SET NULL para conservar vínculo/história.

Nova cópia SQLite: `.local-data/findings-claims-0.4c/native-smoke`, criada por backup da base validada 0.4b em modo somente leitura. Baseline anterior inclui todas as tuplas de papers/sections/spans/vetores com BLOBs/settings/evidências/eventos, além de hashes de todos os módulos rag/llm/graph e migrations históricas. Nenhuma instância dev antiga estava ativa. A base original 0.4b não será aberta pelo novo engine; nenhum LLM, reindexação ou processamento de PDF integra o teste de domínio.

## Implementação A–N

| Item | Resultado |
|---|---|
| A — Preflight | Schema real e contratos 0.4a/0.4b inspecionados; descrições obsoletas de Trail ausente corrigidas no README. |
| B — Migration | 007_research_claims.sql aditiva; nenhuma migration antiga modificada. |
| C — Schema | research_claims + research_claim_evidence; FKs, índice de sessão/data, unicidade por claim/fingerprint e triggers de isolamento. |
| D — ResearchClaim | Texto humano exato, nota exata, draft/reviewed, timestamps UTC e archived_at; nenhuma entidade Finding extra. |
| E — Vínculos | N:N manual, apenas SavedEvidence da mesma sessão; repetir vínculo não muda relação silenciosamente. |
| F — Fingerprint/provenance | Identidade estável, SHA paper/texto, título/seção/páginas/provenance/paginação; snapshot durável reutilizado ou preservado em novo link explícito legado. |
| G — Relações | supports/contradicts/context são classificações humanas, sem LLM/embedding/score de entailment. |
| H — Status | Draft inicial; Reviewed exige vínculo e é uma ação humana; decisão da fonte/relação/revisão independentes. |
| I — Revisões | Versão inicial e novas versões exatas de statement/notas e hashes; sem trim, tradução, geração ou histórico de digitação. |
| J — Trail | Nove novos eventos user/v1, mesmo writer append-only; mutações/eventos atômicos, sem eventos em reads/no-ops. |
| K — Archive/restore | Sem hard-delete de claims na API; arquivadas fora da lista ativa, leitura via filtro/Trail, restauração explícita. |
| L — Findings UI | Terceira aba sem redesenhar sessão, formulários explícitos, seletor da sessão, filtros/contagens EN/PT-BR e ordenação por alteração. |
| M — Navegação | Claim → SavedEvidence/paper/PDF; SavedEvidence → claims; Trail → claim inclusive arquivada. |
| N — Fontes removidas | SET NULL conserva vínculo, identidade, metadados e snapshot histórico; status Reviewed preservado com aviso; sem reconstrução de texto. |

## O–P — Testes

Testes de domínio não chamam LLM. Cobertura nova inclui defaults, texto/nota Unicode e espaços/quebras exatos, vazios/campos inválidos/limites, isolamento/FKs/constraints/unicidade, relações/status independentes, no-ops, archive/restore, paginação, snapshots legados/reutilização, fonte indisponível/removida/reprocessada, navegação reversa, append-only e reabertura. Oito cenários forçam falha no evento para provar rollback de create/update/link/relation/unlink/review/archive/restore.

Os 31 testes novos do engine passaram. A suíte completa final teve **309 passando** (278 anteriores + 31 novos), registrada em `full-engine-tests.log`. Ruff/ESLint/TypeScript e build Vite passaram. Tauri dev compilou e abriu com a nova cópia isolada ainda em 0.4.1-dev.

Playwright: **25 passaram**, preservando os 23 anteriores e acrescentando dois fluxos completos EN/PT-BR. O teste de desktop existente com engine Python real e PDFs sintéticos foi ampliado: cria claim de fixture pela UI, vincula fonte, marca Reviewed, reinicia o processo e compara claim/links/trilha integralmente, além de verificar a UI reaberta. Os dois testes simulados cobrem create/edit/nota/relações/unlink/revisão/Draft/archive/restore/navegação/PDF/indisponibilidade/remoção/filtros/Trail/reload. Screenshots EN/PT inspecionados; fonte histórica e nota humana permanecem visualmente separadas.

O fluxo de edição detectou um problema no nome acessível dos textareas quando preenchidos. Foram adicionados aria-labels explícitos, e a suíte passou. Nenhum teste antigo foi removido; apenas a expectativa do ledger foi atualizada de seis para sete migrations.

## Q — Validação real / reabertura: pendente

A cópia isolada 0.4c foi aberta nativamente com migration 007. Até este checkpoint, nenhum claim foi criado no corpus real. Foram solicitados ao usuário statement inicial, versão revisada e nota, explicitamente como hipótese preliminar de teste, para preservar autoria humana literal. Fixtures sintéticas automatizadas não são apresentadas como afirmações científicas do usuário. O roteiro real e comparação após restart estão preparados em validate_real.py; não serão executados sem os textos.

Falta concluir o roteiro real E6 Supports + E2 Context, revisão/nota/status, sessão descartável para remoção, reabertura e checagem nativa. Nenhum dos itens E6/E2 será removido ou alterado. Nenhuma pergunta Ask/LLM, benchmark ou reindexação integra esse roteiro.

## R — Preservação

Comparação integral de todas as tuplas, incluindo BLOBs, com a cópia fonte 0.4b em modo somente leitura: 10 papers, 180 sections, 2255 source_spans, 2342 vetores, 17 settings, três SavedEvidence preexistentes (incluindo E6/E2) e 21 eventos preexistentes idênticos. Os 22 arquivos monitorados de rag/llm/graph e migrations 001–006 conservam SHA-256. O hash global do SQLite naturalmente muda com o schema; isso não foi usado como teste de preservação.

A projeção API de SavedEvidence agora acrescenta IDs/status de claims relacionadas, sem alterar uma coluna sequer da linha persistida. Triggers da 007 são adicionais; nenhum payload/timestamp/ator/ID de evento anterior é reescrito. A cópia validada 0.4b e o banco principal não foram usados para mutações. Sem alterações em Ask, prompts, validator, repair, modelos, settings, embeddings ou grafo.

## S — Arquivos alterados

- Nova migration 007_research_claims.sql; allowlist em src-tauri/src/main.rs.
- Novo domínio engine/petrus_engine/claims.py; dispatch em service.py; projeção reversa em research.py; tipos/projeção de eventos em trail.py.
- Novo Findings.tsx; integração em ResearchSessionWorkspace.tsx, ResearchEvidenceWorkspace.tsx e ResearchTrail.tsx; DTOs em services/api.ts; estilos app.css e catálogos EN/PT-BR.
- Novo engine/tests/test_research_claims.py, expectativa de ledger em test_engine.py; novo tests/research-claims.spec.mjs e fixture claims-fixture.mjs; ampliação do teste existente desktop-ui.spec.mjs.
- README, architecture, database, roadmap e este relatório.

## T–U — Relatório / recomendação atual

Relatório: docs/validation-0.4c-findings-claims.md. Evidências locais em `.local-data/findings-claims-0.4c/`: baseline/data/core hashes, preservation.json, logs de testes/build/lint/native e screenshots de fixtures. As rotinas reais aguardam human-text.json com textos fornecidos pelo usuário.

**BLOCKED para encerrar 0.4c**, aguardando conteúdo humano e validação real/nativa. Implementação e testes técnicos concluídos. Versão mantida em **0.4.1-dev / 0.4.1.dev0** até validar tudo, conforme solicitado. Não foi reconstruído ou publicado pacote final. Não foi iniciada 0.4d.
