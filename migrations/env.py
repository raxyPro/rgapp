from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    import configparser

    if config.config_file_name:
        cp = configparser.ConfigParser()
        cp.read(config.config_file_name)
        # Only configure logging if alembic.ini contains logging sections
        if cp.has_section("formatters"):
            fileConfig(config.config_file_name)

# Import app + SQLAlchemy metadata
from app import create_app
from extensions import db

app = create_app()

# Make sure models are imported so metadata is complete
import models  # noqa: F401

target_metadata = db.metadata


def get_url():
    # Prefer Alembic ini sqlalchemy.url if user set it; fallback to app config.
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url and ini_url != "driver://user:pass@localhost/dbname":
        return ini_url
    return app.config.get("SQLALCHEMY_DATABASE_URI")


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Ensure app context so SQLAlchemy config is available
    with app.app_context():
        run_migrations_online()
