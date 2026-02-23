from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class InboundMessage:
    branch_id: UUID
    company_id: UUID
    channel: str
    customer_phone: str
    customer_name: str | None
    text: str
    channel_message_id: str


@dataclass(frozen=True)
class OutboundMessage:
    branch_id: UUID
    channel: str
    customer_phone: str
    text: str
