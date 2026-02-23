from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class WhatsAppAccountStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    disconnected = "disconnected"


class WhatsAppConfig(Base):
    __tablename__ = "whatsapp_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    verify_token: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class WhatsAppAccount(TimestampMixin, Base):
    __tablename__ = "whatsapp_accounts"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    waba_id: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_phone: Mapped[str] = mapped_column(String(31), nullable=False)
    status: Mapped[WhatsAppAccountStatus] = mapped_column(
        Enum(WhatsAppAccountStatus, name="whatsapp_account_status", create_type=False),
        nullable=False,
        default=WhatsAppAccountStatus.pending,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
