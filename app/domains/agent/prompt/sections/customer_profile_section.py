from __future__ import annotations

from app.domains.agent.services.agent_context_loader import AgentRunContext

_MILESTONE_VISITS = {5, 10, 25, 50, 100}


class CustomerProfileSection:
    def render(self, ctx: AgentRunContext) -> str:
        parts: list[str] = ["\n--- Customer Profile ---"]

        if ctx.customer_name:
            parts.append(f"Name: {ctx.customer_name}")

        if ctx.customer_history is None or not ctx.customer_history.is_returning:
            parts.append(
                "Status: New customer — welcome them warmly and guide them through booking for the first time."
            )
        else:
            h = ctx.customer_history
            visit_word = "visit" if h.visit_count == 1 else "visits"
            parts.append(f"Status: Returning customer — {h.visit_count} completed {visit_word}")

            if h.last_visit_date:
                date_str = h.last_visit_date.strftime("%b %d, %Y")
                if h.weeks_since_last_visit is not None:
                    week_word = "week" if h.weeks_since_last_visit == 1 else "weeks"
                    date_str += f" ({h.weeks_since_last_visit} {week_word} ago)"
                parts.append(f"Last visit: {date_str}")

            if h.preferred_service_name:
                parts.append(f"Preferred service: {h.preferred_service_name}")
            if h.preferred_staff_name:
                parts.append(f"Preferred staff: {h.preferred_staff_name}")
            if h.preferred_day_of_week:
                parts.append(f"Preferred day: {h.preferred_day_of_week}")

            name_ref = ctx.customer_name if ctx.customer_name else "this customer"
            if ctx.is_new_conversation:
                rules = [f"- IMPORTANT: This is the first response in this conversation. Begin by warmly welcoming back {name_ref}."]
            else:
                rules = [f"- Use the customer's name ({name_ref}) naturally when it fits (e.g. confirming a booking, answering a question). Do not re-introduce yourself."]
            if h.preferred_service_name:
                rules.append(
                    f"- When they ask to book without specifying a service, proactively suggest {h.preferred_service_name}."
                )
            if h.preferred_staff_name:
                rules.append(
                    f"- When they ask to book without specifying staff, proactively suggest {h.preferred_staff_name}."
                )
            if h.next_visit_number in _MILESTONE_VISITS:
                rules.append(
                    f"- Their next booking will be their {h.next_visit_number}th visit — celebrate this milestone in your booking confirmation message!"
                )
            parts.append("\nPersonalization rules:\n" + "\n".join(rules))

        return "\n".join(parts)
