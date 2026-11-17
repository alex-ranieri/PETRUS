"""Private JSON-lines transport over stdin/stdout. No TCP listener or web service."""

import argparse
import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from petrus_engine import __version__
from petrus_engine.service import Engine

log = logging.getLogger(__name__)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--parse-pdf":
        from petrus_engine.pdf.worker import worker_main

        worker_main(sys.argv[2])
        return
    args = argparse.ArgumentParser()
    args.add_argument("--data-dir", required=True, type=Path)
    options = args.parse_args()
    logs = options.data_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(logs / "engine.jsonl", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    engine = Engine(options.data_dir)
    log.info("engine_started version=%s", __version__)
    try:
        for line in sys.stdin:
            request = {}
            try:
                request = json.loads(line)
                result = engine.call(request["method"], request.get("params") or {})
                response = {"id": request.get("id"), "result": result}
            except Exception as exc:
                log.exception("request_failed method=%s", request.get("method"))
                message = (
                    str(exc)
                    if isinstance(exc, (ValueError, FileNotFoundError))
                    else "Operation failed. See the local engine log for details."
                )
                response = {"id": request.get("id"), "error": message}
            print(json.dumps(response, ensure_ascii=False), flush=True)
    finally:
        engine.close()
        log.info("engine_stopped")


if __name__ == "__main__":
    main()
