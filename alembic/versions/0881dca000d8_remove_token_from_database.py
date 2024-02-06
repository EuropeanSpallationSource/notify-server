"""Remove token from database

Revision ID: 0881dca000d8
Revises: fcd46eadd970
Create Date: 2020-11-23 15:25:06.572358

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0881dca000d8"
down_revision = "fcd46eadd970"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("users", "token")


def downgrade():
    op.add_column("users", sa.Column("token", sa.VARCHAR(), nullable=True))
