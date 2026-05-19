import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tudim.db import models as orm
from tudim.domain import entities as domain


def _to_entity(row: orm.User) -> domain.User:
    return domain.User(
        id=row.id,
        phone_number=row.phone_number,
        timezone=row.timezone,
        last_inbound_at=row.last_inbound_at,
        daily_message_count=row.daily_message_count,
        daily_count_reset_at=row.daily_count_reset_at,
        pending_destructive_action=row.pending_destructive_action,
        pending_destructive_expires_at=row.pending_destructive_expires_at,
    )


class SqlUserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_phone(self, phone: str) -> domain.User | None:
        result = await self._session.execute(
            select(orm.User).where(orm.User.phone_number == phone, orm.User.deleted_at.is_(None))
        )
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None

    async def create(self, phone: str, tz: str = "America/Sao_Paulo") -> domain.User:
        row = orm.User(phone_number=phone, timezone=tz)
        self._session.add(row)
        await self._session.flush()
        return _to_entity(row)

    async def touch_last_inbound(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(orm.User).where(orm.User.id == user_id).values(last_inbound_at=func.now())
        )

    async def try_increment_daily_count(self, user_id: uuid.UUID, daily_limit: int) -> bool:
        """Returns True if user is still under daily limit (and increments)."""
        now = datetime.now(timezone.utc)
        row = await self._session.get(orm.User, user_id)
        if row is None:
            return False

        if row.daily_count_reset_at is None or now >= row.daily_count_reset_at:
            row.daily_message_count = 1
            row.daily_count_reset_at = now + timedelta(hours=24)
            return True

        if row.daily_message_count >= daily_limit:
            return False

        row.daily_message_count += 1
        return True

    async def set_pending_destructive(self, user_id: uuid.UUID, action: str, ttl_minutes: int = 5) -> None:
        await self._session.execute(
            update(orm.User).where(orm.User.id == user_id).values(
                pending_destructive_action=action,
                pending_destructive_expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
            )
        )

    async def clear_pending_destructive(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(orm.User).where(orm.User.id == user_id).values(
                pending_destructive_action=None,
                pending_destructive_expires_at=None,
            )
        )