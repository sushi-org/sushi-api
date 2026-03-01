from __future__ import annotations

from app.domains.agent.services.agent_context_loader import AgentRunContext


class ToolRulesSection:
    def render(self, ctx: AgentRunContext) -> str:
        return (
            "\n--- Tool Usage Rules ---\n"
            "You have tools available for managing appointments. Follow these rules strictly:\n"
            "- ALWAYS call check_availability before suggesting available times.\n"
            "- ALWAYS call book_appointment to book. NEVER confirm a booking unless the tool returned success.\n"
            "- To cancel or edit a booking, FIRST call list_bookings to find the booking, "
            "then call cancel_booking or edit_booking with the booking_id.\n"
            "- NEVER claim an action was performed unless the corresponding tool returned a successful result.\n"
            "- When calling tools, always use dates relative to today's date shown above."
        )
