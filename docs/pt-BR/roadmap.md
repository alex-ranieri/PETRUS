[English](../roadmap.md) · **Português (Brasil)**

# Roadmap atual

| Etapa | Estado / escopo |
|---|---|
| 0.1–0.2 | Implementadas: biblioteca, parsing científico, referências, provenance, EN/PT-BR |
| 0.3 / 0.3.0-dev | Validada: embeddings, retrieval híbrido, Ask com validator/reparo, grafo semântico opcional e pacote de desenvolvimento |
| 0.3.1-dev | Validada: catálogo e seleção explícita de modelos LM Studio |
| 0.4a | Validada em 0.4.0-dev: snapshots por sessão, decisão/nota humanas, filtros, origem e eventos básicos; fluxo real e reabertura confirmados |
| 0.4b | Validada em 0.4.1-dev: Research Trail por sessão, atores, histórico imutável, notas e remoções auditáveis; fluxo real, checagem nativa e reabertura confirmados |
| 0.4c | Implementada; validação em andamento: claims humanos, vínculos Supports/Contradicts/Context, histórico, revisão e arquivamento |
| Demais etapas | Síntese (0.4d), exportação e descoberta externa exigem escopo e autorização próprios |
| 1.0 | Distribuição estável macOS/Windows/Linux, condicionada à validação de cada plataforma |

[Relatório 0.4a](validation-0.4a-evidence-workspace.md). Nenhuma etapa futura é iniciada automaticamente.

## Planned work / Trabalho planejado

Planning only: no feature below has been implemented by this documentation update, no release date is promised and the table does not assign new version numbers. / Planejamento: esta atualização não implementa os recursos, não promete datas nem atribui versões futuras.

| Direction / Direção | Scope / Escopo | Acceptance / Aceitação |
|---|---|---|
| PDF discovery agent / Agente de PDFs | Question/topic/DOI search, reference expansion, candidate review, authorized open-access acquisition and indexing / Busca por pergunta/tema/DOI, expansão de referências, revisão e aquisição autorizada | Explicit opt-in to external search, approved downloads or bounded batch policy, source URL/date/identifiers/access metadata, PDF validation, SHA-256 deduplication, timeouts, cancellation, rate limits and visible failures; no paywall bypass / Busca opcional, autorização, proveniência, validação, dedupe e falhas visíveis |
| Ollama integration / Integração Ollama | Dedicated provider, explicit chat and embedding models, health/capability checks / Provider próprio e seleção de modelos | Existing Ask citation/validation contract preserved; test EN/PT, failures, offline inference and local-only model execution; no silent cloud fallback / Preservar contrato Ask, testar falhas e execução local sem fallback em nuvem |
| Model manager / Gerenciador de modelos | Optional catalog, download/update/removal, storage and hardware guidance / Catálogo e gestão de downloads | Show model identity/version or digest, license, quantization, size and measured hardware profile; explicit consent, progress, cancellation and integrity checks where supported; embedding changes require explicit reindexing / Transparência, consentimento, integridade e reindexação explícita |
| Managed runtime / Runtime gerenciado | Evaluate PETRUS-managed inference and optional downloadable model packs / Avaliar inferência gerenciada e pacotes baixáveis | Compare separate Ollama installation with distributable runtime options; establish redistribution rights, process ownership, loopback controls, updates, uninstall behavior and tests per OS / Validar licenças, ciclo de vida e plataformas |
| Cross-platform distribution / Distribuição multiplataforma | macOS arm64, Windows x64, Linux x64; other architectures later / Outras arquiteturas depois | Native sidecar builds, fresh-machine install/launch/upgrade checks, file dialogs, PDF opening, database migrations, optional AI, documented signing and artifacts / Builds e testes reais por sistema |
| Evidence export and reports / Exportação e relatórios | Portable evidence/claim/trail export and report building / Exportação portável e relatórios | Preserve source identity and provenance; distinguish exact source text, human writing and generated content / Preservar proveniência e autoria |
| Scoped synthesis / Síntese com escopo próprio | A separately designed future assistive workflow / Fluxo futuro separado | Human review and traceable citations; do not replace or auto-generate the current human-only Findings / Não alterar o caráter humano dos Achados atuais |
| Usability and extraction / Usabilidade e extração | OCR, metadata editing, job cancellation, accessibility / OCR, metadados, cancelamento e acessibilidade | Preserve originals, record processing changes and expose extraction uncertainty / Preservar originais e incerteza |

### Proposed sequence / Sequência proposta

1. Complete real-corpus validation of existing human claims and consolidate the macOS package. / Concluir validação real das claims e consolidar o pacote macOS.
2. Publish a clearly labeled macOS prerelease with installation notes and reproducible release assets. / Publicar pré-release macOS identificada.
3. Add and validate the optional Ollama provider/model manager; evaluate a managed runtime separately. / Validar Ollama e downloads; avaliar runtime embarcado separadamente.
4. Validate Windows and Linux in native build/test environments; introduce a CI build matrix after successful platform bring-up. / Validar sistemas nativos e depois automatizar a matriz de builds.
5. Implement external discovery and the PDF agent as an explicit online module, followed by exports/reports and separately scoped synthesis. / Implementar descoberta/agente como módulo online explícito; depois exportação/relatórios e síntese com escopo próprio.

This ordering is a proposal, not an implementation commitment. Local library/search must remain usable without models, downloads or external search. Model/runtime redistribution is a separate decision from offering downloads. Offline use requires previously available PDFs, models and runtimes. / Ordem proposta, sem compromisso de execução. Biblioteca/busca devem funcionar sem modelos e serviços externos. Uso offline exige recursos previamente disponíveis.

Ollama offers local and cloud APIs; a PETRUS local-only integration must select downloaded local models and test that inference does not leave the device. See [Ollama API](https://docs.ollama.com/api/introduction) and [model downloads](https://docs.ollama.com/api/pull). / Ollama também oferece modelos em nuvem; integração local exige seleção e validação específicas.

## Planejamento histórico

A tabela abaixo registra o planejamento anterior, não o estado atual. O grafo semântico opcional já foi implementado na série 0.3; o trabalho de sessões foi dividido em workspace 0.4a e trilha 0.4b. As versões futuras originais não são compromissos de execução ou datas.


| Versão | Escopo |
|---|---|
| 0.1 — implementado | Biblioteca local, metadados básicos, FTS5, grafo inicial, notas e scaffold de sessões |
| 0.2 — implementado | Parsing científico estruturado, GROBID, referências, grafo de citações e interface English / Português (Brasil) |
| 0.3 | Embeddings, RAG local, respostas no nível da evidência e links para páginas do PDF |
| 0.4 | Grafo semântico: métodos, resultados, limitações e datasets |
| 0.5 | Sessões completas, Evidence Cards, Research Trail e Report Builder |
| 0.6 | OpenAlex, expansão de citações e descoberta open access |
| 0.7 | Research Agent, busca autônoma de evidências, aquisição autorizada e reindexação |
| 1.0 | Distribuição estável macOS e Windows |

Antes de uma distribuição pública: builds e testes reais por plataforma, assinatura/notarização, política de atualização, revisão de dependências, metadados editáveis e revisão de acessibilidade. OCR, correção de metadados e cancelamento manual de jobs são melhorias incrementais prioritárias. Não há previsão automática de datas.

Validação do escopo 0.2: [validation-0.2.md](validation-0.2.md).
