"""Configure the optional development service for loopback and no remote enrichment."""

import sys
from pathlib import Path

config = Path(sys.argv[1]) / "grobid-home/config/grobid.yaml"
value = config.read_text()
value = (
    value.replace("port: 8070", "port: 8070\n      bindHost: 127.0.0.1")
    if "bindHost:" not in value
    else value
)
value = (
    value.replace("port: 8071", "port: 8071\n      bindHost: 127.0.0.1")
    if "bindHost: 127.0.0.1\n    register" not in value
    else value
)
value = value.replace('service: "crossref"', 'service: "glutton"').replace(
    'url: "http://localhost:8080"', 'url: "http://127.0.0.1:9"'
)
value = value.replace("concurrency: 10", "concurrency: 2").replace(
    "modelPreload: true", "modelPreload: false"
)
config.write_text(value)
