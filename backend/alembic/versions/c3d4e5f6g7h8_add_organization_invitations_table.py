"""Add organization_invitations table

Revision ID: c3d4e5f6g7h8
Revises: a1b2c3d4e5f6
Create Date: 2026-02-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # Check if enum type already exists
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'organizationinvitationstatus'"
    ))
    enum_exists = result.scalar() is not None

    if not enum_exists:
        conn.execute(sa.text(
            "CREATE TYPE organizationinvitationstatus AS ENUM ('PENDING', 'ACCEPTED', 'DECLINED', 'EXPIRED')"
        ))

    # Check if table already exists
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'organization_invitations'"
    ))
    table_exists = result.scalar() is not None

    if not table_exists:
        conn.execute(sa.text("""
            CREATE TABLE organization_invitations (
                id UUID NOT NULL,
                organization_name VARCHAR(255) NOT NULL,
                contact_email VARCHAR(255) NOT NULL,
                twg_id UUID NOT NULL,
                custom_message TEXT,
                status organizationinvitationstatus NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                sent_at TIMESTAMP,
                responded_at TIMESTAMP,
                created_by_id UUID NOT NULL,
                resend_count INTEGER NOT NULL DEFAULT 0,
                last_resend_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                PRIMARY KEY (id),
                CONSTRAINT fk_org_inv_twg FOREIGN KEY (twg_id) REFERENCES twgs(id) ON DELETE CASCADE,
                CONSTRAINT fk_org_inv_user FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))

        # Create index
        conn.execute(sa.text(
            "CREATE INDEX ix_organization_invitations_contact_email ON organization_invitations(contact_email)"
        ))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()

    # Check if table exists before dropping
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'organization_invitations'"
    ))
    if result.scalar() is not None:
        conn.execute(sa.text("DROP INDEX IF EXISTS ix_organization_invitations_contact_email"))
        conn.execute(sa.text("DROP TABLE organization_invitations"))

    # Check if enum type exists before dropping
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'organizationinvitationstatus'"
    ))
    if result.scalar() is not None:
        conn.execute(sa.text("DROP TYPE organizationinvitationstatus"))
