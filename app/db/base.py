from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

_db_instance: BaseDB | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class BaseDB(ABC):
    @abstractmethod
    def create_session_factory(self) -> async_sessionmaker[AsyncSession]:
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        pass

    @abstractmethod
    async def dispose(self) -> None:
        pass


def get_db(db_name: str) -> BaseDB:
    if db_name == "postgres":
        from app.db.postgres import PostgresDB

        return PostgresDB()
    raise ValueError(f"Unsupported database: {db_name}")


def init_db(db_name: str = "postgres") -> None:
    global _db_instance, _session_factory
    _db_instance = get_db(db_name)
    _session_factory = _db_instance.create_session_factory()
    logger.info("Database initialized (engine=%s)", db_name)


async def dispose_db() -> None:
    global _db_instance, _session_factory
    if _db_instance is not None:
        await _db_instance.dispose()
        _db_instance = None
        _session_factory = None
        logger.info("Database disposed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
