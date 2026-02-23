from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.domains.messaging.dependencies import get_messaging_service
from app.domains.messaging.schemas import (
    ConversationDetailResponse,
    ConversationListItem,
    ContactResponse,
    MemberReplyRequest,
    MessageResponse,
    ToolExecutionSummary,
)
from app.domains.messaging.services.messaging_service import MessagingService
from app.domains.whatsapp.dependencies import get_whatsapp_service
from app.domains.whatsapp.services.whatsapp_service import WhatsAppService

router = APIRouter(tags=["conversations"])


@router.get("", response_model=list[ConversationListItem])
async def list_conversations(
    company_id: UUID,
    branch_id: UUID | None = None,
    status: str | None = None,
    needed_human: bool | None = None,
    svc: MessagingService = Depends(get_messaging_service),
):
    conversations = await svc.list_conversations(
        company_id, branch_id, status, needed_human
    )
    items = []
    for conv in conversations:
        msg_count = len(conv.messages) if conv.messages else 0
        items.append(
            ConversationListItem(
                id=conv.id,
                branch_id=conv.branch_id,
                channel=conv.channel,
                contact=ContactResponse.model_validate(conv.contact),
                status=conv.status,
                escalated_at=conv.escalated_at,
                message_count=msg_count,
                created_at=conv.created_at,
            )
        )
    return items


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    company_id: UUID,
    conversation_id: UUID,
    svc: MessagingService = Depends(get_messaging_service),
):
    conv = await svc.get_conversation_detail(conversation_id)
    return ConversationDetailResponse(
        id=conv.id,
        branch_id=conv.branch_id,
        channel=conv.channel,
        contact=ContactResponse.model_validate(conv.contact),
        status=conv.status,
        escalated_at=conv.escalated_at,
        resolved_at=conv.resolved_at,
        messages=[MessageResponse.model_validate(m) for m in conv.messages],
        tool_executions=[],
        created_at=conv.created_at,
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def member_reply(
    company_id: UUID,
    conversation_id: UUID,
    body: MemberReplyRequest,
    svc: MessagingService = Depends(get_messaging_service),
    wa_svc: WhatsAppService = Depends(get_whatsapp_service),
):
    conv = await svc.get_conversation_detail(conversation_id)
    message = await svc.persist_message(conversation_id, "member", body.content)

    await wa_svc.send_message(
        branch_id=conv.branch_id,
        customer_phone=conv.contact.phone,
        text=body.content,
    )

    return MessageResponse.model_validate(message)


@router.put("/{conversation_id}/resolve")
async def resolve_conversation(
    company_id: UUID,
    conversation_id: UUID,
    svc: MessagingService = Depends(get_messaging_service),
):
    conv = await svc.resolve(conversation_id)
    return {"id": str(conv.id), "status": conv.status.value}


@router.put("/{conversation_id}/hand-back")
async def hand_back_conversation(
    company_id: UUID,
    conversation_id: UUID,
    svc: MessagingService = Depends(get_messaging_service),
):
    conv = await svc.hand_back(conversation_id)
    return {"id": str(conv.id), "status": conv.status.value}
