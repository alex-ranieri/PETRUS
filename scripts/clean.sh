#!/usr/bin/env bash
set -euo pipefail
PETRUS_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 "$PETRUS_SCRIPT_DIR/clean.py" "$@"
