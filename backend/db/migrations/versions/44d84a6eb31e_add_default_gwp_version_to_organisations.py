"""add default_gwp_version to organisations

Revision ID: 44d84a6eb31e
Revises: 3134bad4a623
Create Date: 2026-05-14 23:42:59.455176

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44d84a6eb31e'
down_revision: Union[str, Sequence[str], None] = '3134bad4a623'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add as nullable first, set default value, then make not nullable
    op.add_column('organisations',
        sa.Column('default_gwp_version',
            sa.Enum('AR5', 'AR6', name='gwpversion'),
            nullable=True
        )
    )
    # Set AR6 as default for all existing rows
    op.execute("UPDATE organisations SET default_gwp_version = 'AR6'")
    # Now make it not nullable
    op.alter_column('organisations', 'default_gwp_version', nullable=False)


def downgrade() -> None:
    op.drop_column('organisations', 'default_gwp_version')