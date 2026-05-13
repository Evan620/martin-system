"""rename_project_status_enum

Revision ID: b1c2d3e4f5a6
Revises: 79130ce80c1e
Create Date: 2026-05-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = '79130ce80c1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_REMAP_CASE = """
    CASE {col}::text
        WHEN 'DRAFT'              THEN 'CONCEPT'
        WHEN 'PIPELINE'           THEN 'PRE_FEASIBILITY'
        WHEN 'UNDER_REVIEW'       THEN 'FEASIBILITY'
        WHEN 'NEEDS_REVISION'     THEN 'NEEDS_REVISION'
        WHEN 'SUMMIT_READY'       THEN 'BANKABLE'
        WHEN 'DEAL_ROOM_FEATURED' THEN 'SUMMIT_FEATURED'
        WHEN 'IN_NEGOTIATION'     THEN 'IN_NEGOTIATION'
        WHEN 'COMMITTED'          THEN 'COMMITTED'
        WHEN 'IMPLEMENTED'        THEN 'COMMITTED'
        WHEN 'IDENTIFIED'         THEN 'CONCEPT'
        WHEN 'identified'         THEN 'CONCEPT'
        WHEN 'vetting'            THEN 'PRE_FEASIBILITY'
        WHEN 'due_diligence'      THEN 'FEASIBILITY'
        WHEN 'financing'          THEN 'BANKABLE'
        WHEN 'bankable'           THEN 'BANKABLE'
        WHEN 'deal_room'          THEN 'SUMMIT_FEATURED'
        WHEN 'presented'          THEN 'SUMMIT_FEATURED'
        WHEN 'DECLINED'           THEN 'DECLINED'
        WHEN 'ON_HOLD'            THEN 'ON_HOLD'
        WHEN 'ARCHIVED'           THEN 'ARCHIVED'
        ELSE {col}::text
    END
"""


def upgrade() -> None:
    # Step 1: widen all enum columns to plain text so we can freely reassign values
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE VARCHAR(50) USING status::text")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN new_status TYPE VARCHAR(50) USING new_status::text")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN previous_status TYPE VARCHAR(50) USING previous_status::text")

    # Step 2: remap values in each table
    op.execute(f"UPDATE projects SET status = {_REMAP_CASE.format(col='status')}")
    op.execute(f"UPDATE project_status_history SET new_status = {_REMAP_CASE.format(col='new_status')} WHERE new_status IS NOT NULL")
    op.execute(f"UPDATE project_status_history SET previous_status = {_REMAP_CASE.format(col='previous_status')} WHERE previous_status IS NOT NULL")

    # Step 3: drop old type and create new one
    op.execute("DROP TYPE IF EXISTS projectstatus")
    op.execute("""
        CREATE TYPE projectstatus AS ENUM (
            'CONCEPT', 'PRE_FEASIBILITY', 'FEASIBILITY', 'BANKABLE',
            'SUMMIT_FEATURED', 'IN_NEGOTIATION', 'COMMITTED',
            'DECLINED', 'NEEDS_REVISION', 'ON_HOLD', 'ARCHIVED'
        )
    """)

    # Step 4: cast columns back to the new enum type
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE projectstatus USING status::projectstatus")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN new_status TYPE projectstatus USING new_status::projectstatus")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN previous_status TYPE projectstatus USING previous_status::projectstatus")


def downgrade() -> None:
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE VARCHAR(50)")
    op.execute("""
        UPDATE projects SET status = CASE status
            WHEN 'CONCEPT'          THEN 'DRAFT'
            WHEN 'PRE_FEASIBILITY'  THEN 'PIPELINE'
            WHEN 'FEASIBILITY'      THEN 'UNDER_REVIEW'
            WHEN 'BANKABLE'         THEN 'SUMMIT_READY'
            WHEN 'SUMMIT_FEATURED'  THEN 'DEAL_ROOM_FEATURED'
            ELSE status
        END
    """)
    op.execute("DROP TYPE IF EXISTS projectstatus")
    op.execute("""
        CREATE TYPE projectstatus AS ENUM (
            'DRAFT','PIPELINE','UNDER_REVIEW','SUMMIT_READY','DEAL_ROOM_FEATURED',
            'IN_NEGOTIATION','COMMITTED','IMPLEMENTED','DECLINED','NEEDS_REVISION',
            'ON_HOLD','ARCHIVED','identified','vetting','due_diligence','financing',
            'deal_room','bankable','presented'
        )
    """)
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE projectstatus USING status::projectstatus")
