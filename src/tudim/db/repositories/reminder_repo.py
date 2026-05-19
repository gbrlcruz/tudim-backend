import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tudim.db import models as orm
from tudim.domain import entities as domain


def _to_entity(row: orm.Reminder) -> domain.Reminder:
    return domain.Reminder(
        id=row.id,
        user_id=row.user_id,
        content=row.content,
        scheduled_for=row.scheduled_for,
        status=row.status,
        sent_at=row.sent_at,
    )


class SqlReminderRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self, *, user_id: uuid.UUID, content: str, scheduled_for: datetime
    ) -> domain.Reminder:
        row = orm.Reminder(
            user_id=user_id,
            content=content,
            scheduled_for=scheduled_for,
            status="pending",
        )
        self._session.add(row)
        await self._session.flush()
        return _to_entity(row)

    async def list_pending_for_user(self, user_id: uuid.UUID) -> list[domain.Reminder]:
        stmt = (
            select(orm.Reminder)
            .where(
                orm.Reminder.user_id == user_id,
                orm.Reminder.status == "pending",
                orm.Reminder.deleted_at.is_(None),
            )
            .order_by(orm.Reminder.scheduled_for)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def claim_due(self, batch_size: int = 100) -> list[domain.Reminder]:
        inner = (
            select(orm.Reminder.id)
            .where(
                orm.Reminder.status == "pending",
                orm.Reminder.scheduled_for <= func.now(),
                orm.Reminder.deleted_at.is_(None),
            )
            .order_by(orm.Reminder.scheduled_for)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        stmt = (
            update(orm.Reminder)
            .where(orm.Reminder.id.in_(inner))
            .values(status="sending", updated_at=func.now())
            .returning(orm.Reminder)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def mark_sent(self, reminder_id: uuid.UUID) -> None:
        await self._session.execute(
            update(orm.Reminder)
            .where(orm.Reminder.id == reminder_id)
            .values(status="sent", sent_at=func.now())
        )

    async def mark_failed(self, reminder_id: uuid.UUID) -> None:
        await self._session.execute(
            update(orm.Reminder)
            .where(orm.Reminder.id == reminder_id)
            .values(status="failed")
        )
