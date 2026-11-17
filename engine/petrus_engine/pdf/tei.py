"""TEI extraction with conservative, explicit PDF page provenance. No translation or inference."""

import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict

from petrus_engine.pdf.parser import normalize_doi

NS = {"t": "http://www.tei-c.org/ns/1.0"}
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def text(node):
    return re.sub(r"\s+", " ", "".join(node.itertext())).strip() if node is not None else ""


def heading_type(heading):
    value = "".join(
        c for c in unicodedata.normalize("NFKD", heading.casefold()) if not unicodedata.combining(c)
    )
    value = re.sub(r"^[\d\W]+", "", value)
    value = re.sub(r"[^\w]+", " ", value).strip()
    groups = {
        "abstract": ("abstract", "resumo"),
        "introduction": ("introduction", "introducao", "background"),
        "methods": (
            "methods",
            "materials and methods",
            "materials methods",
            "experimental procedures",
            "methodology",
            "metodos",
            "materiais e metodos",
            "metodologia",
        ),
        "results": ("results", "resultados"),
        "discussion": ("discussion", "discussao"),
        "conclusion": ("conclusion", "conclusions", "conclusao", "conclusoes"),
        "references": ("references", "bibliography", "referencias", "referencias bibliograficas"),
    }
    return next((kind for kind, values in groups.items() if value in values), "other")


class PageMapper:
    def __init__(self, pages):
        self.pages = pages
        self.tokens, self.locations, self.starts = [], [], defaultdict(list)
        for page, value in enumerate(pages, 1):
            for match in re.finditer(r"\w+", value):
                token = unicodedata.normalize("NFKC", match.group()).casefold()
                self.starts[token].append(len(self.tokens))
                self.tokens.append(token)
                self.locations.append((page, match.start(), match.end()))

    def map(self, node):
        value = text(node)
        boxes = []
        for coordinate in node.get("coords", "").split(";"):
            try:
                parts = [float(v) for v in coordinate.split(",")]
                page = int(parts[0])
                if (
                    len(parts) == 5
                    and parts[0] == page
                    and 1 <= page <= len(self.pages)
                    and all(v >= 0 for v in parts[1:])
                ):
                    boxes.append(
                        {"page": page, "x": parts[1], "y": parts[2], "width": parts[3], "height": parts[4]}
                    )
            except (ValueError, IndexError, OverflowError):
                continue
        if boxes and len({box["page"] for box in boxes}) == 1:
            return [
                {
                    "page": boxes[0]["page"],
                    "char_start": None,
                    "char_end": None,
                    "text": value,
                    "source_type": "grobid_coordinates",
                    "coordinates": boxes,
                }
            ]
        words = [unicodedata.normalize("NFKC", m.group()).casefold() for m in re.finditer(r"\w+", value)]
        if len(words) < 6 or len(value) < 35:
            return []
        matches = [i for i in self.starts.get(words[0], []) if self.tokens[i : i + len(words)] == words]
        if len(matches) != 1:
            return []
        start = matches[0]
        mapped = defaultdict(list)
        for page, first, last in self.locations[start : start + len(words)]:
            mapped[page].append((first, last))
        spans = []
        for page, offsets in mapped.items():
            first, last = offsets[0][0], offsets[-1][1]
            spans.append(
                {
                    "page": page,
                    "char_start": first,
                    "char_end": last,
                    "text": self.pages[page - 1][first:last],
                    "source_type": "page_text_alignment",
                    "coordinates": [b for b in boxes if b["page"] == page] or None,
                }
            )
        return spans


def names(node):
    if node is None:
        return []
    result = []
    for author in node.findall(".//t:author", NS):
        person = author.find("t:persName", NS)
        result.append(" ".join(text(child) for child in person) if person is not None else text(author))
    return [name for name in result if name]


def doi(node):
    return next(
        (
            normalize_doi(text(e))
            for e in node.findall(".//t:idno", NS)
            if e.get("type", "").casefold() == "doi" and normalize_doi(text(e))
        ),
        None,
    )


def year(node):
    for element in node.findall(".//t:date", NS):
        match = re.search(r"\b((?:18|19|20)\d{2})\b", element.get("when", "") or text(element))
        if match:
            return int(match.group(1))
    return None


def parse_tei(xml: str, pages: list[str]):
    if len(xml) > 30_000_000 or re.search(r"<!\s*(?:DOCTYPE|ENTITY)", xml, re.IGNORECASE):
        raise ValueError("errors.invalidTei")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError("errors.invalidTei") from exc
    header = root.find("t:teiHeader", NS)
    if root.tag != "{http://www.tei-c.org/ns/1.0}TEI" or header is None or root.find("t:text", NS) is None:
        raise ValueError("errors.invalidTei")
    article = header.find(".//t:sourceDesc/t:biblStruct", NS)
    if article is None:
        article = header
    title = text(article.find("t:analytic/t:title", NS)) or text(header.find(".//t:titleStmt/t:title", NS))
    metadata = {
        "title": title or None,
        "authors": names(article),
        "doi": doi(article),
        "journal": text(article.find('t:monogr/t:title[@level="j"]', NS)) or None,
        "publication_year": year(article),
        "abstract": None,
    }
    mapper = PageMapper(pages)
    sections, references, warnings = [], [], []

    def add_section(node, parent=None, force_type=None):
        heading = text(node.find("t:head", NS))
        blocks = [
            child for child in node if child.tag.split("}")[-1] in ("p", "ab", "list", "figure", "formula")
        ]
        content = "\n\n".join(text(block) for block in blocks if text(block))
        if not blocks and not node.findall("t:div", NS):
            content = text(node)
            blocks = [node] if content else []
        spans = []
        all_mapped = bool(blocks)
        for block in blocks:
            mapped = mapper.map(block)
            spans.extend(mapped)
            all_mapped = all_mapped and bool(mapped)
        index = len(sections)
        section = {
            "parent": parent,
            "section_type": force_type or heading_type(heading),
            "heading": heading,
            "section_order": index,
            "text": content,
            "tei_id": node.get(XML_ID),
            "spans": spans,
            "page_start": min((s["page"] for s in spans), default=None) if all_mapped else None,
            "page_end": max((s["page"] for s in spans), default=None) if all_mapped else None,
        }
        sections.append(section)
        for child in node.findall("t:div", NS):
            add_section(child, index)
        children = [s for s in sections if s["parent"] == index]
        if children:
            complete = all(s["page_start"] is not None for s in children) and (not blocks or all_mapped)
            if complete:
                section["page_start"] = min([s["page_start"] for s in children] + [s["page"] for s in spans])
                section["page_end"] = max([s["page_end"] for s in children] + [s["page"] for s in spans])
            else:
                section["page_start"] = section["page_end"] = None
        if section["page_start"] is None and content:
            warnings.append("warnings.unmappedSection")

    abstract = header.find(".//t:profileDesc/t:abstract", NS)
    if abstract is not None:
        metadata["abstract"] = text(abstract) or None
        add_section(abstract, force_type="abstract")
    body = root.find("t:text/t:body", NS)
    if body is not None:
        if any(child.tag.endswith("}p") for child in body):
            # A body wrapper retains paragraphs which have no div; divs still retain their hierarchy.
            add_section(body)
        else:
            for div in body.findall("t:div", NS):
                add_section(div)
    for order, bibl in enumerate(root.findall(".//t:listBibl/t:biblStruct", NS), 1):
        raw = next((text(n) for n in bibl.findall("t:note", NS) if n.get("type") == "raw_reference"), "")
        references.append(
            {
                "citation_order": order,
                "raw_citation": raw or text(bibl),
                "title": text(bibl.find("t:analytic/t:title", NS))
                or text(bibl.find("t:monogr/t:title", NS))
                or None,
                "authors_text": "; ".join(names(bibl)) or None,
                "journal": text(bibl.find('t:monogr/t:title[@level="j"]', NS)) or None,
                "year": year(bibl),
                "doi": doi(bibl),
                "tei_id": bibl.get(XML_ID),
                "spans": mapper.map(bibl),
            }
        )
    refs_by_id = {ref["tei_id"]: ref for ref in references if ref["tei_id"]}
    for citation in root.findall('.//t:body//t:ref[@type="bibr"]', NS):
        for target in citation.get("target", "").split():
            if target.lstrip("#") in refs_by_id:
                refs_by_id[target.lstrip("#")]["spans"].extend(mapper.map(citation))
    return {
        "metadata": metadata,
        "sections": sections,
        "references": references,
        "warnings": sorted(set(warnings)),
        "tei_xml": xml,
    }
