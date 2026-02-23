from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.domains.company.models import Invite, InviteStatus, Member
from app.domains.company.repositories.invite import InviteRepository
from app.domains.company.repositories.member import MemberRepository
from app.domains.company.schemas import InviteCreate


class InviteService:
    def __init__(self, repo: InviteRepository, member_repo: MemberRepository | None = None) -> None:
        self.repo = repo
        self.member_repo = member_repo

    async def list_active(self, company_id: UUID) -> list[Invite]:
        return await self.repo.list_active_by_company(company_id)

    async def create(self, company_id: UUID, created_by: UUID, data: InviteCreate) -> Invite:
        code = self._generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)
        return await self.repo.create(
            company_id=company_id,
            code=code,
            created_by=created_by,
            expires_at=expires_at,
        )

    async def accept(self, code: str, member_id: UUID) -> tuple[Invite, Member]:
        """Redeem an invite code: link the member to the invite's company."""
        if not self.member_repo:
            raise RuntimeError("member_repo required for accept")

        invite = await self.repo.get_active_by_code(code)
        if invite is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invite not found, expired, or already used.",
            )

        member = await self.member_repo.get_by_id(member_id)
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        if member.company_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already part of a company.",
            )

        await self.member_repo.update(member_id, company_id=invite.company_id)
        invite.used_by = member_id
        invite.status = InviteStatus.used
        await self.repo.session.flush()

        member = await self.member_repo.get_by_id(member_id)
        if member:
            await self.repo.session.refresh(member, ["company"])
        return invite, member  # type: ignore[return-value]

    async def revoke(self, invite_id: UUID) -> None:
        invite = await self.repo.get_by_id(invite_id)
        if invite is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
        if invite.status != InviteStatus.active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite is not active")
        invite.status = InviteStatus.revoked
        await self.repo.session.flush()

    @staticmethod
    def _generate_code(length: int = 6) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))
