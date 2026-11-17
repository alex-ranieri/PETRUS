"""Strictly loopback-only GROBID adapter. No proxies, redirects or consolidation."""

import http.client
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from petrus_engine.pdf.parser import PdfParser


class GrobidService:
    def __init__(self, endpoint="http://127.0.0.1:8070", timeout=60):
        self.endpoint = endpoint
        self.timeout = timeout
        self.state = "unavailable"
        self.error = None
        self._address()

    def _address(self):
        parsed = urlsplit(self.endpoint)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
            or parsed.username
            or parsed.password
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("errors.localEndpointOnly")
        host = "127.0.0.1" if parsed.hostname == "localhost" else parsed.hostname
        return host, parsed.port or 8070

    def _request(self, method, path, body=None, headers=None, timeout=None):
        host, port = self._address()
        connection = http.client.HTTPConnection(host, port, timeout=timeout or self.timeout)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            # Never follow a redirect: even a local server cannot redirect a PDF to the internet.
            if response.status != 200:
                raise ValueError("errors.grobidResponse")
            data = response.read(30_000_001)
            if len(data) > 30_000_000:
                raise ValueError("errors.grobidResponse")
            return data
        finally:
            connection.close()

    def health(self):
        try:
            alive = self._request("GET", "/api/isalive", timeout=3).strip().lower()
            if alive not in (b"true", b'"true"'):
                raise ValueError("errors.grobidUnavailable")
            self.state, self.error = "available", None
        except Exception:
            self.state, self.error = "unavailable", "errors.grobidUnavailable"
        return {"state": self.state, "error": self.error, "endpoint": self.endpoint}

    def process(self, path: Path):
        boundary = "PETRUS" + uuid.uuid4().hex
        parts = []
        # All enrichment parameters are zero. GROBID receives data only over a loopback socket.
        fields = [
            ("consolidateHeader", "0"),
            ("consolidateCitations", "0"),
            ("consolidateFunders", "0"),
            ("includeRawCitations", "1"),
            ("includeRawAffiliations", "0"),
            ("segmentSentences", "0"),
        ]
        fields += [("teiCoordinates", tag) for tag in ("p", "head", "biblStruct", "ref", "s")]
        for key, value in fields:
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
            )
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="input"; filename="paper.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
        )
        with path.open("rb") as source:
            content = source.read(100_000_001)
        if len(content) > 100_000_000:
            raise ValueError("errors.pdfTooLarge")
        parts.extend([content, f"\r\n--{boundary}--\r\n".encode()])
        self.state = "running"
        try:
            result = self._request(
                "POST",
                "/api/processFulltextDocument",
                b"".join(parts),
                {"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )
            self.state, self.error = "available", None
            return result.decode("utf-8")
        except Exception:
            self.state, self.error = "error", "errors.grobidFailed"
            raise


class GrobidPdfParser(PdfParser):
    def __init__(self, path: Path, service: GrobidService, pages: list[str]):
        self.path, self.service, self.pages = path, service, pages
        self.document = None

    def parse_metadata(self):
        from petrus_engine.pdf.tei import parse_tei

        self.document = parse_tei(self.service.process(self.path), self.pages)
        return self.document

    def extract_pages(self):
        return self.pages

    def extract_references(self):
        if self.document is None:
            self.parse_metadata()
        return self.document["references"]
