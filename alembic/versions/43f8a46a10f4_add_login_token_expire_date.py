"""Add login_token_expire_date

Revision ID: 43f8a46a10f4
Revises: 06fd850a57c0
Create Date: 2022-10-16 07:42:13.437968

"""

from datetime import datetime, timedelta, timezone
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "43f8a46a10f4"
down_revision = "06fd850a57c0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("login_token_expire_date", sa.DateTime(), nullable=True)
    )
    # login_token_expire_date is only updated when the user requests a new token.
    # To avoid having to reset all tokens, we set the default value to the current date + 30 days
    # when running this migration. This ensures users will continue to receive notifications with
    # their current login token.
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    users = sa.sql.table("users", sa.sql.column("login_token_expire_date"))
    op.execute(users.update().values(login_token_expire_date=expire))
    op.alter_column("users", "login_token_expire_date", nullable=False)


def downgrade():
    op.drop_column("users", "login_token_expire_date")
