from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.domains.messaging.repositories.contact import ContactRepository
from app.domains.messaging.repositories.conversation import ConversationRepository
from app.domains.messaging.repositories.message import MessageRepository
from app.domains.messaging.services.messaging_service import MessagingService


# ── Repositories ─────────────────────────────────────────────────────────


async def get_contact_repo(session: AsyncSession = Depends(get_session)) -> ContactRepository:
    return ContactRepository(session)


async def get_conversation_repo(session: AsyncSession = Depends(get_session)) -> ConversationRepository:
    return ConversationRepository(session)


async def get_message_repo(session: AsyncSession = Depends(get_session)) -> MessageRepository:
    return MessageRepository(session)


# ── Services ─────────────────────────────────────────────────────────────


async def get_messaging_service(
    contact_repo: ContactRepository = Depends(get_contact_repo),
    conversation_repo: ConversationRepository = Depends(get_conversation_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
) -> MessagingService:
    return MessagingService(contact_repo, conversation_repo, message_repo)
