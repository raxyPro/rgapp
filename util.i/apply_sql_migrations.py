from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import text

from app import create_app
from extensions import db

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations_sql")


def ensure_tracker_table():
    # Keep this in-sync with migrations_sql/0001_baseline.sql
    db.session.execute(text("""
    CREATE TABLE IF NOT EXISTS rb_schema_migrations (
      filename VARCHAR(255) NOT NULL PRIMARY KEY,
      applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """))
    db.session.commit()


def applied_filenames() -> set[str]:
    ensure_tracker_table()
    rows = db.session.execute(text("SELECT filename FROM rb_schema_migrations")).fetchall()
    return {r[0] for r in rows}


def apply_migrations():
    ensure_tracker_table()
    already = applied_filenames()

    if not os.path.isdir(MIGRATIONS_DIR):
        print(f"No migrations directory: {MIGRATIONS_DIR}")
        return

    fnames = sorted([f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")])
    to_apply = [f for f in fnames if f not in already]

    if not to_apply:
        print("No pending migrations.")
        return

    for fname in to_apply:
        fpath = os.path.join(MIGRATIONS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            sql = f.read().strip()

        if not sql:
            continue

        # Execute statements sequentially to allow multi-statement files.
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        for stmt in statements:
            db.session.execute(text(stmt))
        db.session.execute(
            text("INSERT INTO rb_schema_migrations (filename, applied_at) VALUES (:f, :t)"),
            {"f": fname, "t": datetime.utcnow()},
        )
        db.session.commit()
        print(f"Applied: {fname}")

    print("Done.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        apply_migrations()
