[English](../database.md) · **Português (Brasil)**

# Modelo local

O schema autoritativo está nas migrations `001_initial.sql` a `007_research_claims.sql`, em `src-tauri/migrations/`. A migration inicial não foi alterada. A versão aplicada é registrada em `schema_migrations`. Cada migration é executada uma vez dentro de uma transação.

| Tabela | Função nesta versão |
|---|---|
| libraries | Pastas cadastradas e última varredura |
| papers | Identidade de conteúdo por SHA-256, metadados, status e notas |
| paper_files | Localizações físicas, biblioteca, size, mtime, disponibilidade e erros |
| authors / paper_authors | Autores extraídos e ordem fornecida pelo PDF |
| collections / collection_papers | Organização manual, relação N:N |
| chunks | Texto extraído por página, numerada a partir de 1 |
| paper_search | FTS5 com rowid correspondente a papers.id |
| jobs | Fila persistida, progresso e resultado de varreduras |
| settings | Preferências tipadas no serviço, valores JSON |
| research_sessions / research_events | Sessões e histórico cronológico canônico de pergunta/retrieval/resultado e ações humanas |
| research_evidence | Snapshots de evidência salvos por sessão, decisão humana, nota e origem |
| embedding_index | Vetores locais, identidade de provider/modelo/dimensão e hash de conteúdo |
| references | Referências ordenadas, DOI, estado/confiança de resolução e target local |
| sections | Hierarquia TEI, heading original, categoria, ordem, texto e páginas opcionais |
| evidence | Estrutura para trechos com contexto e página |
| edges | Citações tipadas CITES com reference_id; demais relações são preservadas |
| source_spans | Página, trecho, offsets opcionais, coordenadas e origem do mapeamento |
| parser_runs | Tentativas científicas, TEI e warnings |
| paper_basic_metadata | Snapshot de metadados básicos, separado dos científicos |

`paper_files` normaliza os campos que dependem de localização: um paper não precisa pertencer a apenas uma biblioteca. A restrição `(library_id, file_path)` impede duplicação de localização no mesmo cadastro; `papers.file_hash` impede duplicação do conteúdo. Caminhos sobrepostos entre bibliotecas podem gerar múltiplos vínculos para a mesma localização, sem duplicar o texto indexado.

Um arquivo indisponível antes do hashing tem `paper_id=NULL`. Um arquivo removido mantém o registro da localização com `available=0`. Um PDF que existe mas não pode ser interpretado pode ter `metadata_status=failed` e continuar aberto pelo aplicativo padrão. Um PDF sem texto pode ter status `warning` e precisar de OCR.

O conteúdo é considerado visível enquanto existir pelo menos uma localização cadastrada; se todas estiverem indisponíveis, o status apresentado é `unavailable`. Artigos antigos sem localizações permanecem retidos para reutilização, mas não entram no catálogo ou no grafo. Remover uma biblioteca não apaga documentos físicos nem garante purga de texto indexado.

FTS é atualizado na mesma transação dos metadados e páginas. O título de fallback é pesquisável mesmo antes de o parsing terminar. Os caminhos de arquivos e as preferências de sistema não são indexados no FTS.

Para copiar o banco com o app em uso, use a API de backup do SQLite; copiar apenas o `.sqlite3` pode deixar de fora transações presentes no WAL. Não altere manualmente migrations já aplicadas; adicione uma nova migration.

## Atualização 0.2

`papers.scientific_status` é independente de metadata_status/index_status e disponibilidade: basic, structured, structured_warning ou failed. `scientific_warning` e scientific_updated_at registram o resultado científico. Um job pode concluir com seções parcialmente não mapeadas; examine também o estado científico do artigo.

`references` mantém os campos históricos e acrescenta citation_order, authors_text, journal, year, resolution_status, resolution_confidence, tei_id e timestamps. O booleano histórico resolved permanece sincronizado. Candidate pode guardar um alvo possível, mas não gera CITES nem é tratado como resolvido pela UI. Resoluções ambíguas não escolhem arbitrariamente uma versão de PDF.

`sections.parent_section_id` preserva a árvore. Chunks não são apagados no reprocessamento científico. Source spans de coordenadas têm offsets de caracteres nulos; spans de alinhamento armazenam offsets no texto original da página, com char_end exclusivo. O trecho armazenado é o texto da região TEI para coordenadas ou a substring original do pypdf para alinhamento. Não é uma tradução.

A substituição científica remove/reinsere somente os dados derivados do artigo dentro de uma transação, limpa ligações obsoletas e resolve as referências locais. Histórico de tentativas fica em parser_runs. Não duplica referências/seções ao repetir a operação. Jobs usam job_type scan/integrity/scientific e paper_id opcional, com chaves de mensagem traduzíveis.

`verify_integrity` recalcula hashes; rescan normal usa size/mtime. Settings acrescenta language, scientific_parser, grobid_endpoint e grobid_fallback sem reescrever preferências existentes.

## SavedEvidence — 0.4a

A migration aditiva `005_research_evidence.sql` cria `research_evidence`. Ela não altera o conteúdo das tabelas de fontes, vetores ou settings.

| Grupo | Campos |
|---|---|
| Identidade | id AUTOINCREMENT; session_id NOT NULL/FK; UNIQUE(session_id, evidence_fingerprint) |
| Paper | paper_id/FK opcional; paper_sha256; paper_title_snapshot; paper_doi_snapshot nullable |
| Unidade/fonte | evidence_unit_id original; source_span_id/section_id opcionais; section_heading_snapshot; evidence_role; provenance_level; source_identity_json |
| Paginação | page_start/page_end nullable; supports_paginated_evidence boolean |
| Trecho imutável | text_snapshot exato; text_sha256 UTF-8 |
| Trabalho humano | decision CHECK included/excluded/uncertain, default uncertain; user_note default vazio |
| Origem | origin_type CHECK ask_answer/retrieved_source; research_event_id opcional; question_snapshot/evidence_label_snapshot opcionais |
| Tempo | created_at/updated_at UTC |

Fingerprint: SHA-256 de JSON canônico (chaves ordenadas, separadores estáveis, Unicode preservado) com SHA do paper/texto, páginas, provenance e identidade semântica da seção/fonte/offsets de subdivisão. Trocar IDs numéricos mantendo a fonte não duplica o item na mesma sessão. O primeiro snapshot/origem/decisão/nota é retornado intacto em um save duplicado; não se acumula histórico de cada recuperação nesta etapa. Cada sessão tem sua própria seleção.

FK de sessão usa ON DELETE CASCADE, conforme a política prévia de research_events. Paper, source_span, section e research_event usam ON DELETE SET NULL: excluir/substituir a fonte não exclui o snapshot. FKs atuais podem ficar nulas; evidence_unit_id e os snapshots mantêm a identidade original interpretável. DOI, heading e páginas ausentes não são inventados.

Contrato original 0.4a (o histórico de eventos é ampliado pela 006 abaixo): somente decisão/nota são editáveis. updated_at muda apenas em alteração real; a nota conserva espaços, Unicode e quebras de linha. Ações emitem `evidence_saved`, `evidence_decision_changed`, `evidence_note_updated` e `evidence_removed`. Payload contém IDs/fingerprint/timestamp e decisão anterior/nova quando aplicável; não contém trechos ou texto de notas. Remoção registra evento antes de hard delete na mesma transação, sem undo/versionamento de snapshots. Eventos da sessão permanecem após remover uma evidência; apagar a sessão também os remove por CASCADE.

O service retorna `source_available`, derivado da FK atual e disponibilidade registrada em paper_files. Não há remapeamento de unidades ou detector de stale source nesta etapa: o texto salvo é sempre o snapshot do save. `E6` identifica uma fonte somente dentro da pergunta registrada; não é global. IDs EvidenceUnit também podem mudar após reprocessar.

## Research Trail — migration 006 / payload v1

A migration 006 acrescenta à tabela existente `research_events`: `actor_type NOT NULL CHECK user/ai/system`, `object_type`, `object_id TEXT`, `payload_version NOT NULL CHECK=1` e `legacy NOT NULL CHECK 0/1`. Os cinco campos históricos (id, session_id, event_type, created_at, payload_json) permanecem intactos. Atores/objetos conhecidos são classificados deterministamente. Sessões preexistentes recebem uma única fronteira `trail_tracking_started`; índice parcial único impede duplicação. Novas sessões começam em session_created, sem fronteira retroativa.

| Evento v1 | Ator | Conteúdo durável |
|---|---|---|
| session_created | user | Título e objeto sessão |
| question_asked | user | Pergunta exata, idioma e SHA-256 |
| retrieval_completed | system | ID pergunta; QueryPlan; config; contagens retornadas; identidades/hashes/ranks das selecionadas; fontes observadas; hash do contexto de auditoria |
| ask_accepted | ai | IDs pergunta/retrieval; resposta final validada + SHA; citações locais; provider/modelo/config; tentativas/reparo |
| ask_abstained | ai, ou system sem fontes | Texto canônico de insuficiência e resumo/status; sem geração inventada |
| ask_rejected / ask_generation_failed | system | Códigos permitidos, status e resumo; sem candidato/erro bruto |
| ask (DTO ask_saved_to_session) | user | Save explícito: referência ao resultado na mesma sessão quando disponível; senão snapshot final validado pelo contrato anterior |
| evidence_saved | user | Identidade/fingerprint/metadata/origem e snapshot durável da fonte salva explicitamente |
| evidence_decision_changed | user | Identidade; old_decision/new_decision (previous/new preservados) |
| evidence_note_updated | user | Identidade; old_note_sha256/new_note_sha256; new_note_snapshot exato |
| evidence_removed | user | Identidade/título/paper SHA/seção/páginas/decisão; referência ao save histórico ou snapshot legado capturado agora |
| trail_tracking_started | system | stage=0.4b e prior_activity_may_be_incomplete |

`payload_version=1` é coluna explícita, sem framework de replay/migração de payloads. JSON canônico UTF-8, chaves ordenadas, hash SHA-256 do payload persistido. `E#` é local à pergunta; EvidenceUnit pode mudar após reprocessar. Fonte/trecho/fingerprint continuam independentes em `research_evidence`, cuja migration 005 não foi alterada. Duplicação de versão humana de nota e da fonte explicitamente salva no histórico é deliberada para auditoria; retrieval nunca duplica todos os trechos.

Limites: pergunta 2.000 caracteres, nota 100.000 caracteres, answer snapshot 2.000.000 bytes UTF-8, JSON payload 2.500.000 bytes. Excesso produz erro/aviso explícito, sem truncamento silencioso. O limite de payload é reforçado por trigger de INSERT; UPDATE é proibido. DELETE individual é proibido enquanto a sessão existe; mantém-se somente o CASCADE histórico quando a própria sessão é excluída. Triggers não são proteção contra um administrador que modifique deliberadamente o schema.

`research_trail_list`: session_id obrigatório, actor_type all/user/ai/system, limit 1–100 (default 50), after_event_id da mesma sessão. Cursor usa timestamp+id e a mesma ordem cronológica, sem OFFSET instável. Projeção compacta não contém answer/nota/trecho. `research_trail_get(session_id,event_id)` carrega detalhes sob demanda. DTO inclui atores/objeto/UTC/versão/legacy/hash/metadata e links com disponibilidade atual. Payloads legados passam por whitelist e nunca são encaminhados integralmente. Aviso de incompletude independe do filtro de ator.

Mutação de evidência e evento são atômicos. Ask registra pergunta antes da execução; retrieval e resultado depois do estado conhecido em transação conjunta. O processo de geração nunca fica dentro de uma transação SQLite. Reabrir não recria eventos. O relatório [0.4b](validation-0.4b-research-trail.md) documenta a comparação real por IDs/timestamps/hashes e preservação dos dois snapshots 0.4a.

## Claims humanos — migration 007

| Tabela | Contrato |
|---|---|
| research_claims | id AUTOINCREMENT; session_id/FK CASCADE; statement NOT NULL até 10.000 caracteres; researcher_note até 100.000; review_status draft/reviewed (default draft); created_at/updated_at UTC; archived_at nullable |
| research_claim_evidence | id AUTOINCREMENT; claim_id/session_id FKs CASCADE; saved_evidence_id FK SET NULL; relation supports/contradicts/context; UNIQUE(claim_id,evidence_fingerprint); SHA do paper/texto, fingerprint, paper_id_snapshot/título/seção/páginas/provenance/paginação; decision_at_link; source_snapshot_event_id/FK; created_at/updated_at UTC |

Migration aditiva, sem modificar 005/006 ou suas linhas. Triggers garantem coerência entre claim, sessão e fonte atual, inclusive ao atualizar. A sessão proprietária da claim é imutável; identidade/sessão de SavedEvidence vinculada também não pode ser trocada diretamente. A API não aceita session_id em link/update como substituto do dono real; extrai do banco. Estado anterior de Included/Excluded/Uncertain não muda por vincular uma fonte.

A fonte removida deixa saved_evidence_id NULL, mas o vínculo mantém metadata/fingerprint e referência ao snapshot histórico. paper_id_snapshot é uma identidade histórica sem FK: disponibilidade atual deriva da SavedEvidence viva e paper_files, não dessa chave antiga. `decision_at_link` é histórica e só é mostrada como tal quando a fonte foi removida; caso contrário a UI projeta a decisão atual separadamente. Relações e status não são recalculados por embeddings.

A referência de snapshot aponta ao evidence_saved/remove já durável, ou ao primeiro claim_evidence_linked que preserva o texto legado ainda disponível. O texto não está na tabela de vínculo. O evento original permanece append-only. Remover o vínculo manualmente faz evento e DELETE do vínculo corrente; remover SavedEvidence conserva a linha do vínculo. Claims só têm Archive/Restore na API, sem hard delete. CASCADE de sessão permanece a política anterior.

`research_claim_list(session_id,filter=all,limit=50,after_id?)` ordena updated_at DESC,id DESC. Limite 1–100. All/Draft/Reviewed contam somente ativas; Archived conta arquivadas. Retorna statements completos e contagens descritivas, sem notas/trechos; get(id) fornece detalhe e até 100 vínculos. Snapshot histórico é carregado sob demanda via Trail. `research_claim_update` aceita somente statement, researcher_note e review_status. Limites são explícitos, sem truncamento. Texto NUL é rejeitado para manter coerência entre comprimento SQLite/Python.

Payload v1 dos nove novos eventos usa actor_type=user/object_type=research_claim e claim_id. Created guarda statement_snapshot/researcher_note_snapshot e hashes; statement_updated guarda a nova versão exata e hashes antigo/novo; note_updated guarda new_note_snapshot exato e hashes; status/relação guardam old/new. Link/unlink guardam identidade, relação e referência de snapshot suficientes para entender o passado. Writer, limite 2,5 MB e triggers append-only existentes são reutilizados. Mutações e eventos são atômicos; nenhuma leitura ou abertura produz eventos retroativos.
