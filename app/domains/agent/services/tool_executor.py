from __future__ import annotations

import logging
import time
from uuid import UUID

from app.domains.agent.repositories.tool_execution import ToolExecutionRepository
from app.domains.agent.tools.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Runs a tool call, logs the ToolExecution audit record, and returns the result."""

    def __init__(self, tool_execution_repo: ToolExecutionRepository) -> None:
        self._repo = tool_execution_repo

    async def run(
        self,
        tool: BaseTool,
        tool_name: str,
        tool_call_id: str,
        arguments: dict,
        context: ToolContext,
        conversation_id: UUID,
        msg_id: str = "",
    ) -> dict:
        start_ms = time.monotonic()
        exec_status = "success"
        try:
            result = await tool.execute(arguments, context)
        except Exception as exc:
            logger.exception("Step 5 - msg=%s: Tool %s failed", msg_id, tool_name)
            result = {"error": str(exc)}
            exec_status = "failure"

        duration_ms = int((time.monotonic() - start_ms) * 1000)
        logger.info("Step 5 - msg=%s: Tool %s %s (%dms)", msg_id, tool_name, exec_status, duration_ms)

        await self._repo.create(
            conversation_id=conversation_id,
            tool=tool_name,
            input=arguments,
            output=result,
            status=exec_status,
            duration_ms=duration_ms,
        )
        return result
