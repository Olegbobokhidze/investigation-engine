"""Async Postgres access: the engine, sessions, and the declarative base for ORM models."""

from sqlalchemy import MetaData
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Deterministic constraint names, so they are identical in every environment.
_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


def to_asyncpg_url(database_url: str) -> tuple[URL, dict[str, str]]:
    """Converts a standard Postgres URL into an asyncpg URL plus connect arguments.

    Hosted providers such as Neon hand out libpq URLs with `sslmode` and `channel_binding`
    query options, which asyncpg rejects. `sslmode` moves into asyncpg's `ssl` argument;
    `channel_binding` has no asyncpg equivalent and is dropped.
    """
    url = make_url(database_url).set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    connect_args = {"ssl": sslmode} if isinstance(sslmode, str) else {}
    return url.set(query=query), connect_args


class Database:
    """Owns the connection pool for the app's lifetime; created at startup, disposed on shutdown."""

    def __init__(self, database_url: str) -> None:
        url, connect_args = to_asyncpg_url(database_url)
        # pool_pre_ping replaces connections the server closed while idle (Neon suspends idle
        # databases on the free tier).
        self.engine: AsyncEngine = create_async_engine(
            url, connect_args=connect_args, pool_pre_ping=True
        )
        self.sessions: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    async def create_tables(self) -> None:
        """Creates missing tables. Idempotent; schema changes would need migrations."""
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()
