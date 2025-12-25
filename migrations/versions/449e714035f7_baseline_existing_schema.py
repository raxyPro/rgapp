"""baseline existing schema

Revision ID: 449e714035f7
Revises: 9829dbb37ecf
Create Date: 2025-12-25 22:10:10.966303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '449e714035f7'
down_revision: Union[str, None] = '9829dbb37ecf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
