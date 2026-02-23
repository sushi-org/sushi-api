from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    async def get_by_id(self, entity_id: UUID) -> T | None:
        return await self.session.get(self.model, entity_id)

    async def list_by(self, **filters: Any) -> list[T]:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> T:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, entity_id: UUID, **kwargs: Any) -> T | None:
        instance = await self.get_by_id(entity_id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, entity_id: UUID) -> bool:
        instance = await self.get_by_id(entity_id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True
