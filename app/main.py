import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import dispose_db, init_db
from app.domains.agent.handlers import agent_router
from app.domains.analytics.handlers import router as analytics_router
from app.domains.auth.handler import router as auth_router
from app.domains.company.handlers import company_router
from app.domains.messaging.handlers import messaging_router
from app.domains.whatsapp.handlers import whatsapp_admin_router, whatsapp_company_router, whatsapp_webhook_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db("postgres")
    logger.info("Database engine created")
    yield
    await dispose_db()
    logger.info("Database engine disposed")


app = FastAPI(title="Sushi API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(whatsapp_webhook_router)
app.include_router(whatsapp_admin_router)
app.include_router(whatsapp_company_router)
app.include_router(auth_router)
app.include_router(company_router)
app.include_router(messaging_router)
app.include_router(agent_router)
app.include_router(analytics_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
