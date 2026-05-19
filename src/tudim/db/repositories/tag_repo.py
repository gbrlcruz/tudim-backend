import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from tudim.db import models as orm
from tudim.domain import entities as domain


def _to_entity(row: orm.Tag) -> domain.Tag:
    return domain.Tag(id=row.id, user_id=row.user_id, name=row.name)


class SqlTagRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_names_for_user(self, user_id: uuid.UUID) -> list[str]:
        result = await self._session.execute(
            select(orm.Tag.name)
            .where(orm.Tag.user_id == user_id)
            .order_by(orm.Tag.name)
        )
        return [r[0] for r in result.all()]

    async def ensure_many(
        self, user_id: uuid.UUID, names: list[str]
    ) -> list[domain.Tag]:
        if not names:
            return []

        seen, unique = set(), []
        for n in names:
            key = n.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(n.strip())

        stmt = insert(orm.Tag).values([{"user_id": user_id, "name": n} for n in unique])
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "name"],
            set_={"name": stmt.excluded.name},
        ).returning(orm.Tag)

        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        by_name = {r.name: r for r in rows}
        return [_to_entity(by_name[n]) for n in unique if n in by_name]
