from __future__ import annotations

import re

from app.domains.auth.schemas import (
    AuthSyncCompany,
    AuthSyncMember,
    AuthSyncRequest,
    AuthSyncResponse,
)
from app.domains.company.repositories.company import CompanyRepository
from app.domains.company.repositories.member import MemberRepository

PERSONAL_EMAIL_DOMAINS = frozenset({
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "me.com",
    "live.com",
    "aol.com",
    "yahoo.co.uk",
    "yahoo.co.jp",
    "hotmail.co.uk",
    "live.co.uk",
    "googlemail.com",
    "protonmail.com",
    "proton.me",
    "mail.com",
    "zoho.com",
})


def _extract_domain(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower()


def _domain_to_company_name(domain: str) -> str:
    """Derive a human-readable company name from a domain (e.g. 'beautyclinic.com' -> 'Beautyclinic')."""
    name = domain.split(".")[0]
    name = re.sub(r"[-_]", " ", name)
    return name.title()


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class AuthSyncService:
    def __init__(
        self,
        member_repo: MemberRepository,
        company_repo: CompanyRepository,
    ) -> None:
        self.member_repo = member_repo
        self.company_repo = company_repo

    async def sync(self, request: AuthSyncRequest) -> AuthSyncResponse:
        member = await self.member_repo.get_by_email(request.email)

        if member is not None:
            return await self._handle_existing_member(member, request)

        domain = _extract_domain(request.email)
        if domain in PERSONAL_EMAIL_DOMAINS:
            return await self._handle_personal_email(request)
        return await self._handle_company_email(request, domain)

    async def _handle_existing_member(
        self, member, request: AuthSyncRequest
    ) -> AuthSyncResponse:
        update_fields = {}
        if request.name and request.name != member.name:
            update_fields["name"] = request.name
        if request.avatar_url and request.avatar_url != member.avatar_url:
            update_fields["avatar_url"] = request.avatar_url
        if update_fields:
            member = await self.member_repo.update(member.id, **update_fields)

        company = None
        if member.company_id:
            company_entity = await self.company_repo.get_by_id(member.company_id)
            if company_entity:
                company = AuthSyncCompany.model_validate(company_entity)

        return AuthSyncResponse(
            member=AuthSyncMember.model_validate(member),
            company=company,
        )

    async def _handle_personal_email(self, request: AuthSyncRequest) -> AuthSyncResponse:
        member = await self.member_repo.create(
            email=request.email,
            name=request.name,
            avatar_url=request.avatar_url,
        )
        return AuthSyncResponse(
            member=AuthSyncMember.model_validate(member),
            company=None,
        )

    async def _handle_company_email(
        self, request: AuthSyncRequest, domain: str
    ) -> AuthSyncResponse:
        company = await self.company_repo.get_by_domain(domain)

        if company is None:
            name = _domain_to_company_name(domain)
            slug = _slugify(name)
            existing = await self.company_repo.get_by_slug(slug)
            if existing:
                slug = f"{slug}-{domain.replace('.', '-')}"
            company = await self.company_repo.create(
                name=name,
                slug=slug,
                domain=domain,
            )

        member = await self.member_repo.create(
            email=request.email,
            name=request.name,
            avatar_url=request.avatar_url,
            company_id=company.id,
        )

        return AuthSyncResponse(
            member=AuthSyncMember.model_validate(member),
            company=AuthSyncCompany.model_validate(company),
        )
