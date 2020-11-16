"""Initial database creation

Revision ID: fcd46eadd970
Revises:
Create Date: 2020-11-16 16:27:09.423308

"""
from alembic import op
import sqlalchemy as sa
from app.models import GUID


# revision identifiers, used by Alembic.
revision = "fcd46eadd970"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "services",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_services")),
    )
    op.create_index(
        op.f("ix_services_category"), "services", ["category"], unique=False
    )
    op.create_index(op.f("ix_services_id"), "services", ["id"], unique=False)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("_apn_tokens", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("subtitle", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("service_id", GUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name=op.f("fk_notifications_service_id_services"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(
        op.f("ix_notifications_timestamp"), "notifications", ["timestamp"], unique=False
    )
    op.create_table(
        "users_services",
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("service_id", GUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name=op.f("fk_users_services_service_id_services"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_users_services_user_id_users")
        ),
    )
    op.create_table(
        "users_notifications",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            name=op.f("fk_users_notifications_notification_id_notifications"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_users_notifications_user_id_users")
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "notification_id", name=op.f("pk_users_notifications")
        ),
    )


def downgrade():
    op.drop_table("users_notifications")
    op.drop_table("users_services")
    op.drop_index(op.f("ix_notifications_timestamp"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_services_id"), table_name="services")
    op.drop_index(op.f("ix_services_category"), table_name="services")
    op.drop_table("services")
