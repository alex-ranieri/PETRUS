[English](../validation-0.4b-research-trail.md) · **Português (Brasil)**

# PETRUS 0.4b — Research Trail

Data: 16/10/2026. Base 0.4.0-dev/0.4a. Concluída. Versão 0.4.1-dev / Python 0.4.1.dev0, atualizada somente após testes, validação real, checagem visual humana e comparação após reiniciar o app.

## Preflight — antes de novo schema

Inspeção confirmou cinco migrations. `research_sessions` guarda id, título, pergunta/descrição e timestamps; `research_events` guarda id, session_id/FK CASCADE, event_type, payload_json e created_at UTC. `research_evidence` (migration 005) é o estado atual com snapshots independentes, fingerprint/dedupe e decisões/notas humanas.

Eventos existentes: session_created; ask (resposta aceita salva explicitamente, com pergunta/resposta/evidências e execução sanitizada); evidence_saved, evidence_decision_changed (previous/new), evidence_note_updated (sem texto/hashes), evidence_removed (IDs/fingerprint/decisão, sem título/paginação). Save/update/remove locais já são transacionais. Não há edit/delete de eventos na API; o banco ainda permite SQL direto. A UI mostra apenas rótulo/data da atividade. Ask receipts são voláteis, limitados a 16 respostas, não um histórico persistente.

Lacunas: atores/objeto/versão explícitos; pergunta/retrieval/resultados automáticos por sessão; resumo de ranking/configuração; distinção accepted/abstained/rejected/generation_failed; versões exatas de notas; remoção interpretável após hard delete; timeline expansível, links, filtros e paginação.

Decisão: evoluir research_events, sem segundo log ou event sourcing. Preservar os payloads, IDs e timestamps históricos; nenhuma pergunta ou retrieval antigo será fabricado. Uma fronteira de tracking única indicará a incompletude anterior.

Validação usará somente `.local-data/research-trail-0.4b/native-smoke`, backup SQLite da cópia isolada 0.4a. Os dois itens antigos e seus eventos foram registrados antes da migration; banco original e biblioteca principal permanecem fora desta etapa.

## Resultado técnico e checagens A–V

A validação real abaixo usa o engine verdadeiro por seu transporte JSON-lines, LM Studio local e a cópia isolada. A UI é coberta separadamente por Playwright/fixtures EN/PT-BR e pela checagem visual humana nativa confirmada pelo usuário em 16/10/2026. Não foi executado benchmark ou avaliação científica extensa.

| Item | Resultado |
|---|---|
| A — Preflight/schema | Tabelas/eventos existentes inspecionados antes da migration; decisão aditiva registrada acima. |
| B — Migration | 006_research_trail.sql evolui research_events; 005 intocada; metadados canônicos, índice cronológico, fronteira única e triggers. |
| C — Event model | JSON canônico, payload_version=1, objeto, ator, UTC, SHA e projeção sob demanda; append-only. Sem segundo log/replay. |
| D — Actor model | User: criação explícita/pergunta/save/decisão/nota/remove; AI: resposta/abstinência validada; System: recuperação/rejeição/falha/fronteira/sem fontes. |
| E — Question | Pergunta exata, idioma/SHA; somente quando sessão-alvo explícita foi enviada. Sem sessão não cria Trail ou sessão. |
| F — Retrieval | QueryPlan/config vigentes, contagem retornada limitada, fontes observadas, identidades/ranks/scores/hashes selecionados; nenhum trecho completo. |
| G — Ask results | accepted, abstained, rejected e generation_failed distintos; só conteúdo final validado/canônico. Rejeição não persiste candidato bruto. |
| H — Evidence | Save manual gera histórico e snapshot durável; retrieval não cria SavedEvidence. Origem ligada ao resultado real quando disponível. |
| I — Decision | before/after completos; no-op sem evento; mutação e evento atômicos. |
| J — Note | nova versão exata + hashes antigo/novo, somente Save note e mudança real; 100 mil caracteres sem trim; rollback se falhar evento. |
| K — Removal | título/paper SHA/fingerprint/seção/páginas/decisão preservados; link para save durável ou captura do snapshot legado em novo evento. |
| L — Legacy boundary | nove eventos reais antigos intactos nos cinco campos históricos + uma fronteira; nenhuma pergunta/retrieval retroativa fabricada. |
| M — Trail UI | Abas Evidence/Research Trail; timeline compacta, detalhe lazy, horário local, EN/PT-BR; workspace anterior preservado. |
| N — Filters/navigation | All/User/PETRUS/System; paginação 50 default/100 máximo; links para evidência, paper e eventos relacionados; indisponibilidade explícita. |
| O — Reopen | Duas instâncias sucessivas do engine confirmam IDs, ordem, timestamps, hashes e detalhes idênticos; app nativo também reiniciado com o mesmo banco: 11 eventos idênticos. |
| P — Python | 278 testes passaram (242 anteriores + 36 novos), incluindo remoção legada, identidade de resposta e snapshot em outra sessão; Ruff passou. |
| Q — Frontend | 23 passaram (17 anteriores + 6 novos); TypeScript/ESLint e build Vite passaram; imagens EN/PT inspecionadas. |
| R — Real validation | Q3 uma vez, aceita na primeira tentativa; sete fontes de sete papers, cinco citações; 11 eventos, nota literal do roteiro e transições requeridas. |
| S — Preservation | 10 papers, 180 sections, 2255 spans, 2342 vetores e 17 settings idênticos; dois SavedEvidence antigos integralmente idênticos; 17 arquivos core/005 SHA inalterados. |
| T — Files | Lista abaixo. |
| U — Report | docs/validation-0.4b-research-trail.md. |
| V — Recommendation | **CLOSE_0_4B**. Validações concluídas, metadata 0.4.1-dev atualizada ao final. Nenhuma 0.4c iniciada. |

## Execução real isolada

Nova sessão **Arbovirus Research Trail test**, ID 2. A Q3 foi enviada com session_id explícito e preservou LM Studio native / qwen/qwen3.5-9b, temperatura 0,1, contexto 8192, saída 1600 e timeout 90. Não foi alterado provider, modelo, retrieval, prompt, validator, reparo ou configuração para obter sucesso. `ask_accepted` ocorreu em uma tentativa; recuperação retornou 30 candidatos e selecionou sete fontes, com ranking observado e cinco citações locais. Aceitação estrutural não é revisão científica.

O roteiro salvou explicitamente o primeiro cartão (E1, id 3), marcou Included, gravou exatamente a nota humana fornecida no pedido: `Evidence selected during Research Trail validation.`. Mudou Included → Uncertain → Included. Salvou explicitamente o segundo cartão (id 4) e removeu esse segundo item. A sessão conserva um item Included; a trilha conserva o save e a remoção do segundo. Nenhum cartão foi salvo pela recuperação.

Eventos 11–21: session_created (user), question_asked (user), retrieval_completed (system), ask_accepted (ai), evidence_saved, evidence_decision_changed, evidence_note_updated, evidence_decision_changed, evidence_decision_changed, evidence_saved e evidence_removed (todos os sete últimos user). Ordenação criada em UTC, exibida localmente. Os 11 IDs/timestamps/hashes e todos os detalhes foram comparados em processos separados, sem alteração. A nota tem SHA-256 `7188a5c7348de00c0b46626b03b1202bbbfbe69a32bf9aee8fee36070b703cea`.

A primeira rotina de verificação assumiu equivocadamente a ordem antiga dos itens (E6 antes de E2), embora o contrato de workspace use created_at DESC. O assert foi corrigido para comparação por identidade, somente leitura; não houve segunda geração ou repetição das mutações. O estado real e seus eventos já estavam completos e corretos. A checagem posterior confirmou E6 Included + nota de 17 caracteres e E2 Uncertain, sem alteração de qualquer campo.

## Preservação e evidências locais

`.local-data/research-trail-0.4b/` contém: data-before.json, legacy-events-before.json, core-before.json, preservation.json, real-validation.json, trail-before-native.json e logs de testes/build/lint/native. Não são artefatos de produto/export. A comparação de preservação usa leitura SQLite da cópia fonte 0.4a e compara todas as tuplas, incluindo BLOBs vetoriais, antes de calcular hashes auxiliares. Não copia/reprocessa PDFs nem reindexa.

Os nove eventos anteriores permanecem exatamente iguais em id/session_id/event_type/created_at/payload_json. A migration acrescenta metadados de ator/objeto/versão e uma fronteira; não reescreve payloads. O banco original, as duas evidências antigas e PRAXIS não receberam alterações. O app está apontado exclusivamente para a cópia `research-trail-0.4b/native-smoke`.

Limites observacionais: contagens de candidatos são retornos limitados, não universo completo; ranks do fallback interno não observado são desconhecidos. Histórico antigo de versões de nota não armazenadas é irrecuperável. Append-only preserva o CASCADE de sessão já existente, não fornece proteção contra administração direta do schema. Não há remapeamento automático de IDs após reprocessamento nem garantia de entailment. Não houve pacote/distribuição nova; o .app empacotado continua 0.3.0-dev.

## Arquivos de implementação

- `src-tauri/migrations/006_research_trail.sql`; allowlist em `src-tauri/src/main.rs`.
- Novo `engine/petrus_engine/trail.py`; integração em `service.py` e `research.py`.
- Novos `ResearchTrail.tsx` e `ResearchSessionWorkspace.tsx`; integração em `App.tsx`, `Ask.tsx`, `ResearchEvidenceWorkspace.tsx`, `services/api.ts`, `styles/app.css` e catálogos EN/PT-BR.
- Novo `engine/tests/test_research_trail.py`; compatibilidade em `test_engine.py` e expectativa histórica de notas em `test_research_evidence.py`; novo `tests/research-trail.spec.mjs`.
- README, architecture, database, roadmap e este relatório. Metadata final atualizada após validação: package.json/package-lock.json, Cargo.toml/Cargo.lock, tauri.conf.json, engine/pyproject.toml/__init__.py e versão exibida nos catálogos EN/PT-BR.


A revisão final acrescentou três regressões: remoção de evidência legada preservando o texto existente sem editar o save antigo; recusa de save manual que tente referenciar uma resposta persistida diferente; e save da resposta em outra sessão conservando snapshot independente. Essa última checagem detectou que a projeção de Ask histórico exigia `limitations`, campo não persistido pelo contrato antigo. A projeção agora revalida as citações/texto existentes com a estrutura mínima necessária; não inventa ou persiste limitações históricas e não modifica nenhum payload antigo.


## Checagem final nativa e versão

O usuário confirmou **“Tudo funciona”** para ordem/atores/expansão de pergunta, recuperação, resposta e nota na nova sessão, e E6 Included + nota, E2 Uncertain e aviso de incompletude na sessão antiga. A janela nativa foi reiniciada no mesmo diretório isolado; PIDs do app/engine mudaram de 33773/33852 para 34446/34487. Os 11 eventos foram comparados com o snapshot anterior: IDs, ordem, timestamps UTC e hashes de payload idênticos. Não houve nova geração ou mutação de evidência durante essas checagens.

Uma inspeção adicional da interface em navegador de teste, ligada ao engine real somente por operações de leitura permitidas, confirmou 11 eventos novos, sete identidades na recuperação, expansão de pergunta/recuperação/resposta/nota e reload. A sessão antiga conserva dois itens com decisões included/uncertain, notas de 17/0 caracteres e dez eventos (nove originais + fronteira). Imagens reais e resultado estão em live-trail-top.png, live-trail-note.png, live-legacy-boundary.png e live-ui.json no diretório local de validação. Isso não automatizou a janela nativa.

Após essa validação, metadata foi elevada a **0.4.1-dev / 0.4.1.dev0**. O app dev permanece aberto com a cópia isolada; o pacote antigo não foi substituído. A documentação e as checagens não implicam validação científica extensa ou benchmark de modelos.
