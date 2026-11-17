"""PETRUS-only allowlisted cleanup. Dry-run by default; never follows symlink targets."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

BUILD = (
    "src-tauri/target",
    "app/dist",
    "engine/build",
    "engine/dist",
    "src-tauri/binaries",
    "test-results",
    "playwright-report",
    ".ruff_cache",
    "engine/.pytest_cache",
)
VALIDATION = (
    ".local-data/native-smoke",
    ".local-data/real-validation",
    ".local-data/validation-0.2",
    ".local-data/validation-0.2-coordinates",
    ".local-data/PETRUS Validation.app",
)
DEPENDENCIES = ("node_modules", ".venv")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "validation", "deep"))
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-deep", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        recognized = (
            json.loads((root / "package.json").read_text())["name"] == "petrus"
            and (root / "src-tauri/migrations/001_initial.sql").is_file()
            and (root / "engine/petrus_engine/scientific.py").is_file()
        )
    except (OSError, ValueError, KeyError):
        recognized = False
    if not recognized or root in (Path("/"), Path.home()):
        parser.error("Unrecognized PETRUS root; refusing cleanup")
    if args.execute and args.mode == "deep" and not args.confirm_deep:
        parser.error("Deep deletion requires --execute --confirm-deep; inspect --dry-run first")
    names = BUILD if args.mode == "build" else VALIDATION
    if args.mode == "deep":
        names = BUILD + VALIDATION + DEPENDENCIES
    paths = []
    total = 0
    # Preflight the entire plan before any deletion, including symlink parents.
    for name in names:
        path = root / name
        if any(p.is_symlink() for p in (path, *path.parents) if p != root.parent):
            parser.error(f"Symlink path refused: {path}")
        if not path.exists():
            continue
        if not path.is_dir() or not path.resolve().is_relative_to(root) or path.resolve() == root:
            parser.error(f"Unsafe destination: {path}")
        if any(p.is_file() and p.suffix.casefold() == ".pdf" for p in path.rglob("*")):
            parser.error(f"PDF found inside candidate; manual review required: {path}")
        size = int(subprocess.check_output(["du", "-sk", str(path)], text=True).split()[0]) * 1024
        total += size
        paths.append(path)
        print(f"{'DELETE' if args.execute else 'DRY-RUN'} {size / 1024**2:.2f} MiB  {path}", flush=True)
    print(f"Estimated total: {total / 1024**3:.3f} GiB", flush=True)
    if args.mode == "deep":
        print(
            "Rebuild: npm ci; python3 -m venv .venv; "
            ".venv/bin/python -m pip install -r engine/requirements-dev.lock; "
            ".venv/bin/python -m pip install -e engine --no-deps",
            flush=True,
        )
    if args.execute:
        for path in paths:
            # Check again immediately before deletion; rmtree itself does not follow child symlinks.
            if path.is_symlink() or path.resolve() != root / path.relative_to(root):
                parser.error(f"Destination changed: {path}")
            print(f"Removing {path}", flush=True)
            shutil.rmtree(path)
    else:
        print("No files removed. Use --execute only after reviewing this plan.")


if __name__ == "__main__":
    main()
