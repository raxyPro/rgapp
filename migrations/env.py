from __future__ import with_statement

import sys
from logging.config import fileConfig
from pathlib import Path
import configparser

from alembic import context
from sqlalchemy import engine_from_config, pool

# -------------------------------------------------------------------
# Alembic Config object
# -------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
# Disable alembic.ini logging config (prevents KeyError: 'formatters')
# You can configure logging later if needed.
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)


# -------------------------------------------------------------------
# Make sure app modules are importable
# Assuming:
#   project_root/
#     app.py
#     config.py
#     models.py
#     extensions.py
#     migrations/
#       env.py  <-- this file
# -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Import your SQLAlchemy Base/metadata
# If you're using Flask-SQLAlchemy, metadata is db.metadata
from extensions import db  # noqa: E402
from models import RBUser, RBUserProfile, RBAudit  # noqa: F401,E402  (ensure models are imported)

target_metadata = db.metadata

# -------------------------------------------------------------------
# Read DATABASE URL from app.ini
# -------------------------------------------------------------------
APP_INI_PATH = PROJECT_ROOT / "app.ini"
if not APP_INI_PATH.exists():
    raise RuntimeError(f"app.ini not found at: {APP_INI_PATH}")

cp = configparser.ConfigParser()
cp.read(APP_INI_PATH)

db_url = cp.get("database", "sqlalchemy_database_uri", fallback=None)
if not db_url:
    raise RuntimeError("Missing [database] sqlalchemy_database_uri in app.ini")

# Override alembic sqlalchemy.url with app.ini value
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,          # detect column type changes
        compare_server_default=True # detect default changes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
