from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    # WhatsApp (access_token / verify_token live in the DB whatsapp_config table)
    WHATSAPP_APP_ID: str = os.getenv("WHATSAPP_APP_ID", "")
    WHATSAPP_APP_SECRET: str = os.getenv("WHATSAPP_APP_SECRET", "")
    WHATSAPP_API_VERSION: str = os.getenv("WHATSAPP_API_VERSION", "v21.0")

    # Postgres
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "34.126.81.157")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USERNAME: str = os.getenv("POSTGRES_USERNAME", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "Tomokilam3!")
    POSTGRES_DB_NAME: str = os.getenv("POSTGRES_DB_NAME", "postgres")
    SQL_COMMAND_ECHO: bool = os.getenv("SQL_COMMAND_ECHO", "false").lower() == "true"

    # Auth
    AUTH_SYNC_SECRET: str = os.getenv("AUTH_SYNC_SECRET", "HELLO")
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "super-secret-admin-key")

    # OpenRouter (LLM)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "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")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_DEFAULT_MODEL: str = os.getenv("OPENROUTER_DEFAULT_MODEL", "openai/gpt-4o-mini")
