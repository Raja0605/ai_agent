"""add explicit deterministic job experience fields

Revision ID: c41f6bf70ae2
Revises: bc129a44d8af
"""
from alembic import op
import sqlalchemy as sa

revision = "c41f6bf70ae2"
down_revision = "bc129a44d8af"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("jobs", sa.Column("experience_min", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("experience_max", sa.Integer(), nullable=True))

def downgrade():
    op.drop_column("jobs", "experience_max")
    op.drop_column("jobs", "experience_min")
