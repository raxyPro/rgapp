from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import text

from app import create_app
from extensions import db


MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations_sql")


def ensure_tracker_table():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS rb_schema_migrations (
          filename VARCHAR(255) NOT NULL PRIMARY KEY,
          applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.session.commit()


def applied_filenames() -> set[str]:
    rows = db.session.execute(text("SELECT filename FROM rb_schema_migrations")).fetchall()
    return {r[0] for r in rows}


def apply_migrations():
    ensure_tracker_table()
    already = applied_filenames()

    files = sorted(
        f for f in os.listdir(MIGRATIONS_DIR)
        if f.endswith(".sql") and not f.startswith("_")
    )

    to_apply = [f for f in files if f not in already]
    if not to_apply:
        print("No new SQL migrations to apply.")
        return

    for fname in to_apply:
        path = os.path.join(MIGRATIONS_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            sql = f.read().strip()
        if not sql:
            continue

        print(f"Applying {fname} ...")
        # Split-on-semicolon is risky; we execute as one block.
        db.session.execute(text(sql))
        db.session.execute(
            text("INSERT INTO rb_schema_migrations (filename, applied_at) VALUES (:f, :t)"),
            {"f": fname, "t": datetime.utcnow()},
        )
        db.session.commit()

    print("Done.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        apply_migrations()
