[English](../development-cleanup-audit-0.2.1.md) · **Português (Brasil)**

# Auditoria de espaço — PETRUS 0.2.1

15 de outubro de 2026. Tamanhos medidos com `du -sk` antes de qualquer limpeza, em MiB (1024² bytes). São estimativas de blocos alocados; arquivos abertos, clones APFS e caches podem mudar o espaço efetivamente liberado. **Nenhuma limpeza real foi executada no projeto.**

| PATH | SIZE (MiB) | CLASSIFICATION | REASON |
|---|---:|---|---|
| `.tools` | 3,776.20 | KEEP | GROBID, Java, Rust e Gradle necessários; nunca incluído no clean |
| `src-tauri/target` | 2,762.00 | SAFE_TO_REMOVE | Output/cache reconstruível; build também contém o app gerado |
| `.local-data` | 333.34 | NEEDS_REVIEW | Contém somente candidatos conhecidos nesta auditoria; o script não remove o diretório inteiro |
| `node_modules` | 188.65 | OPTIONAL_REBUILDABLE | Reinstalável por npm ci; mantido para continuar desenvolvimento |
| `.venv` | 72.02 | OPTIONAL_REBUILDABLE | Reinstalável pelos locks Python; mantido para continuar desenvolvimento |
| `engine/build` | 28.31 | SAFE_TO_REMOVE | Output/cache reconstruível; build também contém o app gerado |
| `engine/dist` | 23.63 | SAFE_TO_REMOVE | Output/cache reconstruível; build também contém o app gerado |
| `src-tauri/binaries` | 23.63 | SAFE_TO_REMOVE | Output/cache reconstruível; build também contém o app gerado |
| `app/dist` | 1.91 | SAFE_TO_REMOVE | Output/cache reconstruível; build também contém o app gerado |
| `app/src` | 1.30 | KEEP | Código, assets, migrations ou documentação; nunca incluído na limpeza |
| `docs` | 1.04 | KEEP | Código, assets, migrations ou documentação; nunca incluído na limpeza |
| `engine/petrus_engine` | 0.30 | KEEP | Código, assets, migrations ou documentação; nunca incluído na limpeza |
| `.ruff_cache` | 0.03 | SAFE_TO_REMOVE | Output/cache reconstruível; build também contém o app gerado |
| `engine/.pytest_cache` | 0.03 | SAFE_TO_REMOVE | Output/cache reconstruível; build também contém o app gerado |
| `src-tauri/src` | 0.01 | KEEP | Código, assets, migrations ou documentação; nunca incluído na limpeza |
| `src-tauri/migrations` | 0.01 | KEEP | Código, assets, migrations ou documentação; nunca incluído na limpeza |
| `test-results` | 0.00 | SAFE_TO_REMOVE | Output/cache reconstruível; build também contém o app gerado |

Não há diretórios `dist/`, `build/` ou `out/` na raiz. Os outputs reais estão nas subpastas listadas. As linhas de código/docs são protegidas e não entram nos totais de limpeza.
.local-data é detalhado abaixo; não somar novamente seus filhos ao total do projeto.

| PATH | SIZE (MiB) | CLASSIFICATION | REASON |
|---|---:|---|---|
| `.local-data/validation-0.2-coordinates` | 128.45 | SAFE_TO_REMOVE | Cópia/saída de validação ou smoke identificada na etapa 0.2 |
| `.local-data/validation-0.2` | 94.20 | SAFE_TO_REMOVE | Cópia/saída de validação ou smoke identificada na etapa 0.2 |
| `.local-data/PETRUS Validation.app` | 55.30 | SAFE_TO_REMOVE | Cópia/saída de validação ou smoke identificada na etapa 0.2 |
| `.local-data/native-smoke` | 47.29 | SAFE_TO_REMOVE | Cópia/saída de validação ou smoke identificada na etapa 0.2 |
| `.local-data/real-validation` | 8.09 | SAFE_TO_REMOVE | Cópia/saída de validação ou smoke identificada na etapa 0.2 |

## Detalhe de .tools — preservado

| PATH | SIZE (MiB) | CLASSIFICATION | REASON |
|---|---:|---|---|
| `.tools/grobid-0.9.1` | 956.28 | KEEP | Ferramenta/cache local, preservado por decisão desta etapa |
| `.tools/cargo` | 743.54 | KEEP | Ferramenta/cache local, preservado por decisão desta etapa |
| `.tools/gradle` | 646.70 | KEEP | Ferramenta/cache local, preservado por decisão desta etapa |
| `.tools/rustup` | 463.12 | KEEP | Ferramenta/cache local, preservado por decisão desta etapa |
| `.tools/grobid.zip` | 384.97 | NEEDS_REVIEW | Arquivo de instalação; candidato manual, excluído do script |
| `.tools/jdk-21` | 335.66 | KEEP | Ferramenta/cache local, preservado por decisão desta etapa |
| `.tools/jdk21.tar.gz` | 190.81 | NEEDS_REVIEW | Arquivo de instalação; candidato manual, excluído do script |
| `.tools/pyinstaller-cache` | 54.59 | KEEP | Ferramenta/cache local, preservado por decisão desta etapa |

## Estimativas por modo

- `build`: **2.773 GiB**.
- `validation`: **0.326 GiB**.
- `deep`: **3.353 GiB**, incluindo build + validation + dependências; não somar novamente os outros modos.

Os três dry-runs foram executados e não removeram arquivos. Deep exige `--execute --confirm-deep`; nenhum deep real foi executado. A única remoção testada ocorreu em fixture sintética temporária criada pelo teste unitário. Nenhuma pasta de origem desconhecida foi removida.

A limpeza não inclui o banco normal em `~/Library/Application Support/org.petrus.desktop/`, a biblioteca V-GEN Lab, PDFs, `.tools`, fontes, migrations, assets, docs, screenshots ou logs principais. Esses locais não foram usados para testes/limpeza. O script recusa symlinks e PDFs até dentro de destinos allowlisted; somente nomes exatos de pastas temporárias são aceitos.

## Verificação da etapa

- 59 testes rápidos relevantes do engine passaram: 58 na execução inicial local, e o adapter HTTP sintético passou isoladamente (0,60 s) após permissão de bind em loopback. A execução inicial teve somente esse bloqueio de sandbox, sem falha funcional.
- Após acrescentar assertions de persistência, 37 testes de foundation/scientific passaram (2,67 s), excluindo o adapter já conferido. A migration final também passou pelo teste isolado de upgrade (0,07 s).
- Verificação final após testar o backfill de seções parciais/ausentes: 5 testes foundation passaram (0,36 s). Ruff dos arquivos Python alterados e `bash -n scripts/clean.sh` passaram. Shellcheck não estava instalado e não foi instalado.
- Nenhum Playwright, build frontend/Tauri, Clippy, GROBID real ou reprocessamento da biblioteca foi executado. O app empacotado 0.2 permanece sem recompilação.

A migration 003 é aditiva. `.gitignore` já cobria target, node_modules, .venv, .tools, .local-data, outputs frontend/PyInstaller e caches locais; não precisou mudar. TEI e logs de validação existentes ficam em diretórios já ignorados.

Ficaram para 0.3: implementação de embedding/retrieval/RAG, escolha de modelo/tokenizer, política de subdivisão, persistência/invalidação do índice vetorial e respostas com evidências. Nenhum deles foi iniciado.
