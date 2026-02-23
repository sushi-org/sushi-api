from fastapi import APIRouter

from app.domains.messaging.handlers.conversation import router as conversation_router

messaging_router = APIRouter(prefix="/api/v1/companies/{company_id}", tags=["messaging"])
messaging_router.include_router(conversation_router, prefix="/conversations")
