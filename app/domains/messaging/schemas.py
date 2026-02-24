from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.messaging.models import ChannelType, ConversationStatus, MessageRole


# ── Contact ───────────────────────────────────────────────────────────────


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str
    name: str | None


# ── Message ───────────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


class MemberReplyRequest(BaseModel):
    content: str


# ── Conversation ──────────────────────────────────────────────────────────


class ConversationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    channel: ChannelType
    contact: ContactResponse
    status: ConversationStatus
    escalated_at: datetime | None
    escalation_reason: str | None = None
    message_count: int
    created_at: datetime


class ToolExecutionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tool: str
    status: str
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    channel: ChannelType
    contact: ContactResponse
    status: ConversationStatus
    escalated_at: datetime | None
    escalation_reason: str | None = None
    resolved_at: datetime | None
    messages: list[MessageResponse]
    tool_executions: list[ToolExecutionSummary]
    created_at: datetime
