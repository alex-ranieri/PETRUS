import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

DOI_PATTERN = re.compile(r'10\.\d{4,9}/[^\s<>"\x00-\x1f]+', re.IGNORECASE)


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    found = DOI_PATTERN.search(value)
    if not found:
        return None
    doi = found.group().rstrip(".,;:")
    # Balanced parentheses are valid DOI characters, unmatched closing delimiters aren't.
    for left, right in [("(", ")"), ("[", "]"), ("{", "}")]:
        while doi.endswith(right) and doi.count(right) > doi.count(left):
            doi = doi[:-1]
    return doi.lower() or None


@dataclass
class ParsedPdf:
    title: str
    authors: list[str] = field(default_factory=list)
    doi: str | None = None
    journal: str | None = None
    publication_year: int | None = None
    abstract: str | None = None
    pages: list[str] = field(default_factory=list)
    page_count: int = 0
    warning: str | None = None


class PdfParser(ABC):
    @abstractmethod
    def parse_metadata(self) -> ParsedPdf: ...

    @abstractmethod
    def extract_pages(self) -> list[str]: ...

    def extract_text(self) -> str:
        return "\n\n".join(self.extract_pages())

    def extract_references(self) -> list[dict]:
        """Reserved for a structured parser such as GROBID; never infer citations from proximity."""
        return []


class SimplePdfParser(PdfParser):
    MAX_PAGES = 300
    MAX_PAGE_CHARS = 100_000

    def __init__(self, path: Path):
        self.path = path
        self.reader = PdfReader(path, strict=False)
        if self.reader.is_encrypted and not self.reader.decrypt(""):
            raise ValueError("This PDF is password protected.")
        self._pages: list[str] | None = None
        self._warnings: list[str] = []

    def extract_pages(self) -> list[str]:
        if self._pages is None:
            self._pages = []
            for index, page in enumerate(self.reader.pages):
                if index >= self.MAX_PAGES:
                    self._warnings.append("Text extraction limited to the first 300 pages.")
                    break
                try:
                    # Bound decompressed content to avoid pathological PDF content streams.
                    contents = page.get_contents()
                    if contents is not None and len(contents.get_data()) > 20_000_000:
                        self._pages.append("")
                        self._warnings.append(f"Page {index + 1} exceeds the extraction limit.")
                        continue
                    self._pages.append((page.extract_text() or "")[: self.MAX_PAGE_CHARS])
                except Exception:
                    logging.getLogger(__name__).exception(
                        "pdf_page_extraction_failed page=%s path=%s", index + 1, self.path
                    )
                    self._pages.append("")
                    self._warnings.append(f"Could not extract page {index + 1}.")
        return self._pages

    def parse_metadata(self) -> ParsedPdf:
        meta = self.reader.metadata or {}
        title = str(meta.get("/Title") or "").strip()
        if len(title) < 4 or title.lower() in {"untitled", "microsoft word", "document"}:
            title = self.path.stem.replace("_", " ")
        raw_authors = str(meta.get("/Author") or "").strip()
        authors = [a.strip() for a in re.split(r";|\s+and\s+|\n", raw_authors) if a.strip()]
        pages = self.extract_pages()
        body = "\n\n".join(pages)
        doi = normalize_doi(" ".join(str(v) for v in meta.values())) or normalize_doi(
            pages[0] if pages else ""
        )
        doi = doi or normalize_doi(body)
        # CreationDate is file provenance, not a reliable publication date. Leave year unknown.
        abstract_match = re.search(
            r"\babstract\b[\s:.-]+(.{80,4000}?)(?=\n\s*(?:keywords|introduction|1[. ]+introduction)\b|\Z)",
            "\n\n".join(pages[:2]),
            re.IGNORECASE | re.DOTALL,
        )
        abstract = re.sub(r"\s+", " ", abstract_match.group(1)).strip() if abstract_match else None
        if not body.strip():
            self._warnings.append("No extractable text. This PDF may require OCR.")
        return ParsedPdf(
            title=title,
            authors=authors[:100],
            doi=doi,
            abstract=abstract,
            pages=pages,
            page_count=len(self.reader.pages),
            warning=" ".join(dict.fromkeys(self._warnings)) or None,
        )
