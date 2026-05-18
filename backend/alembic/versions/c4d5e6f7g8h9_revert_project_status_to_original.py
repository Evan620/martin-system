"""revert_project_status_to_original

Revision ID: c4d5e6f7g8h9
Revises: ba63ce4f6d0c
Create Date: 2026-05-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7g8h9'
down_revision: Union[str, Sequence[str], None] = 'ba63ce4f6d0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_REMAP_CASE = """
    CASE {col}::text
        WHEN 'CONCEPT'        THEN 'DRAFT'
        WHEN 'PRE_FEASIBILITY' THEN 'PIPELINE'
        WHEN 'FEASIBILITY'    THEN 'UNDER_REVIEW'
        WHEN 'BANKABLE'       THEN 'SUMMIT_READY'
        WHEN 'SUMMIT_FEATURED' THEN 'DEAL_ROOM_FEATURED'
        WHEN 'ARCHIVED'       THEN 'ON_HOLD'
        WHEN 'DRAFT'          THEN 'DRAFT'
        WHEN 'PIPELINE'       THEN 'PIPELINE'
        WHEN 'UNDER_REVIEW'   THEN 'UNDER_REVIEW'
        WHEN 'SUMMIT_READY'   THEN 'SUMMIT_READY'
        WHEN 'DEAL_ROOM_FEATURED' THEN 'DEAL_ROOM_FEATURED'
        WHEN 'IN_NEGOTIATION' THEN 'IN_NEGOTIATION'
        WHEN 'COMMITTED'      THEN 'COMMITTED'
        WHEN 'IMPLEMENTED'    THEN 'IMPLEMENTED'
        WHEN 'DECLINED'       THEN 'DECLINED'
        WHEN 'NEEDS_REVISION' THEN 'NEEDS_REVISION'
        WHEN 'ON_HOLD'        THEN 'ON_HOLD'
        ELSE {col}::text
    END
"""

_DOWNGRADE_REMAP_CASE = """
    CASE {col}::text
        WHEN 'DRAFT'              THEN 'CONCEPT'
        WHEN 'PIPELINE'           THEN 'PRE_FEASIBILITY'
        WHEN 'UNDER_REVIEW'       THEN 'FEASIBILITY'
        WHEN 'SUMMIT_READY'       THEN 'BANKABLE'
        WHEN 'DEAL_ROOM_FEATURED' THEN 'SUMMIT_FEATURED'
        WHEN 'IMPLEMENTED'        THEN 'COMMITTED'
        WHEN 'IN_NEGOTIATION'     THEN 'IN_NEGOTIATION'
        WHEN 'COMMITTED'          THEN 'COMMITTED'
        WHEN 'DECLINED'           THEN 'DECLINED'
        WHEN 'NEEDS_REVISION'     THEN 'NEEDS_REVISION'
        WHEN 'ON_HOLD'            THEN 'ON_HOLD'
        ELSE {col}::text
    END
"""


def upgrade() -> None:
    # Step 1: widen all enum columns to plain text so we can freely reassign values
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE VARCHAR(50) USING status::text")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN new_status TYPE VARCHAR(50) USING new_status::text")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN previous_status TYPE VARCHAR(50) USING previous_status::text")

    # Step 2: remap values in each table (old names → new names)
    op.execute(f"UPDATE projects SET status = {_REMAP_CASE.format(col='status')}")
    op.execute(f"UPDATE project_status_history SET new_status = {_REMAP_CASE.format(col='new_status')} WHERE new_status IS NOT NULL")
    op.execute(f"UPDATE project_status_history SET previous_status = {_REMAP_CASE.format(col='previous_status')} WHERE previous_status IS NOT NULL")

    # Step 3: drop old type and create new one with original values
    op.execute("DROP TYPE IF EXISTS projectstatus")
    op.execute("""
        CREATE TYPE projectstatus AS ENUM (
            'DRAFT', 'PIPELINE', 'UNDER_REVIEW',
            'DECLINED', 'NEEDS_REVISION', 'SUMMIT_READY',
            'DEAL_ROOM_FEATURED', 'IN_NEGOTIATION',
            'COMMITTED', 'IMPLEMENTED',
            'ON_HOLD'
        )
    """)

    # Step 4: cast columns back to the new enum type
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE projectstatus USING status::projectstatus")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN new_status TYPE projectstatus USING new_status::projectstatus")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN previous_status TYPE projectstatus USING previous_status::projectstatus")


def downgrade() -> None:
    # Step 1: widen to text
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE VARCHAR(50) USING status::text")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN new_status TYPE VARCHAR(50) USING new_status::text")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN previous_status TYPE VARCHAR(50) USING previous_status::text")

    # Step 2: remap back to old names
    op.execute(f"UPDATE projects SET status = {_DOWNGRADE_REMAP_CASE.format(col='status')}")
    op.execute(f"UPDATE project_status_history SET new_status = {_DOWNGRADE_REMAP_CASE.format(col='new_status')} WHERE new_status IS NOT NULL")
    op.execute(f"UPDATE project_status_history SET previous_status = {_DOWNGRADE_REMAP_CASE.format(col='previous_status')} WHERE previous_status IS NOT NULL")

    # Step 3: drop new type and restore old one
    op.execute("DROP TYPE IF EXISTS projectstatus")
    op.execute("""
        CREATE TYPE projectstatus AS ENUM (
            'CONCEPT', 'PRE_FEASIBILITY', 'FEASIBILITY', 'BANKABLE',
            'SUMMIT_FEATURED', 'IN_NEGOTIATION', 'COMMITTED',
            'DECLINED', 'NEEDS_REVISION', 'ON_HOLD', 'ARCHIVED'
        )
    """)

    # Step 4: cast back
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE projectstatus USING status::projectstatus")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN new_status TYPE projectstatus USING new_status::projectstatus")
    op.execute("ALTER TABLE project_status_history ALTER COLUMN previous_status TYPE projectstatus USING previous_status::projectstatus")
