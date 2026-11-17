[English](../validation-0.3.1-model-discovery.md) · **Português (Brasil)**

# PETRUS 0.3.1-dev — LM Studio Model Discovery

Data: 16/10/2026. Etapa de UX/provider integration sobre o checkpoint 0.3.0-dev. Implementação e validação nativa concluídas; nenhum novo benchmark Ask executado.

## A. Endpoint e contrato

A operação explícita `llm_models({endpoint})` consulta somente **GET `/api/v1/models`**, validada com `http://127.0.0.1:1234`. Aceita raiz ou `/v1` na configuração e normaliza o caminho para o catálogo nativo. Somente HTTP loopback (`127.0.0.1`, `localhost`, `::1`), sem credenciais/query/fragment, proxy, redirects, telemetria ou internet. Timeout 3 s, resposta limitada a 1 MB e campos de texto limitados a 4096 caracteres. Não envia conteúdo científico.

`llm/catalog.py` compartilha transporte de catálogo e interpretação de reasoning com `LMStudioNativeLLMProvider`. A política permanece: capability com off envia off; capability presente sem off bloqueia; ausente omite reasoning. Não há inferência da capacidade pelo nome do modelo.

A UI recebe apenas ID exato (`key`), display name, tipo/categoria, arquitetura, formato, parâmetros, quantização, tamanho, estado de carregamento e capability normalizada. Campos opcionais ausentes permanecem null; tipos não reconhecidos viram unknown. Campos brutos, paths e instâncias internas não são enviados à UI. IDs inválidos/duplicados são ignorados; modelos unknown continuam no catálogo geral e em um grupo separado nos selects.

## B–C. Modelos reais encontrados e classificação

Consulta real pelo engine, antes do teste de conexão:

| ID exato | Categoria oficial | Formato / quantização | Parâmetros | Loaded nessa consulta | Reasoning off |
|---|---|---|---|---|---|
| `google/gemma-4-e2b` | llm | mlx / 4bit | 2B | false | suportado |
| `qwen3.5-4b-mlx` | llm | mlx / 4bit | 4B | false | capability ausente; badge omitida |
| `qwen/qwen3.5-9b` | llm | mlx / 4bit | 9B | false | suportado |
| `text-embedding-nomic-embed-text-v1.5` | embedding | gguf / Q4_K_M | null | false | capability ausente; badge omitida |

Nenhum unknown foi retornado pelo runtime nesta consulta. A classificação usa `type`, sem heurística de nome. São modelos disponíveis no catálogo, mesmo quando descarregados. A disponibilidade/carregamento pode mudar; esse retrato não é cache persistente nem garantia de compatibilidade científica. Consultar o catálogo não carregou modelos. Não foram feitos testes de geração para comparar os modelos listados.

## D–E. Dropdowns de chat e embedding

`LocalModelSelect` é usado somente quando o respectivo provider é `lmstudio`. Chat mostra llm; embedding mostra embedding; unknown fica em grupo próprio. IDs configurados continuam visíveis mesmo fora da lista. Detalhes opcionais aparecem apenas quando conhecidos. Ausência de capability não produz erro nem badge inventada de internal reasoning.

Sem ID salvo, permanece **Select a model / Selecionar um modelo**. Nenhum primeiro modelo, loaded, Qwen ou embedding é escolhido automaticamente. A seleção altera apenas o draft; Save persiste o ID exato, incluindo strings Unicode. Não há badge ou seleção automática de baseline. OpenAI-compatible permanece com entrada manual, sem descoberta LM Studio.

## F. Refresh e teste de conexão

A abertura do controle e mudanças de endpoint fazem leitura do catálogo em memória. **Refresh models / Atualizar modelos** força nova consulta, com estado de loading no botão. Não salva settings, não muda a seleção, não chama chat/embeddings, não baixa nem carrega modelos. Respostas antigas são descartadas após mudar endpoint/desmontar o controle. Não foi criada tabela/cache de catálogo no SQLite.

**Save and check connection / Salvar e testar conexão** permanece separado: salva o draft e chama o teste de provider/modelo existente. Essa ação explícita pode usar o modelo conforme a semântica anterior; não se confunde com descoberta read-only.

## G–I. Configurado ausente, custom e offline

Modelo ausente permanece selecionado com **Configured — currently unavailable / Configurado — indisponível no momento**. Falha de catálogo mostra instrução EN/PT-BR para iniciar LM Studio e atualizar, sem apagar IDs ou impedir uso de Settings. A UI não expõe texto bruto de erros do servidor. Catálogo vazio possui estado próprio.

**Custom model ID… / ID de modelo personalizado…** abre entrada manual preservando inicialmente o ID atual. ID manual continua possível offline ou com catálogo incompleto; depende de Save para persistir. Nenhuma mudança automática no embedding configurado.

## J. Testes Python

- **212 passed**, suíte completa `engine/tests`, incluindo **26 testes novos** de catálogo.
- **48 testes existentes** de provider nativo passaram também na verificação focada após extrair os helpers compartilhados.
- Cobertura nova: catálogo normal/múltiplo/vazio, opcionais ausentes/malformados, classificação llm/embedding/unknown, IDs Unicode/exatos/duplicados, offline, HTTP sanitizado, redirect rejeitado, loopback, resposta limitada/inválida, capability compartilhada, somente GET e nenhuma mutação de settings/banco.
- Ruff passou para engine, testes e scripts.

## K. Testes frontend e build

- **6 testes novos Playwright**, EN/PT-BR com IPC simulado: lista, classificação, badges condicionais, seleção explícita, ID exato/Unicode salvo, reabertura, embedding, refresh sem save/inferência, loading, offline, ausente, custom, vazio e OpenAI-compatible manual.
- **5 testes existentes Playwright**: navegação Ask com fixtures/IPC simulado, fluxo desktop com fixture local, i18n e conteúdo científico. Não são um novo benchmark Ask contra LM Studio.
- Execução final conjunta: **11 passed (20,5 s)**.
- ESLint e TypeScript passaram sem warnings.
- `npm run build` passou.
- Build Tauri dev 0.3.1-dev passou e o app foi aberto com engine de desenvolvimento e cópia isolada do banco.
- O pacote `.app` do checkpoint 0.3.0-dev não foi reconstruído nem substituído nesta etapa.

## L. Validação real e manual

A chamada real `Engine.call('llm_models', ...)` retornou os quatro modelos acima; um dump completo antes/depois confirmou **nenhuma alteração no banco por essa consulta**.

O usuário confirmou literalmente **“Todos os cinco itens funcionam”** para:

1. Chat lista Gemma 4 E2B, Qwen3.5 4B e Qwen3.5 9B.
2. Selecionar `qwen/qwen3.5-9b`, salvar, sair/reabrir Settings e conferir persistência.
3. Executar Save and check connection.
4. Dropdown embedding lista Nomic Embed Text v1.5.
5. Refresh mantém a seleção.

Essa é confirmação humana da interface nativa, separada dos testes browser com IPC simulado e da consulta real pelo engine. Não houve automação da GUI nativa.

Na leitura posterior, o banco isolado estava com `qwen3.5-4b-mlx` como seleção atual; o valor foi preservado, sem restauração automática ao 9B. Isso não muda a baseline documentada nem substitui a confirmação manual de persistência do 9B. Embedding permaneceu Nomic, temperatura 0,1, contexto 8192, limite 1600, timeout 90 e expansão desligada.

Banco usado: `.local-data/model-discovery-0.3.1/native-smoke/petrus.sqlite3`, criado por backup SQLite da base separada de validação 0.3b. O banco principal do aplicativo não foi utilizado.

Preservação verificada: 10 artigos, 180 seções, 2255 source spans e 2342 vetores; artigos/seções/spans e todas as tuplas do índice de embedding, incluindo blobs de vetores, idênticos à origem da cópia. Settings mudaram somente no fluxo de salvamento explícito da checagem humana. SHA-256 dos arquivos `rag/ask.py`, `rag/validation.py`, `rag/retrieval.py`, `rag/providers.py` e `llm/local.py` não mudou durante esta etapa. Prompts, validator, bounded repair, retrieval e implementação de embeddings preservados. Defaults 1600/90 preservados.

## M. Arquivos alterados

- Engine: novo `engine/petrus_engine/llm/catalog.py`; refatoração compartilhada em `llm/native.py`; operação em `service.py`.
- Fronteira nativa: allowlist em `src-tauri/src/main.rs`.
- UI: novo `app/src/components/LocalModelSelect.tsx`; integração em `AISettings.tsx`; types em `app/src/services/api.ts`; catálogos EN/PT-BR.
- Testes: novo `engine/tests/test_model_catalog.py`; novo `tests/model-discovery.spec.mjs`; resposta de catálogo simulada em `tests/ask-03b.spec.mjs`.
- Versão: `package.json`, `package-lock.json`, `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`, `src-tauri/Cargo.lock`, `engine/pyproject.toml`, `engine/petrus_engine/__init__.py` e label EN/PT-BR atualizados para 0.3.1-dev (Python packaging: 0.3.1.dev0).
- Documentação: `README.md`, `docs/architecture.md` e este relatório.

## N. Evidências locais e encerramento

Arquivos de execução em `.local-data/model-discovery-0.3.1/` (dados de validação locais, sem inclusão no produto): `real-catalog.json`, `real-engine-discovery.json`, `core-before.json`, `data-before.json`, `preservation-check.json`, `python-tests.log`, `lint.log`, `frontend-build.log`, `native-dev.log` e `ui/*tests*.log`.

Etapa 0.3.1-dev concluída. Sem auto-selection, downloader, modelo carregado por refresh, cache SQLite, remote providers, nova avaliação científica ou início da 0.4. O app dev fica aberto para uso na cópia isolada.
