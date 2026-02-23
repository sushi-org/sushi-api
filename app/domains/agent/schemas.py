from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.agent.models import (
    AgentStatus,
    KnowledgeEntryStatus,
    ReplyTemplateTrigger,
    ToolExecutionStatus,
)


# ── Agent ─────────────────────────────────────────────────────────────────


class AgentUpsert(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    tools_enabled: dict | None = None
    status: AgentStatus | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    company_id: uuid.UUID
    name: str
    system_prompt: str
    model: str
    tools_enabled: dict
    status: AgentStatus
    created_at: datetime
    updated_at: datetime


# ── Knowledge Entry ───────────────────────────────────────────────────────


class KnowledgeEntryCreate(BaseModel):
    question: str
    answer: str
    category: str | None = None


class KnowledgeEntryUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None
    sort_order: int | None = None
    status: KnowledgeEntryStatus | None = None


class KnowledgeEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    answer: str
    category: str | None
    sort_order: int
    status: KnowledgeEntryStatus
    created_at: datetime
    updated_at: datetime


# ── Reply Template ────────────────────────────────────────────────────────


class ReplyTemplateUpsert(BaseModel):
    name: str
    content: str


class ReplyTemplateResponse(BaseModel):
    trigger: ReplyTemplateTrigger
    name: str
    content: str
    is_custom: bool


# ── Tool Execution ────────────────────────────────────────────────────────


class ToolExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    tool: str
    input: dict
    output: dict
    status: ToolExecutionStatus
    duration_ms: int | None
    created_at: datetime
