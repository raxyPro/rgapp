"""Ensure rb_user.status includes 'invited'

Revision ID: update_user_status_enum
Revises: add_login_action_enum
Create Date: 2025-12-25 15:45:00
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "update_user_status_enum"
down_revision: Union[str, None] = "add_login_action_enum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE rb_user MODIFY status "
        "ENUM('invited','active','blocked','deleted') NOT NULL DEFAULT 'invited'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE rb_user MODIFY status "
        "ENUM('active','blocked','deleted') NOT NULL DEFAULT 'active'"
    )
