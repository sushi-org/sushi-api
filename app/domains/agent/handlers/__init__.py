from fastapi import APIRouter

from app.domains.agent.handlers.agent import router as agent_config_router
from app.domains.agent.handlers.knowledge import router as knowledge_router
from app.domains.agent.handlers.template import router as template_router

_prefix = "/api/v1/companies/{company_id}/branches/{branch_id}/agent"

agent_router = APIRouter()
agent_router.include_router(agent_config_router, prefix=_prefix, tags=["agent"])
agent_router.include_router(knowledge_router, prefix=f"{_prefix}/knowledge", tags=["knowledge"])
agent_router.include_router(template_router, prefix=f"{_prefix}/templates", tags=["templates"])
