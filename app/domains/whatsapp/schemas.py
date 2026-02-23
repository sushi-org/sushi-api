from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.whatsapp.models import WhatsAppAccountStatus


# ── WhatsApp Config ───────────────────────────────────────────────────────


class WhatsAppConfigUpdate(BaseModel):
    access_token: str | None = None
    verify_token: str | None = None


class WhatsAppConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    access_token_masked: str
    verify_token_masked: str
    updated_at: datetime


# ── WhatsApp Account ─────────────────────────────────────────────────────


class WhatsAppAccountCreate(BaseModel):
    branch_id: uuid.UUID
    waba_id: str
    phone_number_id: str
    display_phone: str


class WhatsAppAccountUpdate(BaseModel):
    display_phone: str | None = None
    status: WhatsAppAccountStatus | None = None


class WhatsAppAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    company_id: uuid.UUID
    waba_id: str
    phone_number_id: str
    display_phone: str
    status: WhatsAppAccountStatus
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
