from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.domains.agent.dependencies import get_agent_chat_service
from app.domains.agent.services.agent_chat_service import AgentChatService
from app.domains.messaging.dependencies import get_messaging_service
from app.domains.messaging.services.messaging_service import MessagingService
from app.domains.pipeline.service import InboundPipelineService
from app.domains.whatsapp.dependencies import get_whatsapp_service
from app.domains.whatsapp.services.whatsapp_service import WhatsAppService


async def get_pipeline_service(
    messaging_service: MessagingService = Depends(get_messaging_service),
    whatsapp_service: WhatsAppService = Depends(get_whatsapp_service),
    agent_service: AgentChatService = Depends(get_agent_chat_service),
    session: AsyncSession = Depends(get_session),
) -> InboundPipelineService:
    return InboundPipelineService(
        messaging_service=messaging_service,
        whatsapp_service=whatsapp_service,
        agent_service=agent_service,
        session=session,
    )
