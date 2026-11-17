[English](../validation-0.3-final.md) · **Português (Brasil)**

# PETRUS 0.3 — release checkpoint / 0.3c

**16 de outubro de 2026. Checkpoint preparado: 0.3.0-dev. Testes, build dev, pacote macOS e smoke do sidecar passaram. Checklist nativo dev confirmado pelo usuário nos sete itens e smoke visual do pacote confirmado nos três itens. Recomendação final: CLOSE_0_3. Série 0.3 encerrada como checkpoint de desenvolvimento 0.3.0-dev, sem publicação/notarização.**

## Checklist manual curto — janela dev atual

A janela é iniciada pelo código do workspace com o banco isolado de dez artigos. Não usar o aplicativo antigo registrado. A automação nativa CUA não será utilizada nesta etapa.

1. **Library:** confirmar dez artigos do corpus Arbovirus_evolution.
2. **Settings → AI:** confirmar LM Studio native; qwen/qwen3.5-9b; temperatura 0,1; limite de saída 1600; timeout 90 s. Clicar Check connection e conferir sucesso.
3. **Campos EN/PT-BR:** conferir rótulos/valores; salvar 1600/90, sair e reabrir Settings; tentar valor abaixo/acima dos limites e confirmar bloqueio. Limites: tokens 128–8192, timeout 5–600 s. Não é necessário enviar boolean/string pela UI; isso é coberto por testes reais do backend.
4. **Ask Q1:** enviar `What methods were used for phylogenetic reconstruction?`; conferir loading e resposta aceita se a geração for válida. Se rejeitada, deve aparecer falha técnica, sem chamá-la de evidência insuficiente.
5. **Citação:** numa resposta aceita, clicar [E#], conferir destaque do Evidence Card e paper/seção/página conhecida/provenance/trecho.
6. **Navegação:** View in library → Open paper deve abrir o PDF. O leitor do SO pode não abrir na página exata; o aviso existente é esperado.
7. **Abstinência:** enviar `What is the efficacy of the RTS,S malaria vaccine?`; se houver abstinência validada, conferir estado distinto de falha técnica. Se a geração for inválida, registrar a falha; não contá-la como abstinência.

Não é solicitada avaliação científica extensa. Enviar confirmação dos itens e descrever falhas permite registrar a validação manual. Se Q1 não gerar resposta aceita, o teste visual de citação/card continua pendente; não se inventa sucesso.

## Estado da UI nativa

**Checklist dev confirmado pelo usuário em 16 de outubro de 2026.** Confirmação direta, item a item:

| Item | Retorno do usuário |
|---|---|
| 1 — Library | Há dez artigos |
| 2 — Settings AI / conexão | Tudo ok |
| 3 — Campos / limites | Valores confirmados, juntamente com bloqueio |
| 4 — Ask Q1 | Resposta ok |
| 5 — Citação / Evidence Card | Citação ok |
| 6 — Library / PDF | PDF abrindo corretamente |
| 7 — Abstinência | Evidência insuficiente |

A confirmação corresponde aos sete itens acima, incluindo o fluxo Q1 → citação/card → Library/PDF e o estado de evidência insuficiente. Fonte: resposta humana, registrada em .local-data/release-checkpoint-0.3c/manual-dev-confirmation.json. Não houve relato de rejeição na sessão manual; a apresentação de falhas técnicas permanece coberta pelos testes de browser e não se inventa observação nativa desse ramo.

O app dev foi compilado em 9,04 s e iniciado com o banco isolado de dez artigos. Conforme instruído, não se usou CUA, aplicativo antigo registrado, AppleScript ou cliques automatizados. Na continuação após o checklist, a instância dev já não estava em execução. O novo pacote foi então iniciado explicitamente por seu executável, com PETRUS_DEV_ENGINE removido e PETRUS_DATA_DIR apontando à cópia package-smoke.

**Smoke visual do pacote confirmado pelo usuário:** “Os três itens funcionam” — Library abre com os dez artigos; Settings → AI abre e mostra LM Studio native/Qwen 9B; Ask PETRUS abre. A confirmação foi recebida após o lançamento explícito do pacote atual com a base package-smoke e está registrada em manual-package-confirmation.json. Nenhuma repetição de Q1–Q9 foi solicitada ou executada pelo agente. A evidência visual é a confirmação humana, não observação automatizada da GUI.

## Componentes da série 0.3

Retrieval híbrido local, EvidenceUnits/provenance, embeddings SQLite, QueryPlan EN/PT, Ask com fontes/citações/Evidence Cards, bounded repair, validação e research event final, semantic similarity e settings nativos de token/timeout. Nenhuma nova capacidade científica nesta estabilização.

Baseline: LMStudioNativeLLMProvider, qwen/qwen3.5-9b, reasoning off quando anunciado, temperatura 0,1, contexto 8192, output 1600, timeout 90 s. Embedding text-embedding-nomic-embed-text-v1.5, 768 dimensões. 4B permanece suportado; não é a baseline recomendada.

Benchmark histórico 9B: first pass 5/9; repair 4/9, sucesso 2/4; final 7/9 incluindo três abstinências; mediana de geração final 49,282 s. Benchmark histórico 4B no mesmo orçamento: first pass/final 2/9, duas abstinências, sete falhas; mediana de geração final 57,707 s e fração reasoning mediana 100%. O probe Q1 2400/180 foi separado e não alterou os defaults. Nenhum benchmark/modelo novo será executado nesta etapa.

## Testes e regressões

- **Python completo: 186 passed in 6.44s** — .venv/bin/python -m pytest engine/tests -q. Inclui dois novos casos explícitos de rejeição de strings nos settings; booleanos/ranges/privacidade permanecem cobertos.
- **Ruff completo de engine, tests e scripts: passou**, com ruff.toml.
- **npm run lint: passou**, incluindo ESLint e TypeScript --noEmit.
- **Playwright focado: 5 passed in 12.9s** — ask-03b, desktop-ui e scientific-i18n. Ask/citação/highlight/falha/abstinência e settings EN/PT usam IPC simulado. Onboarding/ingestão de duas fixtures, pesquisa, detalhe, coleções, grafo, sessões e persistência usam engine Python real com fronteira Tauri/dialog/SO substituída. Esses testes não equivalem à observação da janela nativa.
- O primeiro pytest foi limitado pelo sandbox no mock HTTP local; a suíte foi repetida com permissão local apropriada. A atualização da versão revelou uma instalação editável antiga (0.1.0) com namespace obsoleto; ela foi atualizada offline, sem novas dependências, para 0.3.0.dev0. O log de versão passou a usar __version__. Um teste antigo do grafo foi ajustado para ligar explicitamente Shared authors, que começa desligado na política atual. O rótulo About passou a ler a versão de package.json, mantendo o teste de copy/i18n.

Os testes não alteraram prompts, retrieval, defaults ou embedding. Não houve qualquer rodada de LLM, 4B/Gemma ou benchmark nesta etapa. Eventuais chamadas de Check connection/Q1/Q8 pelo usuário pertencem ao checklist manual.

## Build e pacote macOS

- Sidecar PyInstaller atual reconstruído: arm64, runtime Python/NumPy/parser incluídos.
- Build Tauri dev passou, 9,04 s; instância atual iniciada explicitamente com o banco isolado.
- **npm run desktop:build passou**, incluindo build frontend/TypeScript/Vite e Tauri debug com assets empacotados; etapa Rust/bundle final em 13,16 s. Bundle de aproximadamente 60,19 MiB.
- Pacote: src-tauri/target/debug/bundle/macos/PETRUS.app. Versão/CFBundleShortVersionString/CFBundleVersion 0.3.0-dev; Cargo/package.json/Tauri alinhados. Python usa a forma PEP 440 equivalente 0.3.0.dev0, com versão do engine exibida como 0.3.0-dev.
- Assinatura ad hoc local aplicada e **codesign --verify --deep --strict passou**. Sem notarização/publicação.
- O pacote anterior foi preservado em .local-data/release-checkpoint-0.3c/previous/PETRUS-0.2.0.app e não foi aberto.

### Smoke do pacote: confirmado e limite

scripts/smoke_release_bundle.py executou o sidecar **de dentro do novo .app**, com PATH reduzido a /usr/bin:/bin, em .local-data/release-checkpoint-0.3c/package-smoke. O driver usa Python do workspace somente para orquestrar; o engine executado inclui seu próprio runtime empacotado.

Confirmado: startup/shutdown do sidecar; snapshot Settings com LM Studio native/Qwen 9B/0,1/1600/90; Library com dez papers; imports do Ask/provider nativo/NumPy e rejeição de pergunta vazia antes de retrieval/LLM; round-trip de settings; rejeição de boolean/string/valores fora de range; jobs inalterados; assets do build contendo Ask, Settings e Library. Não houve scan, geração LLM ou reprocessamento de artigos. A base foi copiada por SQLite backup da base de validação, não da principal.

**Confirmado manualmente pelo usuário:** Library com dez artigos, Settings/AI com LM Studio native/Qwen 9B e página Ask no pacote atual. A GUI não foi automatizada nem presumida a partir do sidecar; a confirmação humana complementa o smoke técnico. Não se afirma repetição do fluxo Q1/PDF no pacote: esse fluxo foi confirmado na instância dev, conforme o checklist original.

Para testar manualmente o pacote atual com essa base separada (sem usar o aplicativo antigo ou banco principal):

```sh
cd /Users/alexranieri/Documents/PETRUS_Follow_the_connections_Find_the_evidence
env -u PETRUS_DEV_ENGINE \
  PETRUS_DATA_DIR="$PWD/.local-data/release-checkpoint-0.3c/package-smoke" \
  ./src-tauri/target/debug/bundle/macos/PETRUS.app/Contents/MacOS/petrus
```

A janela dev e a janela do pacote devem ser identificadas pelo modo de lançamento; não se deve tratar uma como confirmação visual da outra. A instância dev já estava encerrada ao receber sua confirmação. Abriu-se então somente o pacote atual com a base de smoke separada; sua checagem visual foi solicitada e confirmada pelo usuário após a confirmação dev.

## Integridade e artefatos

O banco principal não foi aberto pelo agente. Os processos de teste usam somente fixtures/diretórios temporários ou bancos de validação explicitamente separados. A base de dez artigos manteve 10 papers, 180 sections, 2255 source_spans e 2342 vetores; o digest do índice antes/depois é idêntico. Hashes de providers, prompts, Ask, validator e retrieval são idênticos aos do início da estabilização. A seleção persistida continua qwen/qwen3.5-9b e os valores efetivos continuam 1600/90.

Logs/manifests em .local-data/release-checkpoint-0.3c/: pytest.log, ruff.log, frontend-lint.log, playwright.log, dev.log, sidecar-build.log, package-build.log, package-manifest.json, package-smoke.log, package-smoke.json, baseline.json, final-integrity.json e backup before-dev.sqlite3. A cópia do smoke e o pacote anterior também ficam nesse diretório, ignorado pelo Git. Screenshots em docs/screenshots são de browser com fixtures, não capturas nativas desta etapa.

Documentação consolidada: architecture.md ganhou CURRENT com os componentes atuais e marcadores explícitos nos estados históricos, sem apagar a evolução. README e metadados de versão foram alinhados ao checkpoint de desenvolvimento. Não se marcou o 4B como universalmente inválido nem se removeu seu suporte.

## Checkpoint e recomendação

**CLOSE_0_3.** Testes, builds, assinatura ad hoc, smoke do sidecar, sete itens da UI nativa dev e três itens do smoke visual do pacote estão concluídos. A série 0.3 é encerrada como **PETRUS 0.3.0-dev**, checkpoint local de desenvolvimento. As confirmações visuais são do usuário e as verificações automatizadas permanecem identificadas separadamente. Sem publicação/notarização ou commit/tag automático; limitações científicas e itens adiados permanecem válidos.

Este diretório ainda não é um repositório Git. Não foram executados init, commit ou tag. Com a checagem manual concluída, comandos recomendados, a executar pelo usuário se desejar adotar Git:

```sh
git init
git add .
git commit -m "Checkpoint PETRUS 0.3.0-dev"
git tag -a v0.3.0-dev -m "PETRUS 0.3.0-dev release checkpoint"
```

.gitignore já exclui bancos locais, ambientes, builds e pacotes; esses comandos não publicam nada. A referência recomendada neste fechamento é v0.3.0-dev; nenhuma tag foi criada.

## Limitações e adiamentos

Aceitação estrutural não comprova correctness/entailment; output do 9B ainda varia. Resistência à injeção foi observada em uma amostra, sem garantia universal. Páginas podem ser desconhecidas; abrir página exata no leitor padrão não é portátil. OCR, streaming, reranker, OpenAlex, Crossref, agent, Report Builder, full Research Trail, novos modelos e indexação de V-GEN inteira ficam adiados. Sem publicação/notarização ou commit/tag automático. Banco principal preservado.
