from __future__ import annotations

import json

from app.domains.agent.services.agent_context_loader import AgentRunContext


class BusinessContextSection:
    def render(self, ctx: AgentRunContext) -> str:
        parts: list[str] = ["\n--- Company & Branch Context ---"]

        if ctx.company:
            parts.append(f"Company: {ctx.company.name}")
        if ctx.branch:
            parts.append(f"Branch: {ctx.branch.name}")
            if ctx.branch.address:
                parts.append(f"Address: {ctx.branch.address}")
            if ctx.branch.operating_hours:
                parts.append(f"Operating Hours: {json.dumps(ctx.branch.operating_hours)}")

        if ctx.active_services:
            parts.append("\nServices offered:")
            for svc in ctx.active_services:
                price_str = f"${svc.default_price}" if svc.default_price else "N/A"
                desc = f": {svc.description}" if svc.description else ""
                parts.append(
                    f"  - {svc.name} (ID: {svc.id}, {price_str}, {svc.default_duration_minutes}min){desc}"
                )

        if ctx.active_staff:
            parts.append("\nStaff:")
            for s in ctx.active_staff:
                parts.append(f"  - {s.name} (ID: {s.id})")

        return "\n".join(parts)
