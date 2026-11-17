[English](../grobid.md) · **Português (Brasil)**

# GROBID local no PETRUS 0.2

GROBID é opcional e permanece fora do `.app`. O engine Python, a biblioteca, a pesquisa e as páginas funcionam sem Java/GROBID. A implementação validada usa **GROBID 0.9.1, Java 21 e os modelos Wapiti**, sem Docker. Os scripts a seguir são para desenvolvimento no macOS; o adapter HTTP e o domínio Python não dependem do macOS.

## Preparar e iniciar no Mac

Na pasta do projeto:

```bash
bash scripts/setup_grobid.sh
bash scripts/start_grobid.sh
```

O primeiro script baixa o JDK Temurin 21 e o código oficial GROBID para `.tools/` e compila `:grobid-service:classes`. Não altera o Java do sistema. O download/compilação inicial requer internet e espaço para aproximadamente 1–2 GB de ferramentas/modelos/cache. Datasets de treinamento e documentação do projeto externo são omitidos na extração. Permissões de execução de `gradlew`, `pdfalto` e `pdfalto_server` são restauradas explicitamente.

O segundo comando permanece em primeiro plano: mantenha esse terminal aberto; `Ctrl+C` encerra o serviço iniciado nele. Não inicie uma segunda instância na mesma porta. Após a preparação, o comando usa Gradle `--offline`. Configure `PETRUS_JAVA_HOME` ou `PETRUS_GROBID_HOME` somente para usar instalações locais alternativas.

O script configura ambos os conectores em **127.0.0.1**: API 8070 e administração 8071. A aplicação usa apenas a API 8070. Configura concorrência 2 e carregamento sob demanda dos modelos, adequados à validação local.

## Ativar no aplicativo

1. Abra o PETRUS e conecte sua biblioteca.
2. Em **Settings → Indexing** ou **Configurações → Indexação**, selecione **GROBID**.
3. Mantenha `http://127.0.0.1:8070` e clique em **Check connection / Testar conexão**.
4. Mantenha o fallback simples habilitado.
5. Abra um artigo e clique em **Reprocess scientific metadata / Reprocessar metadados científicos**. Para a biblioteca inteira, use o botão correspondente em **Libraries / Bibliotecas**.
6. Acompanhe o progresso e examine **Content → Structured**, **References** e **Explore**.

Escolher GROBID não reprocessa silenciosamente todos os arquivos antigos. Novos conteúdos ingeridos usam a configuração escolhida; os existentes dependem da operação explícita de reprocessamento. Reprocessamento preserva hashes e a camada de páginas; se tamanho/mtime mudaram, primeiro é necessário reescanear.

## Privacidade e protocolo

`GrobidService` aceita apenas HTTP em `127.0.0.1`, `localhost` ou `::1`. `localhost` é conectado diretamente a `127.0.0.1`, sem resolução DNS arbitrária. Proxies e redirects não são usados. Credenciais, query strings e paths arbitrários no endpoint são recusados.

Cada `processFulltextDocument` envia `consolidateHeader=0`, `consolidateCitations=0` e `consolidateFunders=0`. A configuração do serviço de desenvolvimento também aponta qualquer consolidação eventual para um endpoint local inativo; não usa Crossref ou OpenAlex. O PDF chega somente ao serviço local, que pode criar arquivos temporários necessários ao parsing. Nenhum PDF original é editado. O envio ao GROBID não é uma consulta à internet.

Limites do adapter: 100 MB por PDF, 60 segundos por requisição e 30 MB por resposta TEI. A verificação de saúde tem timeout de 3 segundos. Uma falha produz um registro de tentativa no banco e mantém o conteúdo básico utilizável. Se já existia uma estrutura válida, uma falha transitória conserva essa última estrutura e a sinaliza com aviso.

## Coordenadas e locale da JVM

O script de início define `-Duser.language=en -Duser.country=US` **somente no processo Java**, para estabilizar a serialização numérica de coordenadas. Isso não muda o idioma do macOS nem traduz os artigos.

Na validação, a JVM usando locale português gerou coordenadas com vírgulas decimais, ambíguas com os próprios delimitadores. O PETRUS não tentou adivinhar seus valores: rejeitou essas coordenadas e recorreu ao alinhamento exato. A rodada final usa o formato numérico corrigido. Se iniciar GROBID por outro meio, mantenha a mesma configuração de locale.

O client solicita coordenadas para `p`, `head`, `biblStruct`, `ref` e `s`. Uma região atribuída a uma única página produz spans por coordenadas; regiões que atravessam páginas exigem alinhamento do trecho para não atribuir o parágrafo inteiro a cada página. Alinhamento exige uma ocorrência textual normalizada única, sem fuzzy matching de páginas. Intervalos incompletos ficam `NULL`, mesmo que existam alguns spans conhecidos dentro da seção.

## Diagnóstico

O aplicativo registra erros em `logs/engine.jsonl`, no diretório mostrado em **General / Geral**. Ao executar manualmente, o serviço GROBID mostra seu próprio diagnóstico no terminal. `Check connection` verifica `/api/isalive` e não envia PDFs.

Um HTTP 500 ou limite do GROBID não torna o arquivo indisponível: disponibilidade física, extração básica, indexação e parsing científico são estados separados. PDFs grandes, figuras isoladas e documentos não científicos podem não produzir uma estrutura útil. Títulos, autores, ano e referências extraídos por modelos precisam de conferência: datas de acesso e outros elementos editoriais podem ser interpretados incorretamente. Não há enriquecimento externo para corrigir esses casos.

As coordenadas indicam a região reportada pelo parser, não uma validação manual da interpretação científica. Consulte o PDF original antes de usar os dados em uma síntese ou publicação.

Referências de instalação e API: [documentação oficial de instalação](https://grobid.readthedocs.io/en/latest/Install-Grobid/) e [API GROBID](https://grobid.readthedocs.io/en/latest/Grobid-service/).
