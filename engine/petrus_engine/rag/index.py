"""Rebuildable SQLite float32 vectors, validated against current EvidenceUnits at read time."""

import hashlib
import json
from dataclasses import asdict

import numpy as np

from petrus_engine.rag.evidence import EvidenceRepository, subdivide_span


def content_hash(unit):
    # Includes provenance/identity to catch source row ID reuse after scientific reprocessing.
    return hashlib.sha256(json.dumps(asdict(unit), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def checked_vector(value, dimension=None):
    vector = np.asarray(value, dtype="<f4")
    if (
        vector.ndim != 1
        or not vector.size
        or (dimension is not None and vector.size != dimension)
        or not np.isfinite(vector).all()
        or not np.linalg.norm(vector.astype("float64"))
    ):
        raise ValueError("embedding_invalid_vector_or_dimension")
    return vector


def available_ids(database):
    with database.connect() as db:
        return [
            r[0]
            for r in db.execute(
                "SELECT DISTINCT paper_id FROM paper_files WHERE available=1 AND paper_id IS NOT NULL ORDER BY paper_id"
            )
        ]


def current_units(database, max_chars=None):
    if max_chars is None:
        with database.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key='embedding_max_chars'").fetchone()
        max_chars = json.loads(row[0]) if row else 6000
    repository = EvidenceRepository(database)
    return {
        child.unit_id: child
        for paper in available_ids(database)
        for u in repository.iter_units(paper)
        for child in subdivide_span(u, max_chars)
    }


class SQLiteVectorIndex:
    def __init__(self, database, provider, max_chars=None):
        self.database, self.provider = database, provider
        self.max_chars = max_chars

    def upsert(self, unit, vector, fingerprint):
        vector = checked_vector(vector, self.provider.dimension)
        with self.database.connect() as db:
            dimensions = {
                r[0]
                for r in db.execute(
                    "SELECT DISTINCT dimension FROM embedding_index WHERE provider_id=? AND model_id=?",
                    (self.provider.provider_id, self.provider.model_id),
                )
            }
            if dimensions and dimensions != {len(vector)}:
                raise ValueError("embedding_dimension_mismatch_rebuild_required")
            db.execute(
                """INSERT INTO embedding_index(unit_id,paper_id,provider_id,model_id,dimension,content_hash,vector_blob)
                VALUES(?,?,?,?,?,?,?) ON CONFLICT(unit_id,provider_id,model_id) DO UPDATE SET
                paper_id=excluded.paper_id,dimension=excluded.dimension,content_hash=excluded.content_hash,
                vector_blob=excluded.vector_blob,updated_at=CURRENT_TIMESTAMP""",
                (
                    unit.unit_id,
                    unit.paper_id,
                    self.provider.provider_id,
                    self.provider.model_id,
                    len(vector),
                    fingerprint,
                    vector.tobytes(),
                ),
            )

    def search(self, vector, limit=10, include_bibliography=True):
        query = checked_vector(vector, self.provider.dimension)
        units = current_units(self.database, self.max_chars)
        with self.database.connect() as db:
            rows = db.execute(
                """SELECT unit_id,content_hash,vector_blob FROM embedding_index
                WHERE provider_id=? AND model_id=? AND dimension=? ORDER BY unit_id""",
                (self.provider.provider_id, self.provider.model_id, len(query)),
            ).fetchall()
        rows = [
            r
            for r in rows
            if r["unit_id"] in units
            and r["content_hash"] == content_hash(units[r["unit_id"]])
            and (
                include_bibliography or units[r["unit_id"]].evidence_role not in ("bibliography", "metadata")
            )
        ]
        if not rows:
            return []
        # One vectorized matrix operation, not a Python loop computing cosine per row.
        matrix = (
            np.frombuffer(b"".join(r["vector_blob"] for r in rows), dtype="<f4")
            .reshape(len(rows), -1)
            .astype("float64")
        )
        query = query.astype("float64")
        norms = np.linalg.norm(matrix, axis=1)
        if not np.isfinite(matrix).all() or np.any(norms == 0):
            raise ValueError("embedding_invalid_stored_vector")
        scores = np.clip((matrix @ query) / (norms * np.linalg.norm(query)), -1, 1)
        return sorted(
            zip((r["unit_id"] for r in rows), scores.tolist()), key=lambda pair: (-pair[1], pair[0])
        )[:limit]


class EmbeddingIndexService:
    def __init__(self, database, provider, max_chars=None):
        self.database, self.provider = database, provider
        with database.connect() as db:
            configured = db.execute("SELECT value FROM settings WHERE key='embedding_max_chars'").fetchone()
        self.max_chars = max_chars or (
            json.loads(configured[0]) if configured else getattr(provider, "max_chars", 6000)
        )
        self.index = SQLiteVectorIndex(database, provider, self.max_chars)

    def index_paper(self, paper_id):
        if paper_id not in available_ids(self.database):
            raise ValueError("embedding_paper_unavailable")
        units = [
            child
            for unit in EvidenceRepository(self.database).iter_units(paper_id)
            for child in subdivide_span(unit, self.max_chars)
        ]
        result = {"indexed": 0, "cached": 0, "warnings": []}
        for unit in units:
            fingerprint = content_hash(unit)
            if len(unit.text) > self.max_chars:
                result["warnings"].append(
                    {
                        "code": "embedding_unit_too_large",
                        "unit_id": unit.unit_id,
                        "characters": len(unit.text),
                    }
                )
                with self.database.connect() as db:
                    db.execute(
                        "DELETE FROM embedding_index WHERE unit_id=? AND provider_id=? AND model_id=?",
                        (unit.unit_id, self.provider.provider_id, self.provider.model_id),
                    )
                continue
            with self.database.connect() as db:
                previous = db.execute(
                    """SELECT content_hash,dimension FROM embedding_index
                    WHERE unit_id=? AND provider_id=? AND model_id=?""",
                    (unit.unit_id, self.provider.provider_id, self.provider.model_id),
                ).fetchone()
            if (
                previous
                and previous["content_hash"] == fingerprint
                and self.provider.dimension in (None, previous["dimension"])
            ):
                result["cached"] += 1
                continue
            vectors = self.provider.embed_documents([unit.text])
            if len(vectors) != 1:
                raise ValueError("embedding_response_count")
            # Never persist a vector for text/provenance changed while the request was running.
            current = {
                child.unit_id: child
                for u in EvidenceRepository(self.database).iter_units(paper_id)
                for child in subdivide_span(u, self.max_chars)
            }
            if unit.unit_id not in current or content_hash(current[unit.unit_id]) != fingerprint:
                result["warnings"].append({"code": "embedding_unit_changed", "unit_id": unit.unit_id})
                continue
            self.index.upsert(unit, vectors[0], fingerprint)
            result["indexed"] += 1
        self.remove_stale()
        return result

    def index_all_available(self):
        return {str(paper): self.index_paper(paper) for paper in available_ids(self.database)}

    def clear(self):
        """Explicit rebuild boundary for this provider/model, leaving source evidence intact."""
        with self.database.connect() as db:
            cursor = db.execute(
                "DELETE FROM embedding_index WHERE provider_id=? AND model_id=?",
                (self.provider.provider_id, self.provider.model_id),
            )
            return cursor.rowcount

    def remove_stale(self):
        units = current_units(self.database, self.max_chars)
        with self.database.connect() as db:
            stale = [
                r["id"]
                for r in db.execute("SELECT id,unit_id,content_hash FROM embedding_index")
                if r["unit_id"] not in units or r["content_hash"] != content_hash(units[r["unit_id"]])
            ]
            db.executemany("DELETE FROM embedding_index WHERE id=?", ((i,) for i in stale))
        return len(stale)

    def status(self):
        units = current_units(self.database, self.max_chars)
        with self.database.connect() as db:
            rows = db.execute(
                "SELECT * FROM embedding_index WHERE provider_id=? AND model_id=?",
                (self.provider.provider_id, self.provider.model_id),
            ).fetchall()
        current = [
            r
            for r in rows
            if r["unit_id"] in units
            and r["content_hash"] == content_hash(units[r["unit_id"]])
            and self.provider.dimension in (None, r["dimension"])
        ]
        return {
            "provider_id": self.provider.provider_id,
            "model_id": self.provider.model_id,
            "stored": len(rows),
            "current": len(current),
            "stale_or_incompatible": len(rows) - len(current),
            "dimensions": sorted({r["dimension"] for r in current}),
        }
