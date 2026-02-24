from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from app.domains.messaging.models import ConversationStatus
from app.domains.pipeline.contracts import InboundMessage
from app.domains.pipeline.guardrails import check_keyword_escalation, check_max_turns

if TYPE_CHECKING:
    from app.domains.messaging.services.messaging_service import MessagingService
    from app.domains.whatsapp.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)

DEFAULT_ESCALATION_MESSAGE = "Let me connect you with our team. Someone will be with you shortly."


class AgentServiceProtocol(Protocol):
    async def process(self, conversation_id, branch_id, customer_phone: str = "", customer_name: str | None = None) -> "AgentResponse": ...
    async def resolve_template(self, agent_id, trigger: str) -> str: ...


class AgentResponse:
    def __init__(self, text: str, escalate: bool = False, escalation_reason: str | None = None):
        self.text = text
        self.escalate = escalate
        self.escalation_reason = escalation_reason


class InboundPipelineService:
    def __init__(
        self,
        messaging_service: MessagingService,
        whatsapp_service: WhatsAppService,
        agent_service: AgentServiceProtocol | None = None,
    ) -> None:
        self.messaging = messaging_service
        self.whatsapp = whatsapp_service
        self.agent = agent_service

    async def handle_inbound(self, inbound: InboundMessage) -> None:
        # 1. Deduplication
        if await self.messaging.is_duplicate(inbound.channel_message_id):
            logger.info("Duplicate message %s — skipping", inbound.channel_message_id)
            return

        # 2. Resolve contact
        contact = await self.messaging.resolve_contact(
            inbound.company_id, inbound.customer_phone, inbound.customer_name
        )

        # 3. Find or create conversation
        conversation, is_new = await self.messaging.find_or_create_conversation(
            branch_id=inbound.branch_id,
            company_id=inbound.company_id,
            contact_id=contact.id,
            channel=inbound.channel,
        )

        # 4. Persist inbound message
        await self.messaging.persist_message(
            conversation.id, "customer", inbound.text, inbound.channel_message_id
        )

        # 4b. Acknowledge receipt to the customer
        await self._acknowledge(inbound)

        # 5. If escalated, store only — do not invoke agent
        if conversation.status == ConversationStatus.escalated:
            logger.info("Conversation %s is escalated — message stored for member", conversation.id)
            return

        # 6. Pre-agent guardrails: keyword escalation
        if check_keyword_escalation(inbound.text):
            await self._escalate_with_message(
                conversation.id, inbound,
                reason="Customer requested human assistance (keyword detected)",
            )
            return

        # 7. Invoke agent (or fallback)
        if self.agent is not None:
            try:
                response = await self.agent.process(
                    conversation.id,
                    conversation.branch_id,
                    customer_phone=inbound.customer_phone,
                    customer_name=inbound.customer_name,
                )
            except Exception:
                logger.exception("Agent failed for conversation %s", conversation.id)
                await self._escalate_with_message(
                    conversation.id, inbound,
                    reason="Agent failed to process message",
                )
                return
        else:
            await self._escalate_with_message(
                conversation.id, inbound,
                reason="No active agent for this branch",
            )
            return

        # 8. Persist agent response
        await self.messaging.persist_message(conversation.id, "agent", response.text)

        # 9. Handle escalation signal from agent
        if response.escalate:
            await self.messaging.escalate(conversation.id, response.escalation_reason)

        # 10. Post-response guardrails: max turns
        agent_count = await self.messaging.count_agent_messages(conversation.id)
        if check_max_turns(agent_count):
            if not response.escalate:
                await self.messaging.escalate(
                    conversation.id, "Maximum conversation turns exceeded"
                )

        # 11. Deliver reply
        await self._deliver(inbound.branch_id, inbound.channel, inbound.customer_phone, response.text)

    async def _escalate_with_message(
        self, conversation_id, inbound: InboundMessage, reason: str | None = None,
    ) -> None:
        escalation_text = DEFAULT_ESCALATION_MESSAGE

        if self.agent is not None:
            try:
                template = await self.agent.resolve_template(None, "escalation")
                if template:
                    escalation_text = template
            except Exception:
                pass

        await self.messaging.persist_message(conversation_id, "agent", escalation_text)
        await self.messaging.escalate(conversation_id, reason)
        await self._deliver(inbound.branch_id, inbound.channel, inbound.customer_phone, escalation_text)

    async def _acknowledge(self, inbound: InboundMessage) -> None:
        """Mark the inbound message as read and show typing indicator."""
        if inbound.channel == "whatsapp":
            try:
                await self.whatsapp.mark_as_read(
                    inbound.branch_id, inbound.channel_message_id, typing=True
                )
            except Exception:
                logger.debug("Failed to send acknowledgement — non-critical, continuing")

    async def _deliver(self, branch_id, channel: str, customer_phone: str, text: str) -> None:
        if channel == "whatsapp":
            await self.whatsapp.send_message(branch_id, customer_phone, text)
        else:
            logger.warning("No adapter for channel %s", channel)
