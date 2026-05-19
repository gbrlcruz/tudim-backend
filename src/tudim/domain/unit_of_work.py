from __future__ import annotations

from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tudim.db.repositories.habit_repo import SqlHabitRepository
from tudim.db.repositories.note_repo import SqlNoteRepository
from tudim.db.repositories.reminder_repo import SqlReminderRepository
from tudim.db.repositories.tag_repo import SqlTagRepository
from tudim.db.repositories.user_repo import SqlUserRepository


class UnitOfWork(Protocol):
    users: SqlUserRepository
    tags: SqlTagRepository
    notes: SqlNoteRepository
    habits: SqlHabitRepository
    reminders: SqlReminderRepository

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.users = SqlUserRepository(self._session)
        self.tags = SqlTagRepository(self._session)
        self.notes = SqlNoteRepository(self._session)
        self.habits = SqlHabitRepository(self._session)
        self.reminders = SqlReminderRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.rollback()
        await self._session.close()
        self._session = None

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()