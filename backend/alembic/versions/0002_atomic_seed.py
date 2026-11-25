"""Claim synthetic panel generation once per experiment.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("experiments", sa.Column("seeded", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute(sa.text(
        "UPDATE experiments SET seeded = true WHERE EXISTS ("
        "SELECT 1 FROM participants WHERE experiment_id = experiments.id "
        "AND consent_version = 'synthetic-generator-v1')"
    ))


def downgrade():
    op.drop_column("experiments", "seeded")
