from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.whatsapp.models import WhatsAppConfig


class WhatsAppConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self) -> WhatsAppConfig | None:
        stmt = select(WhatsAppConfig).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, **kwargs: Any) -> WhatsAppConfig:
        config = await self.get()
        if config is None:
            config = WhatsAppConfig(**kwargs)
            self.session.add(config)
        else:
            for key, value in kwargs.items():
                if value is not None:
                    setattr(config, key, value)
        await self.session.flush()
        await self.session.refresh(config)
        return config
