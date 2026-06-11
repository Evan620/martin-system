"""
Member-scoped document search (search_documents in app/tools/database_tools.py).

A member searching with their twg_id must see:
  - documents belonging to their own TWG
  - global registry documents (twg_id IS NULL)
and must NEVER see:
  - documents belonging to another TWG
  - confidential documents (own-TWG, other-TWG, or global)

Uses an in-memory SQLite DB and patches the AsyncSessionLocal used by the
tool so the real WHERE-clause logic is exercised (no mocks of the query).
"""
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import TWG, TWGPillar, Document, User, UserRole
from app.tools.database_tools import search_documents

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def _make_session_factory():
    engine = create_async_engine(DATABASE_URL, echo=False)
    # Only create the tables this test touches: the full metadata contains
    # Postgres-only column types (e.g. projects.value_chain_stages ARRAY)
    # that SQLite cannot render. FKs are not enforced by SQLite by default,
    # so missing referenced tables are fine.
    needed = [User.__table__, TWG.__table__, Document.__table__]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=needed))
    return engine, sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _doc(file_name, uploader_id, twg_id=None, is_confidential=False):
    return Document(
        id=uuid.uuid4(),
        twg_id=twg_id,
        file_name=file_name,
        file_path=f"/tmp/{file_name}",
        file_type="application/pdf",
        uploaded_by_id=uploader_id,
        is_confidential=is_confidential,
    )


async def _seed(session_factory):
    """Returns (twg_a_id, seeded file_name -> doc mapping)."""
    async with session_factory() as session:
        uploader = User(
            id=uuid.uuid4(),
            email=f"uploader_{uuid.uuid4()}@ecowas.int",
            hashed_password="x",
            full_name="Uploader",
            role=UserRole.ADMIN,
        )
        twg_a = TWG(id=uuid.uuid4(), name="Energy TWG", pillar=TWGPillar.energy_infrastructure)
        twg_b = TWG(id=uuid.uuid4(), name="Agri TWG", pillar=TWGPillar.agriculture_food_systems)
        session.add_all([uploader, twg_a, twg_b])
        await session.commit()

        docs = [
            _doc("own_twg_doc.pdf", uploader.id, twg_id=twg_a.id),
            _doc("global_doc.pdf", uploader.id, twg_id=None),
            _doc("other_twg_doc.pdf", uploader.id, twg_id=twg_b.id),
            _doc("own_twg_confidential.pdf", uploader.id, twg_id=twg_a.id, is_confidential=True),
            _doc("global_confidential.pdf", uploader.id, twg_id=None, is_confidential=True),
        ]
        session.add_all(docs)
        await session.commit()
        return twg_a.id


@pytest.mark.asyncio
async def test_member_search_includes_own_twg_and_global_docs():
    engine, factory = await _make_session_factory()
    try:
        twg_a_id = await _seed(factory)
        with patch("app.tools.database_tools.AsyncSessionLocal", factory):
            results = await search_documents(twg_id=twg_a_id)

        names = {r["file_name"] for r in results}
        assert "own_twg_doc.pdf" in names, "member must see their own TWG's documents"
        assert "global_doc.pdf" in names, (
            "member must see global registry documents (twg_id IS NULL)"
        )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_member_search_never_returns_other_twg_or_confidential_docs():
    engine, factory = await _make_session_factory()
    try:
        twg_a_id = await _seed(factory)
        with patch("app.tools.database_tools.AsyncSessionLocal", factory):
            results = await search_documents(twg_id=twg_a_id)

        names = {r["file_name"] for r in results}
        assert "other_twg_doc.pdf" not in names, "must never leak another TWG's documents"
        assert "own_twg_confidential.pdf" not in names, "must never return confidential docs"
        assert "global_confidential.pdf" not in names, (
            "must never return confidential docs, even global ones"
        )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_member_search_accepts_string_twg_id():
    """The tool layer receives twg_id as a string from the agent runtime."""
    engine, factory = await _make_session_factory()
    try:
        twg_a_id = await _seed(factory)
        with patch("app.tools.database_tools.AsyncSessionLocal", factory):
            results = await search_documents(twg_id=str(twg_a_id))

        names = {r["file_name"] for r in results}
        assert names == {"own_twg_doc.pdf", "global_doc.pdf"}
    finally:
        await engine.dispose()
