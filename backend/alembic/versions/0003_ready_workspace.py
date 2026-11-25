"""Shared workspaces, study policies, images, notifications and training leases.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("experiments", sa.Column("policy", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("model_runs", sa.Column("started_at", sa.DateTime(timezone=True)))
    op.add_column("model_runs", sa.Column("claim", sa.String(36)))
    op.create_table(
        "project_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("project_id", "user_id"),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
    op.create_table(
        "product_images",
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("content", sa.LargeBinary(), nullable=False),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.String(250), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_project_id", "notifications", ["project_id"])


def downgrade():
    op.drop_table("notifications")
    op.drop_table("product_images")
    op.drop_table("project_members")
    op.drop_column("model_runs", "claim")
    op.drop_column("model_runs", "started_at")
    op.drop_column("experiments", "policy")
