from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class AuthSyncRequest(BaseModel):
    email: str
    name: str
    avatar_url: str | None = None


class AuthSyncMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    company_id: uuid.UUID | None


class AuthSyncCompany(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class AuthSyncResponse(BaseModel):
    member: AuthSyncMember
    company: AuthSyncCompany | None
