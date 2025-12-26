"""Add module registry and user-module access mapping

Revision ID: 20251226_01
Revises: 
Create Date: 2025-12-26

"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = "20251226_01"
down_revision = None
branch_labels = None
dependencies = None


def upgrade():
    op.create_table(
        "rb_module",
        sa.Column("module_key", sa.String(length=50), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "rb_user_module",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("rb_user.user_id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "module_key",
            sa.String(length=50),
            sa.ForeignKey("rb_module.module_key", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("has_access", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("granted_by", sa.BigInteger(), nullable=True),
        sa.Column("granted_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "module_key", name="uq_rb_user_module"),
    )

    # Seed default modules
    now = datetime.utcnow()
    rb_module = sa.table(
        "rb_module",
        sa.Column("module_key", sa.String(length=50)),
        sa.Column("name", sa.String(length=120)),
        sa.Column("description", sa.String(length=255)),
        sa.Column("is_enabled", sa.Boolean()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    op.bulk_insert(
        rb_module,
        [
            {
                "module_key": "cv",
                "name": "CV Module",
                "description": "CV creation and management",
                "is_enabled": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "module_key": "chat",
                "name": "Chat Module",
                "description": "Chat experience (placeholder)",
                "is_enabled": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "module_key": "social",
                "name": "Social Media Module",
                "description": "Social media features (placeholder)",
                "is_enabled": True,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade():
    op.drop_table("rb_user_module")
    op.drop_table("rb_module")
