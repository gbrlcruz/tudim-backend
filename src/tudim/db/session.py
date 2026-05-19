from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from tudim.config import settings
from tudim.domain.unit_of_work import SqlAlchemyUnitOfWork

# psycopg v3 understands sslmode + channel_binding natively
_url = settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_async_engine(
    _url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

def make_uow() -> SqlAlchemyUnitOfWork:
    from tudim.domain.unit_of_work import SqlAlchemyUnitOfWork
    return SqlAlchemyUnitOfWork(SessionLocal)