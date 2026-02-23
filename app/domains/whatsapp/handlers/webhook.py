from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session
from app.domains.pipeline.contracts import InboundMessage
from app.domains.pipeline.dependencies import get_pipeline_service
from app.domains.pipeline.service import InboundPipelineService
from app.domains.whatsapp.dependencies import get_whatsapp_account_repo, get_whatsapp_config_repo
from app.domains.whatsapp.models import WhatsAppAccountStatus
from app.domains.whatsapp.repositories.account import WhatsAppAccountRepository
from app.domains.whatsapp.repositories.config import WhatsAppConfigRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    config_repo: WhatsAppConfigRepository = Depends(get_whatsapp_config_repo),
) -> Response:
    config = await config_repo.get()
    if config is None:
        logger.warning("Webhook verification failed — no config in DB")
        return Response(content="Forbidden", status_code=403)

    if hub_mode == "subscribe" and hub_verify_token == config.verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning("Webhook verification failed — token mismatch")
    return Response(content="Forbidden", status_code=403)


@router.post("")
async def receive_message(
    request: Request,
    account_repo: WhatsAppAccountRepository = Depends(get_whatsapp_account_repo),
    pipeline: InboundPipelineService = Depends(get_pipeline_service),
) -> dict:
    body = await request.json()
    logger.info("Incoming webhook payload")

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])

            if not phone_number_id or not messages:
                continue

            account = await account_repo.get_by_phone_number_id(phone_number_id)
            if account is None or account.status == WhatsAppAccountStatus.disconnected:
                logger.warning("No active WhatsApp account for phone_number_id %s", phone_number_id)
                continue

            customer_name: str | None = None
            if contacts:
                profile = contacts[0].get("profile", {})
                customer_name = profile.get("name")

            for msg in messages:
                msg_type = msg.get("type")
                if msg_type != "text":
                    logger.info("Skipping non-text message type=%s", msg_type)
                    continue

                inbound = InboundMessage(
                    branch_id=account.branch_id,
                    company_id=account.company_id,
                    channel="whatsapp",
                    customer_phone=msg.get("from", ""),
                    customer_name=customer_name,
                    text=msg["text"]["body"],
                    channel_message_id=msg.get("id", ""),
                )

                await pipeline.handle_inbound(inbound)

    return {"status": "ok"}
