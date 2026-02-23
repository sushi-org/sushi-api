from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.config import Config
from app.domains.company.repositories.branch import BranchRepository
from app.domains.whatsapp.models import WhatsAppAccountStatus
from app.domains.whatsapp.repositories.account import WhatsAppAccountRepository
from app.domains.whatsapp.repositories.config import WhatsAppConfigRepository
from app.domains.whatsapp.schemas import WhatsAppAccountCreate, WhatsAppAccountUpdate, WhatsAppConfigUpdate

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com"


class WhatsAppService:
    def __init__(
        self,
        config_repo: WhatsAppConfigRepository,
        account_repo: WhatsAppAccountRepository,
        branch_repo: BranchRepository,
    ) -> None:
        self.config_repo = config_repo
        self.account_repo = account_repo
        self.branch_repo = branch_repo

    # ── Config ────────────────────────────────────────────────────────────

    async def get_config(self):
        return await self.config_repo.get()

    async def update_config(self, data: WhatsAppConfigUpdate):
        kwargs = data.model_dump(exclude_unset=True)
        if not kwargs:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")
        return await self.config_repo.upsert(**kwargs)

    # ── Accounts ──────────────────────────────────────────────────────────

    async def list_accounts(self) -> list:
        return await self.account_repo.list_by()

    async def list_accounts_by_company(self, company_id: UUID) -> list:
        return await self.account_repo.list_by(company_id=company_id)

    async def get_account(self, account_id: UUID):
        account = await self.account_repo.get_by_id(account_id)
        if account is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "WhatsApp account not found")
        return account

    async def create_account(self, data: WhatsAppAccountCreate):
        branch = await self.branch_repo.get_by_id(data.branch_id)
        if branch is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")

        existing = await self.account_repo.get_by_branch_id(data.branch_id)
        if existing is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Branch already has a WhatsApp account")

        existing_phone = await self.account_repo.get_by_phone_number_id(data.phone_number_id)
        if existing_phone is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Phone number ID already registered")

        return await self.account_repo.create(
            branch_id=data.branch_id,
            company_id=branch.company_id,
            waba_id=data.waba_id,
            phone_number_id=data.phone_number_id,
            display_phone=data.display_phone,
        )

    async def update_account(self, account_id: UUID, data: WhatsAppAccountUpdate):
        kwargs = data.model_dump(exclude_unset=True)
        if not kwargs:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")
        account = await self.account_repo.update(account_id, **kwargs)
        if account is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "WhatsApp account not found")
        return account

    async def disconnect_account(self, account_id: UUID):
        account = await self.account_repo.get_by_id(account_id)
        if account is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "WhatsApp account not found")

        try:
            await self._unsubscribe_from_waba(account.waba_id)
        except Exception:
            logger.warning("Failed to unsubscribe WABA %s during disconnect — continuing", account.waba_id)

        account.status = WhatsAppAccountStatus.disconnected
        await self.account_repo.session.flush()
        await self.account_repo.session.refresh(account)
        return account

    async def approve_account(self, account_id: UUID):
        """Subscribe app to WABA, then transition account pending → active."""
        account = await self.account_repo.get_by_id(account_id)
        if account is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "WhatsApp account not found")
        if account.status != WhatsAppAccountStatus.pending:
            raise HTTPException(status.HTTP_409_CONFLICT, "Account is not pending approval")

        await self._subscribe_to_waba(account.waba_id)

        account.status = WhatsAppAccountStatus.active
        account.verified_at = datetime.now(timezone.utc)
        await self.account_repo.session.flush()
        await self.account_repo.session.refresh(account)
        return account

    async def check_waba_subscription(self, waba_id: str) -> dict:
        """Check whether our app is subscribed to a WABA's webhooks."""
        config = await self.config_repo.get()
        if config is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "WhatsApp config not set — add access token first")

        url = f"{GRAPH_API_BASE}/{Config.WHATSAPP_API_VERSION}/{waba_id}/subscribed_apps"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {config.access_token}"})
            return resp.json()

    # ── WABA subscription ──────────────────────────────────────────────────

    async def _subscribe_to_waba(self, waba_id: str) -> None:
        config = await self.config_repo.get()
        if config is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "WhatsApp config not set — add access token first")

        url = f"{GRAPH_API_BASE}/{Config.WHATSAPP_API_VERSION}/{waba_id}/subscribed_apps"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers={"Authorization": f"Bearer {config.access_token}"})
            if resp.status_code != 200:
                logger.error("WABA subscribe failed (%s): %s", resp.status_code, resp.text)
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    f"Failed to subscribe app to WABA {waba_id}: {resp.text}",
                )
            logger.info("Subscribed app to WABA %s", waba_id)

    async def _unsubscribe_from_waba(self, waba_id: str) -> None:
        config = await self.config_repo.get()
        if config is None:
            return

        url = f"{GRAPH_API_BASE}/{Config.WHATSAPP_API_VERSION}/{waba_id}/subscribed_apps"
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers={"Authorization": f"Bearer {config.access_token}"})
            if resp.status_code != 200:
                logger.warning("WABA unsubscribe failed (%s): %s", resp.status_code, resp.text)
            else:
                logger.info("Unsubscribed app from WABA %s", waba_id)

    # ── Presence indicators ────────────────────────────────────────────────

    async def mark_as_read(self, branch_id: UUID, message_id: str, *, typing: bool = False) -> None:
        """Mark a message as read. Optionally show a typing indicator (dismissed on reply or after 25s)."""
        account, config = await self._resolve_account_config(branch_id)
        if not account or not config:
            return

        url = f"{GRAPH_API_BASE}/{Config.WHATSAPP_API_VERSION}/{account.phone_number_id}/messages"
        payload: dict = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        if typing:
            payload["typing_indicator"] = {"type": "text"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=self._auth_headers(config))
            if resp.status_code != 200:
                logger.warning("WhatsApp mark-as-read failed (%s): %s", resp.status_code, resp.text)

    # ── Outbound delivery ─────────────────────────────────────────────────

    async def send_message(self, branch_id: UUID, customer_phone: str, text: str) -> None:
        account, config = await self._resolve_account_config(branch_id)
        if not account or not config:
            return

        url = f"{GRAPH_API_BASE}/{Config.WHATSAPP_API_VERSION}/{account.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": customer_phone,
            "type": "text",
            "text": {"body": text},
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=self._auth_headers(config))
            if resp.status_code != 200:
                logger.error("WhatsApp send failed (%s): %s", resp.status_code, resp.text)

    # ── Internal helpers ───────────────────────────────────────────────────

    async def _resolve_account_config(self, branch_id: UUID):
        account = await self.account_repo.get_by_branch_id(branch_id)
        if account is None or account.status == WhatsAppAccountStatus.disconnected:
            logger.error("No active WhatsApp account for branch %s", branch_id)
            return None, None

        config = await self.config_repo.get()
        if config is None:
            logger.error("WhatsApp config not found")
            return None, None

        return account, config

    @staticmethod
    def _auth_headers(config) -> dict:
        return {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }
