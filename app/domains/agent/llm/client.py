from __future__ import annotations

import json
import logging
import time

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from app.config import Config

logger = logging.getLogger(__name__)


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=Config.OPENROUTER_BASE_URL,
        api_key=Config.OPENROUTER_API_KEY,
    )


async def chat_completion(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    msg_id: str = "",
) -> ChatCompletion:
    client = _get_client()
    kwargs: dict = {
        "model": model,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    prefix = f"Step 5 - msg={msg_id}: " if msg_id else ""
    logger.info("%sLLM request (model=%s messages=%d tools=%d)", prefix, model, len(messages), len(tools) if tools else 0)
    start = time.monotonic()

    try:
        response = await client.chat.completions.create(**kwargs)
    except Exception:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception("%sLLM failed model=%s elapsed=%dms", prefix, model, elapsed_ms)
        raise

    elapsed_ms = int((time.monotonic() - start) * 1000)
    usage = response.usage
    logger.info(
        "%sLLM response (elapsed=%dms tokens=%s)",
        prefix, elapsed_ms, usage.total_tokens if usage else "?",
    )
    return response


def parse_tool_calls(response: ChatCompletion) -> list[dict]:
    """Extract tool calls from a ChatCompletion response."""
    message = response.choices[0].message
    if not message.tool_calls:
        return []

    calls = []
    for tc in message.tool_calls:
        try:
            arguments = json.loads(tc.function.arguments)
        except (json.JSONDecodeError, TypeError):
            arguments = {}
        calls.append({
            "id": tc.id,
            "name": tc.function.name,
            "arguments": arguments,
        })
    return calls


def get_response_text(response: ChatCompletion) -> str | None:
    """Extract the text content from a ChatCompletion response."""
    message = response.choices[0].message
    return message.content
