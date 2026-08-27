"""remove loops and add MCP servers

Revision ID: bc129a44d8af
Revises: af26479577bf
"""
from alembic import op
import sqlalchemy as sa

revision = "bc129a44d8af"
down_revision = "af26479577bf"
branch_labels = None
depends_on = None

def upgrade():
    op.drop_table("loop_matches")
    op.drop_table("job_loops")
    op.create_table("mcp_servers",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("name", sa.String(), nullable=False),
        sa.Column("server_type", sa.String(), nullable=False), sa.Column("transport", sa.String(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True))

def downgrade():
    op.drop_table("mcp_servers")
