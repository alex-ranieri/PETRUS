"""Bounded paper centroids from current compatible scientific-content embeddings."""

from collections import defaultdict

import numpy as np

from petrus_engine.rag.index import content_hash

SEMANTIC_THRESHOLD = 0.85
CENTROID_UNITS = 12


def paper_centroids(db, units, provider, paper_ids):
    grouped = defaultdict(list)
    priority = {"abstract": 0, "body": 1, "methods": 2, "results": 3, "discussion": 4, "conclusion": 5}
    for row in db.execute(
        "SELECT unit_id,content_hash,dimension,vector_blob FROM embedding_index WHERE provider_id=? AND model_id=? ORDER BY unit_id",
        (provider.provider_id, provider.model_id),
    ):
        unit = units.get(row["unit_id"])
        if (
            unit is None
            or unit.paper_id not in paper_ids
            or unit.evidence_role not in priority
            or len(unit.text.strip()) < 80
            or row["content_hash"] != content_hash(unit)
        ):
            continue
        if provider.dimension is not None and row["dimension"] != provider.dimension:
            continue
        grouped[unit.paper_id].append((priority[unit.evidence_role], unit.unit_id, row))
    dimensions = {r["dimension"] for rows in grouped.values() for _, _, r in rows}
    if len(dimensions) != 1:
        return {}
    output = {}
    for pid, rows in grouped.items():
        matrix = np.stack(
            [
                np.frombuffer(r["vector_blob"], dtype="<f4").astype("float64")
                for _, _, r in sorted(rows, key=lambda item: (item[0], item[1]))[:CENTROID_UNITS]
            ]
        )
        norms = np.linalg.norm(matrix, axis=1)
        if not np.isfinite(matrix).all() or np.any(norms == 0):
            continue
        mean = (matrix / norms[:, None]).mean(axis=0)
        norm = np.linalg.norm(mean)
        if norm:
            output[pid] = mean / norm
    return output


def semantic_relations(db, units, provider, paper_ids):
    centers = paper_centroids(db, units, provider, set(paper_ids))
    ids = sorted(centers)
    if len(ids) < 2:
        return []
    matrix = np.stack([centers[i] for i in ids])
    pairs = {}
    for start in range(0, len(ids), 128):
        scores = matrix[start : start + 128] @ matrix.T
        for offset, row in enumerate(scores):
            source = start + offset
            eligible = [i for i in range(source + 1, len(ids)) if row[i] >= SEMANTIC_THRESHOLD]
            for target in sorted(eligible, key=lambda i: (-row[i], ids[i]))[:6]:
                pairs[(ids[source], ids[target])] = float(np.clip(row[target], -1, 1))
    edges = []
    degree = defaultdict(int)
    for (a, b), score in sorted(pairs.items(), key=lambda item: (-item[1], item[0])):
        if degree[a] >= 6 or degree[b] >= 6:
            continue
        edges.append(
            {
                "source_paper_id": a,
                "target_paper_id": b,
                "relation_type": "SEMANTIC_SIMILARITY",
                "score": round(score, 4),
                "metadata": {
                    "score": round(score, 4),
                    "computed_from": "semantic_content",
                    "model_id": provider.model_id,
                    "centroid_max_units": CENTROID_UNITS,
                },
            }
        )
        degree[a] += 1
        degree[b] += 1
        if len(edges) == 300:
            break
    return edges
