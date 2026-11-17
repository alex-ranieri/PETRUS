#!/usr/bin/env bash
set -euo pipefail
PETRUS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export JAVA_HOME="${PETRUS_JAVA_HOME:-$PETRUS_ROOT/.tools/jdk-21/Contents/Home}"
export PATH="$JAVA_HOME/bin:$PATH"
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-} -Duser.language=en -Duser.country=US"
export GRADLE_USER_HOME="$PETRUS_ROOT/.tools/gradle"
cd "${PETRUS_GROBID_HOME:-$PETRUS_ROOT/.tools/grobid-0.9.1}"
python3 "$PETRUS_ROOT/scripts/configure_grobid.py" "$PWD"
exec ./gradlew --offline --no-daemon run
