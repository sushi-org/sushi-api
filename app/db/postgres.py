from __future__ import annotations

import logging

import sqlalchemy.engine.url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Config
from app.db.base import BaseDB

logger = logging.getLogger(__name__)


class PostgresDB(BaseDB):
    def __init__(self) -> None:
        super().__init__()
        connection_params = {
            "drivername": "postgresql+asyncpg",
            "username": Config.POSTGRES_USERNAME,
            "password": Config.POSTGRES_PASSWORD,
            "host": Config.POSTGRES_HOST,
            "port": Config.POSTGRES_PORT,
            "database": Config.POSTGRES_DB_NAME,
        }
        logger.info("Creating DB Engine with host=%s port=%s db=%s",
                     Config.POSTGRES_HOST, Config.POSTGRES_PORT, Config.POSTGRES_DB_NAME)

        url = sqlalchemy.engine.url.URL.create(**connection_params)
        self._async_engine = create_async_engine(
            url,
            echo=Config.SQL_COMMAND_ECHO,
            pool_size=15,
            max_overflow=5,
            pool_timeout=30,
            pool_recycle=1800,
        )

    def create_session_factory(self) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(self._async_engine, class_=AsyncSession, expire_on_commit=False)

    async def dispose(self) -> None:
        await self._async_engine.dispose()

    async def test_connection(self) -> bool:
        try:
            async with self._async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database connection test failed: %s", e)
            raise
