from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass
class ToolContext:
    """Runtime context passed to every tool execution."""
    branch_id: UUID
    company_id: UUID
    conversation_id: UUID
    customer_phone: str
    customer_name: str | None


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def parameters(self) -> dict: ...

    @abstractmethod
    async def execute(self, arguments: dict[str, Any], context: ToolContext) -> dict: ...

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
