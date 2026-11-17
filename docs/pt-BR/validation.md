[English](../validation.md) · **Português (Brasil)**

# Validação desta iteração

Data: 15 de outubro de 2026. Ambiente: macOS Apple Silicon (arm64).

## Resultado

| Verificação | Resultado |
|---|---|
| Pytest do engine | 21 testes passaram |
| Fluxo completo Playwright | 1 teste de ponta a ponta passou |
| ESLint + TypeScript | Sem erros |
| Ruff | Sem erros |
| Rust Clippy `-D warnings` | Sem warnings/erros |
| Build frontend | Passou, grafo em chunk separado |
| Build Tauri de desenvolvimento | PETRUS.app arm64, aproximadamente 55 MB |
| Assinatura local | Assinatura ad hoc aplicada; `codesign --verify --deep --strict` passou |
| Engine empacotado | Ingestão, FTS5 e texto por página passaram com runtime Python embutido |
| Logo | SHA-256 do asset idêntico ao PNG original |

O teste Playwright usa React e o engine Python reais, banco temporário e dois PDFs sintéticos. Substitui a fronteira nativa de IPC, diálogo e abertura/revelação de arquivos. Verifica onboarding, ingestão, busca, detalhes/DOI, conteúdo por página, notas, criação/associação de coleção, renderização do grafo, criação de sessão e recuperação após reiniciar o engine. As solicitações de Open PDF/Reveal são verificadas na fronteira de IPC; esse teste não automatiza Preview ou Finder.

A validação nativa abriu o `.app` com o engine empacotado, exibiu onboarding com a logo, abriu o seletor de diretórios, exibiu progresso e a biblioteca real da V-GEN Lab e executou busca textual pela interface. As telas claro/escuro e o grafo foram renderizados e inspecionados. Abrir/revelar no sistema usa `OSService` compilado; a visualização do conteúdo no Preview/Finder não faz parte da evidência automatizada.

O smoke test do executável PyInstaller remove Python de desenvolvimento do PATH em sistemas POSIX, cataloga os dois PDFs sintéticos, consulta FTS, lê texto da página e encerra o processo. Isso confirma que o sidecar e o subprocesso parser funcionam sem a `.venv`. No ambiente de execução do agente, o sandbox bloqueia o semáforo do bootloader PyInstaller; o teste do binário foi executado fora desse sandbox e passou. Isso não é uma dependência do usuário do aplicativo.

## Biblioteca real — leitura inicial separada

A primeira leitura de desenvolvimento encontrou **266 PDFs**, dos quais **43 estavam disponíveis localmente e foram indexados**; **223 estavam marcados pelo macOS como sob demanda** e foram registrados sem forçar download. Houve dois avisos de extração entre os arquivos disponíveis, além dos locais cloud-only. A busca por `dengue` retornou 26 artigos e o grafo recebeu 43 nós. Esses números descrevem a leitura inicial; disponibilidade e resultados podem mudar após sincronização do OneDrive e novas varreduras.

O resultado técnico dessa leitura permanece somente em `.local-data/real-validation/`, ignorado pelo Git. Nenhum PDF de pesquisa foi copiado para o repositório. A biblioteca real não é usada nos testes automatizados. A UI nativa foi exercitada em outro banco de teste em `.local-data/native-smoke/`.

## Limites da evidência

Não foram validados builds Windows/Linux, distribuição pública, notarização, OCR, GROBID, RAG, modelos locais ou consultas externas. Essas funcionalidades estão desativadas ou no roadmap. O build entregue é de desenvolvimento para uso local no Mac; não representa uma release 1.0.

Os testes verificam que arquivos sintéticos permanecem idênticos antes/depois da ingestão e da remoção de biblioteca. A validação real usa somente leitura dos PDFs, sem comparação exaustiva de hashes antes/depois de toda a árvore de pesquisa.
