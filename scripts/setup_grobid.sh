#!/usr/bin/env bash
set -euo pipefail
PETRUS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$PETRUS_ROOT/.tools"
VERSION=0.9.1
mkdir -p "$TOOLS"
if [[ ! -d "$TOOLS/jdk-21" ]]; then
  case "$(uname -m)" in arm64) ARCH=aarch64;; x86_64) ARCH=x64;; *) echo 'Unsupported architecture'; exit 1;; esac
  curl -fL --retry 3 "https://api.adoptium.net/v3/binary/latest/21/ga/mac/$ARCH/jdk/hotspot/normal/eclipse" -o "$TOOLS/jdk21.tar.gz"
  mkdir -p "$TOOLS/jdk-21"
  tar -xzf "$TOOLS/jdk21.tar.gz" --strip-components=1 -C "$TOOLS/jdk-21"
fi
export JAVA_HOME="${PETRUS_JAVA_HOME:-$TOOLS/jdk-21/Contents/Home}"
export PATH="$JAVA_HOME/bin:$PATH"
export GRADLE_USER_HOME="$TOOLS/gradle"
if [[ ! -d "$TOOLS/grobid-$VERSION" ]]; then
  curl -fL --retry 3 "https://github.com/grobidOrg/grobid/archive/refs/tags/$VERSION.zip" -o "$TOOLS/grobid.zip"
  python3 - "$TOOLS/grobid.zip" "$TOOLS" <<'PY'
import sys,zipfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[1]) as archive:
    for name in archive.namelist():
        if '/grobid-trainer/resources/dataset/' in name or '/doc/' in name:
            continue
        archive.extract(name,Path(sys.argv[2]))
PY
fi
cd "$TOOLS/grobid-$VERSION"
chmod +x gradlew
find grobid-home/pdfalto -type f \( -name pdfalto -o -name pdfalto_server \) -exec chmod +x {} \;
./gradlew --no-daemon :grobid-service:classes -x test
echo "GROBID built. Run: bash scripts/start_grobid.sh"
