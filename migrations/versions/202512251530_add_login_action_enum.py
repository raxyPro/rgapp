"""Add missing 'login' action to rb_audit enum

Revision ID: add_login_action_enum
Revises: 1256eb79eccf
Create Date: 2025-12-25 15:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "add_login_action_enum"
down_revision: Union[str, None] = "1256eb79eccf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update enum to include all actions used in the models/routes
    op.execute(
        "ALTER TABLE rb_audit MODIFY action "
        "ENUM('add','invite','register','login','edit') NOT NULL"
    )


def downgrade() -> None:
    # Revert to the prior enum without 'login'
    op.execute(
        "ALTER TABLE rb_audit MODIFY action "
        "ENUM('add','invite','register','edit') NOT NULL"
    )
