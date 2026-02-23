from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AgentStatus(str, enum.Enum):
    active = "active"
    paused = "paused"


class KnowledgeEntryStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class ReplyTemplateTrigger(str, enum.Enum):
    greeting = "greeting"
    availability_found = "availability_found"
    availability_none = "availability_none"
    booking_confirmed = "booking_confirmed"
    booking_slot_unavailable = "booking_slot_unavailable"
    escalation = "escalation"


class ToolExecutionStatus(str, enum.Enum):
    success = "success"
    failure = "failure"


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(127), nullable=False)
    tools_enabled: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status", create_type=False),
        nullable=False,
        default=AgentStatus.active,
    )

    knowledge_entries: Mapped[list[KnowledgeEntry]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    reply_templates: Mapped[list[ReplyTemplate]] = relationship(back_populates="agent", cascade="all, delete-orphan")


class KnowledgeEntry(TimestampMixin, Base):
    __tablename__ = "knowledge_entries"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[KnowledgeEntryStatus] = mapped_column(
        Enum(KnowledgeEntryStatus, name="knowledge_entry_status", create_type=False),
        nullable=False,
        default=KnowledgeEntryStatus.active,
    )

    agent: Mapped[Agent] = relationship(back_populates="knowledge_entries")


class ReplyTemplate(TimestampMixin, Base):
    __tablename__ = "reply_templates"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    trigger: Mapped[ReplyTemplateTrigger] = mapped_column(
        Enum(ReplyTemplateTrigger, name="reply_template_trigger", create_type=False), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[KnowledgeEntryStatus] = mapped_column(
        Enum(KnowledgeEntryStatus, name="knowledge_entry_status", create_type=False),
        nullable=False,
        default=KnowledgeEntryStatus.active,
    )

    agent: Mapped[Agent] = relationship(back_populates="reply_templates")


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    tool: Mapped[str] = mapped_column(String(63), nullable=False)
    input: Mapped[dict] = mapped_column(JSONB, nullable=False)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[ToolExecutionStatus] = mapped_column(
        Enum(ToolExecutionStatus, name="tool_execution_status", create_type=False), nullable=False
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
