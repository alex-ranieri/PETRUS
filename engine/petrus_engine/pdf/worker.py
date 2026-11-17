"""Isolate PDF parsing: a malformed document must not hold the ingest queue indefinitely."""

import json
import subprocess
import sys
import threading
from dataclasses import asdict
from pathlib import Path

from petrus_engine.pdf.parser import ParsedPdf, SimplePdfParser

_active = set()
_lock = threading.Lock()


def cancel_parsers():
    with _lock:
        for process in list(_active):
            if process.poll() is None:
                process.kill()


def parse_pdf_isolated(path: Path, timeout=60) -> ParsedPdf:
    command = (
        [sys.executable, "--parse-pdf", str(path)]
        if getattr(sys, "frozen", False)
        else [sys.executable, "-m", "petrus_engine.pdf.worker", str(path)]
    )
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace"
    )
    with _lock:
        _active.add(process)
    try:
        output, error = process.communicate(timeout=timeout)
        if process.returncode:
            raise ValueError(f"PDF parser failed: {error[-2000:]}")
        return ParsedPdf(**json.loads(output))
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.communicate()
        raise ValueError(
            "PDF parsing exceeded the 60-second limit. The remaining files will continue."
        ) from exc
    finally:
        with _lock:
            _active.discard(process)


def worker_main(path: str):
    result = SimplePdfParser(Path(path)).parse_metadata()
    print(json.dumps(asdict(result), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    worker_main(sys.argv[1])
