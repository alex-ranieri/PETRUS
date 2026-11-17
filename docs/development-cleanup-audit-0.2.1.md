**English** · [Português (Brasil)](pt-BR/development-cleanup-audit-0.2.1.md)

# Disk-space audit — PETRUS 0.2.1

15 October 2026. Sizes measured with `du -sk` before any cleanup, in MiB (1024² bytes). These estimate allocated blocks; open files, APFS clones and caches can change the space actually reclaimed. **No real cleanup was performed in the project.**

| PATH | SIZE (MiB) | CLASSIFICATION | REASON |
|---|---:|---|---|
| `.tools` | 3,776.20 | KEEP | Required GROBID, Java, Rust and Gradle; never included in cleanup |
| `src-tauri/target` | 2,762.00 | SAFE_TO_REMOVE | Rebuildable output/cache; build output also contains the generated app |
| `.local-data` | 333.34 | NEEDS_REVIEW | Contains only known candidates in this audit; the script does not remove the entire directory |
| `node_modules` | 188.65 | OPTIONAL_REBUILDABLE | Reinstallable with npm ci; kept for continued development |
| `.venv` | 72.02 | OPTIONAL_REBUILDABLE | Reinstallable from Python locks; kept for continued development |
| `engine/build` | 28.31 | SAFE_TO_REMOVE | Rebuildable output/cache; build output also contains the generated app |
| `engine/dist` | 23.63 | SAFE_TO_REMOVE | Rebuildable output/cache; build output also contains the generated app |
| `src-tauri/binaries` | 23.63 | SAFE_TO_REMOVE | Rebuildable output/cache; build output also contains the generated app |
| `app/dist` | 1.91 | SAFE_TO_REMOVE | Rebuildable output/cache; build output also contains the generated app |
| `app/src` | 1.30 | KEEP | Source, assets, migrations or documentation; never included in cleanup |
| `docs` | 1.04 | KEEP | Source, assets, migrations or documentation; never included in cleanup |
| `engine/petrus_engine` | 0.30 | KEEP | Source, assets, migrations or documentation; never included in cleanup |
| `.ruff_cache` | 0.03 | SAFE_TO_REMOVE | Rebuildable output/cache; build output also contains the generated app |
| `engine/.pytest_cache` | 0.03 | SAFE_TO_REMOVE | Rebuildable output/cache; build output also contains the generated app |
| `src-tauri/src` | 0.01 | KEEP | Source, assets, migrations or documentation; never included in cleanup |
| `src-tauri/migrations` | 0.01 | KEEP | Source, assets, migrations or documentation; never included in cleanup |
| `test-results` | 0.00 | SAFE_TO_REMOVE | Rebuildable output/cache; build output also contains the generated app |

There are no `dist/`, `build/` or `out/` directories at the root. Actual outputs are in the listed subfolders. Source/documentation rows are protected and excluded from cleanup totals.
.local-data is detailed below; do not add its children to the project total again.

| PATH | SIZE (MiB) | CLASSIFICATION | REASON |
|---|---:|---|---|
| `.local-data/validation-0.2-coordinates` | 128.45 | SAFE_TO_REMOVE | Validation/smoke copy or output identified in stage 0.2 |
| `.local-data/validation-0.2` | 94.20 | SAFE_TO_REMOVE | Validation/smoke copy or output identified in stage 0.2 |
| `.local-data/PETRUS Validation.app` | 55.30 | SAFE_TO_REMOVE | Validation/smoke copy or output identified in stage 0.2 |
| `.local-data/native-smoke` | 47.29 | SAFE_TO_REMOVE | Validation/smoke copy or output identified in stage 0.2 |
| `.local-data/real-validation` | 8.09 | SAFE_TO_REMOVE | Validation/smoke copy or output identified in stage 0.2 |

## .tools detail — preserved

| PATH | SIZE (MiB) | CLASSIFICATION | REASON |
|---|---:|---|---|
| `.tools/grobid-0.9.1` | 956.28 | KEEP | Local tool/cache, preserved by this stage's decision |
| `.tools/cargo` | 743.54 | KEEP | Local tool/cache, preserved by this stage's decision |
| `.tools/gradle` | 646.70 | KEEP | Local tool/cache, preserved by this stage's decision |
| `.tools/rustup` | 463.12 | KEEP | Local tool/cache, preserved by this stage's decision |
| `.tools/grobid.zip` | 384.97 | NEEDS_REVIEW | Installation archive; manual candidate, excluded from the script |
| `.tools/jdk-21` | 335.66 | KEEP | Local tool/cache, preserved by this stage's decision |
| `.tools/jdk21.tar.gz` | 190.81 | NEEDS_REVIEW | Installation archive; manual candidate, excluded from the script |
| `.tools/pyinstaller-cache` | 54.59 | KEEP | Local tool/cache, preserved by this stage's decision |

## Estimates by mode

- `build`: **2.773 GiB**.
- `validation`: **0.326 GiB**.
- `deep`: **3.353 GiB**, including build + validation + dependencies; do not add the other modes again.

All three dry runs were executed and removed no files. Deep requires `--execute --confirm-deep`; no real deep cleanup was performed. The only tested removal used a temporary synthetic fixture created by the unit test. No unknown source folder was removed.

Cleanup excludes the normal database in `~/Library/Application Support/org.petrus.desktop/`, the V-GEN Lab library, PDFs, `.tools`, source, migrations, assets, documentation, screenshots and primary logs. These locations were not used for testing/cleanup. The script rejects symlinks and PDFs even inside allowlisted destinations; only exact temporary-folder names are accepted.

## Stage verification

- 59 relevant quick engine tests passed: 58 in the initial local run, and the synthetic HTTP adapter passed separately (0.60 s) after loopback bind permission. The initial run encountered only this sandbox restriction, not a functional failure.
- After adding persistence assertions, 37 foundation/scientific tests passed (2.67 s), excluding the already-checked adapter. The final migration also passed the isolated upgrade test (0.07 s).
- Final verification after testing partial/missing section backfill: 5 foundation tests passed (0.36 s). Ruff for changed Python files and `bash -n scripts/clean.sh` passed. Shellcheck was not installed and was not installed for this work.
- No Playwright, frontend/Tauri build, Clippy, real GROBID or library reprocessing was run. The packaged 0.2 app remains unrecompiled.

Migration 003 is additive. `.gitignore` already covered target, node_modules, .venv, .tools, .local-data, frontend/PyInstaller outputs and local caches; no change was needed. Existing validation TEI and logs remain in already-ignored directories.

Deferred to 0.3: embedding/retrieval/RAG implementation, model/tokenizer selection, subdivision policy, vector-index persistence/invalidation and evidence-backed answers. None was started.
