from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.domains.messaging.models import ConversationStatus, MessageRole
from app.domains.messaging.repositories.contact import ContactRepository
from app.domains.messaging.repositories.conversation import ConversationRepository
from app.domains.messaging.repositories.message import MessageRepository

logger = logging.getLogger(__name__)


class MessagingService:
    def __init__(
        self,
        contact_repo: ContactRepository,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
    ) -> None:
        self.contact_repo = contact_repo
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo

    # ── Contact resolution ────────────────────────────────────────────────

    async def resolve_contact(self, company_id: UUID, phone: str, name: str | None = None):
        contact = await self.contact_repo.get_by_company_phone(company_id, phone)
        if contact is None:
            contact = await self.contact_repo.create(company_id=company_id, phone=phone, name=name)
        elif name and not contact.name:
            contact.name = name
            await self.contact_repo.session.flush()
            await self.contact_repo.session.refresh(contact)
        return contact

    # ── Conversation lifecycle ────────────────────────────────────────────

    async def find_or_create_conversation(
        self,
        branch_id: UUID,
        company_id: UUID,
        contact_id: UUID,
        channel: str,
    ) -> tuple:
        """Returns (conversation, is_new)."""
        conversation = await self.conversation_repo.find_open(branch_id, channel, contact_id)
        if conversation is not None:
            return conversation, False

        conversation = await self.conversation_repo.create(
            branch_id=branch_id,
            company_id=company_id,
            contact_id=contact_id,
            channel=channel,
            status=ConversationStatus.active,
        )
        return conversation, True

    async def escalate(self, conversation_id: UUID):
        conv = await self.conversation_repo.get_by_id(conversation_id)
        if conv is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        conv.status = ConversationStatus.escalated
        conv.escalated_at = datetime.now(timezone.utc)
        await self.conversation_repo.session.flush()
        await self.conversation_repo.session.refresh(conv)
        return conv

    async def resolve(self, conversation_id: UUID):
        conv = await self.conversation_repo.get_by_id(conversation_id)
        if conv is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        conv.status = ConversationStatus.resolved
        conv.resolved_at = datetime.now(timezone.utc)
        await self.conversation_repo.session.flush()
        await self.conversation_repo.session.refresh(conv)
        return conv

    async def hand_back(self, conversation_id: UUID):
        conv = await self.conversation_repo.get_by_id(conversation_id)
        if conv is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        conv.status = ConversationStatus.active
        conv.escalated_at = None
        await self.conversation_repo.session.flush()
        await self.conversation_repo.session.refresh(conv)
        return conv

    # ── Messages ──────────────────────────────────────────────────────────

    async def is_duplicate(self, channel_message_id: str) -> bool:
        if not channel_message_id:
            return False
        return await self.message_repo.exists_by_channel_message_id(channel_message_id)

    async def persist_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        channel_message_id: str | None = None,
    ):
        return await self.message_repo.create(
            conversation_id=conversation_id,
            role=role,
            content=content,
            channel_message_id=channel_message_id,
        )

    async def get_recent_messages(self, conversation_id: UUID, limit: int = 20):
        return await self.message_repo.get_recent(conversation_id, limit)

    async def count_agent_messages(self, conversation_id: UUID) -> int:
        return await self.message_repo.count_by_role(conversation_id, MessageRole.agent)

    # ── Dashboard queries ─────────────────────────────────────────────────

    async def list_conversations(
        self,
        company_id: UUID,
        branch_id: UUID | None = None,
        status_filter: str | None = None,
        needed_human: bool | None = None,
    ):
        return await self.conversation_repo.list_by_company(
            company_id, branch_id, status_filter, needed_human
        )

    async def get_conversation_detail(self, conversation_id: UUID):
        conv = await self.conversation_repo.get_with_messages(conversation_id)
        if conv is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        return conv
