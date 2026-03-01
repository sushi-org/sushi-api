from __future__ import annotations

from typing import Callable

from app.domains.agent.tools.base import BaseTool


class ToolRegistry:
    """Central registry mapping tool names to factory callables.

    Factories receive their dependencies at registration time (via closure),
    so the registry itself has no dependencies.

    Usage:
        registry = ToolRegistry()
        registry.register("check_availability", lambda: CheckAvailabilityTool(scheduling_svc))
        enabled_tools = registry.build_enabled({"check_availability": True})
    """

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], BaseTool]] = {}

    def register(self, name: str, factory: Callable[[], BaseTool]) -> None:
        self._factories[name] = factory

    def build_enabled(self, enabled_map: dict[str, bool]) -> dict[str, BaseTool]:
        """Build only the tools that are enabled according to the agent config."""
        result: dict[str, BaseTool] = {}
        for name, enabled in enabled_map.items():
            if enabled and name in self._factories:
                result[name] = self._factories[name]()
        return result

    def all_registered(self) -> list[str]:
        return list(self._factories.keys())
