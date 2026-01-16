"""add user service filters table

Revision ID: 526ceb669661
Revises: 43f8a46a10f4
Create Date: 2025-12-09 14:43:51.163279

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '526ceb669661'
down_revision = '43f8a46a10f4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users_services_filters',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service_id', sa.CHAR(32), nullable=False),
        sa.Column('include_keywords', sa.String(), nullable=False),
        sa.Column('exclude_keywords', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], name=op.f('fk_users_services_filters_service_id_services')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_users_services_filters_user_id_users')),
        sa.PrimaryKeyConstraint('user_id', 'service_id', name=op.f('pk_users_services_filters'))
    )


def downgrade():
    op.drop_table('users_services_filters')
