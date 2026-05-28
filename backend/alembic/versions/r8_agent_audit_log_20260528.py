"""add agent_audit_log table

Revision ID: r8_agent_audit
Revises: r8_s3ct0r_d3t
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'r8_agent_audit'
down_revision = 'r8_s3ct0r_d3t'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: prod has historically been schema-modified out-of-band.
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_audit_log (
            id            UUID PRIMARY KEY,
            created_at    TIMESTAMP NOT NULL DEFAULT now(),
            user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
            user_role     VARCHAR(50),
            action_id     VARCHAR(32),
            tool_name     VARCHAR(80) NOT NULL,
            target_type   VARCHAR(40),
            target_id     VARCHAR(64),
            before_json   JSONB,
            after_json    JSONB,
            summary       TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_audit_log_created_at ON agent_audit_log (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_audit_log_action_id ON agent_audit_log (action_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_audit_log")
