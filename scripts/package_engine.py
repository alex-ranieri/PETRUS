"""Build a platform-native sidecar; run on each target OS/architecture."""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.environ["PYINSTALLER_CONFIG_DIR"] = str(root / ".tools" / "pyinstaller-cache")
system = platform.system()
machine = platform.machine().lower()
arch = "aarch64" if machine in ("arm64", "aarch64") else "x86_64"
target = {
    "Darwin": f"{arch}-apple-darwin",
    "Windows": f"{arch}-pc-windows-msvc",
    "Linux": f"{arch}-unknown-linux-gnu",
}[system]
suffix = ".exe" if system == "Windows" else ""
subprocess.run(
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "petrus-engine",
        "--paths",
        str(root / "engine"),
        "--add-data",
        f"{root / 'src-tauri/migrations'}{os.pathsep}migrations",
        "--distpath",
        str(root / "engine/dist"),
        "--workpath",
        str(root / "engine/build"),
        str(root / "scripts/engine_entry.py"),
    ],
    cwd=root / "engine",
    check=True,
)
destination = root / "src-tauri/binaries" / f"petrus-engine-{target}{suffix}"
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(root / "engine/dist" / f"petrus-engine{suffix}", destination)
print(f"Sidecar ready: {destination}")
