import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tudim.db import models as orm
from tudim.domain import entities as domain


def _habit_to_entity(row: orm.Habit) -> domain.Habit:
    return domain.Habit(
        id=row.id, user_id=row.user_id, name=row.name,
        aliases=list(row.aliases or []), active=row.active,
    )


def _log_to_entity(row: orm.HabitLog) -> domain.HabitLog:
    return domain.HabitLog(
        id=row.id, habit_id=row.habit_id, user_id=row.user_id,
        occurred_at=row.occurred_at, details=row.details,
    )


class SqlHabitRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_active(self, user_id: uuid.UUID) -> list[domain.Habit]:
        stmt = (
            select(orm.Habit)
            .where(orm.Habit.user_id == user_id, orm.Habit.active.is_(True), orm.Habit.deleted_at.is_(None))
            .order_by(orm.Habit.name)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_habit_to_entity(r) for r in rows]

    async def list_active_names(self, user_id: uuid.UUID) -> list[str]:
        return [h.name for h in await self.list_active(user_id)]

    async def log_check_in(
        self,
        *,
        habit_id: uuid.UUID,
        user_id: uuid.UUID,
        occurred_at: datetime,
        details: str | None = None,
    ) -> domain.HabitLog:
        row = orm.HabitLog(habit_id=habit_id, user_id=user_id, occurred_at=occurred_at, details=details)
        self._session.add(row)
        await self._session.flush()
        return _log_to_entity(row)

    async def compute_streak(self, habit_id: uuid.UUID, tz: str) -> int:
        sql = text("""
            WITH dates AS (
              SELECT DISTINCT (occurred_at AT TIME ZONE :tz)::date AS d
              FROM habit_logs
              WHERE habit_id = :habit_id AND deleted_at IS NULL
            ),
            ranked AS (
              SELECT d, ROW_NUMBER() OVER (ORDER BY d DESC) AS rn FROM dates
            )
            SELECT COUNT(*) FROM ranked
            WHERE d = ((NOW() AT TIME ZONE :tz)::date - (rn - 1) * INTERVAL '1 day')::date
        """)
        result = await self._session.execute(sql, {"habit_id": habit_id, "tz": tz})
        return int(result.scalar() or 0)


# Pure function — no repo needed, no DB needed. Moved out of the repo.
def match_habit_by_aliases(habits: list[domain.Habit], text_segment: str) -> domain.Habit | None:
    lowered = text_segment.lower()
    for habit in habits:
        for alias in [habit.name, *habit.aliases]:
            if alias.lower() in lowered:
                return habit
    return None