"""Typed citations, metadata relations and bounded local derived relatedness."""

from petrus_engine.graph.relatedness import RelatednessService


def build_graph(db, limit=300):
    visible = "SELECT id FROM papers p WHERE EXISTS(SELECT 1 FROM paper_files f WHERE f.paper_id=p.id) ORDER BY updated_at DESC,id DESC LIMIT ?"
    papers = db.execute(
        "SELECT id,title FROM papers WHERE id IN (" + visible + ") ORDER BY id", (limit,)
    ).fetchall()
    ids = {p["id"] for p in papers}
    edges = []
    for table, key, label in [
        ("paper_authors", "author_id", "Shared author"),
        ("collection_papers", "collection_id", "Same collection"),
    ]:
        rows = db.execute(
            f"""SELECT a.paper_id AS source,b.paper_id AS target,a.{key} AS group_id
            FROM {table} a JOIN {table} b ON a.{key}=b.{key} AND a.paper_id<b.paper_id
            WHERE a.paper_id IN ({visible})
            AND b.paper_id IN ({visible})
            LIMIT 2000""",
            (limit, limit),
        ).fetchall()
        for row in rows:
            if row["source"] in ids and row["target"] in ids:
                edges.append(
                    {
                        "source": str(row["source"]),
                        "target": str(row["target"]),
                        "relation": label,
                        "type": "SHARED_AUTHOR" if table == "paper_authors" else "SAME_COLLECTION",
                        "id": f"{table}-{row['source']}-{row['target']}-{row['group_id']}",
                    }
                )
    for row in db.execute("""SELECT e.*,r.*,s.title AS source_title,t.title AS target_title FROM edges e
        JOIN "references" r ON r.id=e.reference_id JOIN papers s ON s.id=e.source_id
        JOIN papers t ON t.id=e.target_id WHERE e.relation='CITES' AND r.resolution_status='resolved' LIMIT 4000"""):
        if row["source_id"] in ids and row["target_id"] in ids:
            edges.append(
                {
                    "id": f"cites-{row['reference_id']}",
                    "source": str(row["source_id"]),
                    "target": str(row["target_id"]),
                    "relation": "CITES",
                    "type": "CITES",
                    "reference": dict(row),
                }
            )
    for relation in RelatednessService(db).relations(ids):
        source, target = relation["source_paper_id"], relation["target_paper_id"]
        kind = relation["relation_type"]
        edges.append(
            {
                "id": f"{kind}-{source}-{target}",
                "source": str(source),
                "target": str(target),
                "relation": kind,
                "type": kind,
                "score": relation["score"],
                "metadata": relation["metadata"],
            }
        )
    return {
        "nodes": [{"id": str(p["id"]), "label": p["title"]} for p in papers],
        "edges": edges,
        "limit": limit,
    }
