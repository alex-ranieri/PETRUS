**English** · [Português (Brasil)](pt-BR/grobid.md)

# Local GROBID in PETRUS 0.2

GROBID is optional and remains outside the `.app`. The Python engine, library, search and pages work without Java/GROBID. The validated implementation uses **GROBID 0.9.1, Java 21 and Wapiti models**, without Docker. The following scripts are for macOS development; the HTTP adapter and Python domain do not depend on macOS.

## Prepare and start on Mac

From the project folder:

```bash
bash scripts/setup_grobid.sh
bash scripts/start_grobid.sh
```

The first script downloads the Temurin 21 JDK and official GROBID source into `.tools/` and compiles `:grobid-service:classes`. It does not change system Java. Initial download/build requires internet access and approximately 1–2 GB for tools/models/cache. Training datasets and the external project's documentation are omitted during extraction. Execution permissions for `gradlew`, `pdfalto` and `pdfalto_server` are explicitly restored.

The second command stays in the foreground: keep that terminal open; `Ctrl+C` stops the service started there. Do not start a second instance on the same port. After preparation, the command uses Gradle `--offline`. Set `PETRUS_JAVA_HOME` or `PETRUS_GROBID_HOME` only to use alternative local installations.

The script binds both connectors to **127.0.0.1**: API 8070 and administration 8071. The application uses only API 8070. Concurrency is set to 2, with on-demand model loading, suitable for local validation.

## Enable in the application

1. Open PETRUS and connect your library.
2. In **Settings → Indexing** or **Configurações → Indexação**, select **GROBID**.
3. Keep `http://127.0.0.1:8070` and click **Check connection / Testar conexão**.
4. Keep the basic fallback enabled.
5. Open a paper and click **Reprocess scientific metadata / Reprocessar metadados científicos**. For the entire library, use the corresponding button in **Libraries / Bibliotecas**.
6. Follow progress and inspect **Content → Structured**, **References** and **Explore**.

Selecting GROBID does not silently reprocess all existing files. Newly ingested content uses the selected configuration; existing content requires explicit reprocessing. Reprocessing preserves hashes and the page layer; if size/mtime changed, rescan first.

## Privacy and protocol

`GrobidService` accepts HTTP only on `127.0.0.1`, `localhost` or `::1`. `localhost` connects directly to `127.0.0.1`, without arbitrary DNS resolution. Proxies and redirects are not used. Credentials, query strings and arbitrary endpoint paths are rejected.

Each `processFulltextDocument` sends `consolidateHeader=0`, `consolidateCitations=0` and `consolidateFunders=0`. The development service configuration also points any eventual consolidation to an inactive local endpoint; it does not use Crossref or OpenAlex. The PDF reaches only the local service, which may create temporary files needed for parsing. No original PDF is edited. Sending a PDF to GROBID is not an internet query.

Adapter limits: 100 MB per PDF, 60 seconds per request and 30 MB per TEI response. The health check has a 3-second timeout. A failure records an attempt in the database and leaves basic content usable. If valid structure already existed, a transient failure retains that last structure and flags it with a warning.

## Coordinates and JVM locale

The startup script sets `-Duser.language=en -Duser.country=US` **only for the Java process**, to stabilize numeric coordinate serialization. This does not change the macOS language or translate papers.

During validation, the JVM using a Portuguese locale generated coordinates with decimal commas, ambiguous with the delimiters themselves. PETRUS did not guess their values: it rejected those coordinates and used exact alignment. The final run uses the corrected numeric format. Keep the same locale settings if starting GROBID another way.

The client requests coordinates for `p`, `head`, `biblStruct`, `ref` and `s`. A region assigned to one page produces coordinate-based spans; regions crossing pages require passage alignment so that the whole paragraph is not attributed to every page. Alignment requires a unique normalized textual occurrence, without fuzzy page matching. Incomplete ranges remain `NULL`, even when some known spans exist within the section.

## Diagnostics

The application records errors in `logs/engine.jsonl`, in the directory shown under **General / Geral**. When run manually, the GROBID service shows its own diagnostics in the terminal. `Check connection` checks `/api/isalive` and sends no PDFs.

An HTTP 500 or GROBID limit does not make the file unavailable: physical availability, basic extraction, indexing and scientific parsing are separate states. Large PDFs, standalone figures and non-scientific documents may not produce useful structure. Model-extracted titles, authors, years and references need checking: access dates and other editorial elements may be misinterpreted. There is no external enrichment to correct these cases.

Coordinates indicate the region reported by the parser, not manual validation of the scientific interpretation. Consult the original PDF before using the data in a synthesis or publication.

Installation and API references: [official installation documentation](https://grobid.readthedocs.io/en/latest/Install-Grobid/) and [GROBID API](https://grobid.readthedocs.io/en/latest/Grobid-service/).
