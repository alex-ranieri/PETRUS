"""Exercise the bundled runtime without relying on the developer Python environment."""

import json
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
arch = "aarch64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
target = {
    "Darwin": f"{arch}-apple-darwin",
    "Windows": f"{arch}-pc-windows-msvc",
    "Linux": f"{arch}-unknown-linux-gnu",
}[platform.system()]
suffix = ".exe" if platform.system() == "Windows" else ""
binary = root / "src-tauri/binaries" / f"petrus-engine-{target}{suffix}"
with tempfile.TemporaryDirectory(prefix="petrus-frozen-") as data:
    process = subprocess.Popen(
        [str(binary), "--data-dir", data],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, **({"PATH": "/usr/bin:/bin"} if os.name != "nt" else {})},
    )
    sequence = 0

    def rpc(method, params=None):
        global sequence
        sequence += 1
        process.stdin.write(json.dumps({"id": sequence, "method": method, "params": params or {}}) + "\n")
        process.stdin.flush()
        line = process.stdout.readline()
        if not line:
            raise RuntimeError(process.stderr.read())
        response = json.loads(line)
        if "error" in response:
            raise RuntimeError(response["error"])
        return response["result"]

    try:
        rpc("add_library", {"path": str(root / "engine/tests/fixtures")})
        deadline = time.monotonic() + 30
        while True:
            snapshot = rpc("snapshot")
            if snapshot["jobs"][0]["status"] not in ("running", "queued"):
                break
            if time.monotonic() > deadline:
                raise RuntimeError("Frozen engine timeout")
            time.sleep(0.2)
        assert snapshot["stats"]["indexed"] == 2, snapshot
        assert rpc("papers", {"query": "surveillance"})["total"] == 1
        assert "Evidence for viral evolution" in rpc("content", {"id": 1, "page": 1})["page"]["text"]
        print(
            json.dumps(
                {
                    "frozen_engine": True,
                    "stats": snapshot["stats"],
                    "job": snapshot["jobs"][0]["status"],
                    "fts_search": True,
                    "page_text": True,
                }
            )
        )
    finally:
        process.stdin.close()
        process.wait(timeout=10)
    assert process.returncode == 0
    print("Standalone engine, embedded parser and shutdown: OK")
