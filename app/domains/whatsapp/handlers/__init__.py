from fastapi import APIRouter

from app.domains.whatsapp.handlers.admin import router as admin_router
from app.domains.whatsapp.handlers.company_accounts import router as company_accounts_router
from app.domains.whatsapp.handlers.webhook import router as webhook_router

__all__ = ["whatsapp_admin_router", "whatsapp_webhook_router", "whatsapp_company_router"]

whatsapp_admin_router = admin_router
whatsapp_webhook_router = webhook_router

whatsapp_company_router = APIRouter(prefix="/api/v1")
whatsapp_company_router.include_router(
    company_accounts_router,
    prefix="/companies/{company_id}/whatsapp/accounts",
    tags=["whatsapp-accounts"],
)
