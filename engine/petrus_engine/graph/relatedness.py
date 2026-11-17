"""Deterministic local relatedness, never evidence, agreement or causality."""

import math
import re
import unicodedata
from collections import Counter, defaultdict
from enum import StrEnum
from itertools import combinations

from petrus_engine.pdf.parser import normalize_doi
from petrus_engine.references import normalize_title


class RelatednessType(StrEnum):
    TITLE_SIMILARITY = "TITLE_SIMILARITY"
    SHARED_KEYWORDS = "SHARED_KEYWORDS"
    SHARED_REFERENCES = "SHARED_REFERENCES"
    SEMANTIC_SIMILARITY = "SEMANTIC_SIMILARITY"  # Generated through the bounded centroid service.


STOPWORDS = set(
    """the and for with from into between among this that these those their using
of to in on at by an as is are was were not our its via can may new a comparative comparison
study studies analysis analyses results result virus viruses viral paper papers method methods
research effect effects investigation approach findings introduction discussion conclusion
artigo artigos estudo estudos analise analises resultados resultado virus viral virais metodo
metodos pesquisa abordagem efeito efeitos sobre entre com sem para por uma um uns umas dos das
nos nas aos as os de da do e em o a ao no na pelo pela sua seu suas seus este esta estes estas
isso isto como mais nao sao foi ser foram uso utilizando avaliacao assessment evaluation
""".split()
)


def terms(value):
    value = "".join(
        c for c in unicodedata.normalize("NFKD", (value or "").casefold()) if not unicodedata.combining(c)
    )
    return {
        t for t in re.findall(r"[^\W_]+", value) if len(t) >= 4 and not t.isdigit() and t not in STOPWORDS
    }


def reference_key(doi, title):
    normalized = normalize_doi(doi)
    if normalized:
        return "doi:" + normalized
    title = normalize_title(title)
    if len(title) >= 30 and len(title.split()) >= 5:
        return "title:" + title
    return None


def candidates(features):
    """Only pairs sharing a feature; ubiquitous postings are deliberately excluded."""
    inverted = defaultdict(list)
    for paper_id, values in sorted(features.items()):
        for value in sorted(values):
            inverted[value].append(paper_id)
    pairs = set()
    posting_limit = max(40, int(len(features) * 0.25))
    for ids in inverted.values():
        if len(ids) <= posting_limit:
            pairs.update(combinations(ids, 2))
    return sorted(pairs)


def weighted_jaccard(a, b, weights):
    union = a | b
    return sum(weights[t] for t in a & b) / sum(weights[t] for t in union) if union else 0.0


class RelatednessService:
    MAX_PER_TYPE = 300
    MAX_PER_PAPER = 6

    def __init__(self, db):
        self.db = db

    def semantic_relations(self, paper_ids, units, provider):
        from petrus_engine.graph.semantic import semantic_relations

        return semantic_relations(self.db, units, provider, paper_ids)

    def relations(self, paper_ids):
        ids = sorted(set(paper_ids))
        if len(ids) < 2:
            return []
        marks = ",".join("?" for _ in ids)
        papers = [
            dict(p)
            for p in self.db.execute(
                f"SELECT id,title,abstract FROM papers WHERE id IN ({marks}) ORDER BY id", ids
            )
        ]
        titles = {p["id"]: terms(p["title"]) for p in papers}
        corpus = {p["id"]: terms((p["title"] or "") + " " + (p["abstract"] or "")) for p in papers}
        title_frequency = Counter(t for values in titles.values() for t in values)
        title_weights = {
            t: 1 + math.log((1 + len(papers)) / (1 + count)) for t, count in title_frequency.items()
        }
        frequency = Counter(t for values in corpus.values() for t in values)
        weights = {t: 1 + math.log((1 + len(papers)) / (1 + count)) for t, count in frequency.items()}
        keywords = {
            pid: set(
                sorted(
                    (t for t in values if len(papers) < 5 or frequency[t] / len(papers) <= 0.6),
                    key=lambda t: (-weights[t], t),
                )[:12]
            )
            for pid, values in corpus.items()
        }
        refs = {pid: set() for pid in ids}
        examples = {}
        for ref in self.db.execute(
            f'SELECT source_paper_id,doi,title FROM "references" WHERE source_paper_id IN ({marks}) ORDER BY id',
            ids,
        ):
            key = reference_key(ref["doi"], ref["title"])
            if key:
                refs[ref["source_paper_id"]].add(key)
                examples.setdefault(key, {"doi": normalize_doi(ref["doi"]), "title": ref["title"]})
        output = []
        for kind, features in (
            (RelatednessType.TITLE_SIMILARITY, titles),
            (RelatednessType.SHARED_KEYWORDS, keywords),
            (RelatednessType.SHARED_REFERENCES, refs),
        ):
            edges = []
            for source, target in candidates(features):
                a, b = features[source], features[target]
                shared = sorted(a & b)
                score = (
                    (len(shared) / len(a | b) if a | b else 0)
                    if kind == RelatednessType.SHARED_REFERENCES
                    else weighted_jaccard(
                        a, b, title_weights if kind == RelatednessType.TITLE_SIMILARITY else weights
                    )
                )
                minimum, threshold = {
                    RelatednessType.TITLE_SIMILARITY: (3, 0.65),
                    RelatednessType.SHARED_KEYWORDS: (3, 0.20),
                    RelatednessType.SHARED_REFERENCES: (2, 0.05),
                }[kind]
                if len(shared) < minimum or score < threshold:
                    continue
                metadata = {"score": round(score, 4)}
                if kind == RelatednessType.SHARED_REFERENCES:
                    metadata.update(
                        shared_reference_count=len(shared), examples=[examples[k] for k in shared[:5]]
                    )
                else:
                    metadata.update(shared_terms=shared[:10], count=len(shared), term_source="derived_term")
                edges.append(
                    {
                        "source_paper_id": source,
                        "target_paper_id": target,
                        "relation_type": kind.value,
                        "score": round(score, 4),
                        "metadata": metadata,
                    }
                )
            degree = Counter()
            count = 0
            for edge in sorted(
                edges, key=lambda e: (-e["score"], e["source_paper_id"], e["target_paper_id"])
            ):
                a, b = edge["source_paper_id"], edge["target_paper_id"]
                if degree[a] >= self.MAX_PER_PAPER or degree[b] >= self.MAX_PER_PAPER:
                    continue
                output.append(edge)
                degree[a] += 1
                degree[b] += 1
                count += 1
                if count >= self.MAX_PER_TYPE:
                    break
        return output
