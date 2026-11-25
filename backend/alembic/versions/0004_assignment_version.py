"""Use an integer assignment version for portable optimistic updates.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("participants", sa.Column("assignment_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("participants", "assignment_version")
