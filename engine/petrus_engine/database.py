"""SQLite ownership, migration ledger and short-lived per-thread connections."""

import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        migrations = (
            Path(sys._MEIPASS) / "migrations"
            if hasattr(sys, "_MEIPASS")
            else Path(__file__).resolve().parents[2] / "src-tauri" / "migrations"
        )
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)")
            for migration in sorted(migrations.glob("*.sql")):
                if not db.execute(
                    "SELECT 1 FROM schema_migrations WHERE version=?", (migration.name,)
                ).fetchone():
                    # executescript commits pending transactions; wrap the entire migration explicitly.
                    escaped = migration.name.replace("'", "''")
                    db.executescript(
                        "BEGIN IMMEDIATE;\n"
                        + migration.read_text()
                        + f"\nINSERT INTO schema_migrations VALUES ('{escaped}');\nCOMMIT;"
                    )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=30000")
        try:
            with db:
                yield db
        finally:
            db.close()
