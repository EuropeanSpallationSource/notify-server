"""Rename apn_token to device_token

Revision ID: 06fd850a57c0
Revises: 0881dca000d8
Create Date: 2021-03-27 13:32:58.393608

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "06fd850a57c0"
down_revision = "0881dca000d8"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "users",
        "_apn_tokens",
        new_column_name="_device_tokens",
    )


def downgrade():
    op.alter_column(
        "users",
        "_device_tokens",
        new_column_name="_apn_tokens",
    )
