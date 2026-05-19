import uuid
from datetime import datetime
from typing import Protocol

from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from tudim.db import models as orm
from tudim.domain import entities as domain


def _to_entity(row: orm.Note) -> domain.Note:
    return domain.Note(
        id=row.id,
        user_id=row.user_id,
        content=row.content,
        occurred_at=row.occurred_at,
        raw_message=row.raw_message,
        confidence=row.confidence,
        tags=[domain.Tag(id=t.id, user_id=t.user_id, name=t.name) for t in row.tags],
        created_at=row.created_at,
    )


class NoteRepository(Protocol):
    async def create(
        self,
        *,
        user_id: uuid.UUID,
        content: str,
        occurred_at: datetime,
        raw_message: str | None,
        confidence: float | None,
        tag_ids: list[uuid.UUID],
    ) -> domain.Note: ...

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        tag_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 50,
        cursor_occurred_at: datetime | None = None,
        cursor_id: uuid.UUID | None = None,
    ) -> list[domain.Note]: ...

    async def search_text(self, user_id: uuid.UUID, query: str, limit: int = 10) -> list[domain.Note]: ...

    async def get_last(self, user_id: uuid.UUID) -> domain.Note | None: ...

    async def soft_delete(self, note_id: uuid.UUID) -> None: ...


class SqlNoteRepository:
    """Concrete NoteRepository over SQLAlchemy. Conforms to the Protocol structurally."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        content: str,
        occurred_at: datetime,
        raw_message: str | None,
        confidence: float | None,
        tag_ids: list[uuid.UUID],
    ) -> domain.Note:
        row = orm.Note(
            user_id=user_id,
            content=content,
            occurred_at=occurred_at,
            raw_message=raw_message,
            confidence=confidence,
        )
        if tag_ids:
            # Fetch tag rows to attach via relationship; they're already created by the tag repo.
            tag_rows = (await self._session.execute(
                select(orm.Tag).where(orm.Tag.id.in_(tag_ids))
            )).scalars().all()
            row.tags = list(tag_rows)
        self._session.add(row)
        await self._session.flush()
        return _to_entity(row)

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        tag_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 50,
        cursor_occurred_at: datetime | None = None,
        cursor_id: uuid.UUID | None = None,
    ) -> list[domain.Note]:
        stmt = select(orm.Note).where(orm.Note.user_id == user_id, orm.Note.deleted_at.is_(None))

        if tag_id is not None:
            stmt = stmt.join(orm.note_tags, orm.Note.id == orm.note_tags.c.note_id).where(
                orm.note_tags.c.tag_id == tag_id
            )
        if from_dt is not None:
            stmt = stmt.where(orm.Note.occurred_at >= from_dt)
        if to_dt is not None:
            stmt = stmt.where(orm.Note.occurred_at <= to_dt)

        if cursor_occurred_at is not None and cursor_id is not None:
            stmt = stmt.where(
                and_(
                    orm.Note.occurred_at <= cursor_occurred_at,
                    ~and_(orm.Note.occurred_at == cursor_occurred_at, orm.Note.id >= cursor_id),
                )
            )

        stmt = stmt.order_by(orm.Note.occurred_at.desc(), orm.Note.id.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def search_text(self, user_id: uuid.UUID, query: str, limit: int = 10) -> list[domain.Note]:
        stmt = (
            select(orm.Note)
            .where(
                orm.Note.user_id == user_id,
                orm.Note.deleted_at.is_(None),
                text("search_tsv @@ plainto_tsquery('portuguese', :q)"),
            )
            .order_by(orm.Note.occurred_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt, {"q": query})).scalars().all()
        return [_to_entity(r) for r in rows]

    async def get_last(self, user_id: uuid.UUID) -> domain.Note | None:
        stmt = (
            select(orm.Note)
            .where(orm.Note.user_id == user_id, orm.Note.deleted_at.is_(None))
            .order_by(orm.Note.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(row) if row else None

    async def soft_delete(self, note_id: uuid.UUID) -> None:
        from datetime import datetime, timezone
        await self._session.execute(
            update(orm.Note).where(orm.Note.id == note_id).values(deleted_at=datetime.now(timezone.utc))
        )