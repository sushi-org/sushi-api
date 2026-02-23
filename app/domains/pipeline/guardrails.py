from __future__ import annotations

ESCALATION_KEYWORDS: list[str] = [
    "speak to a human",
    "talk to someone",
    "real person",
    "speak to a person",
    "talk to a human",
    "customer service",
    "speak to manager",
]

DEFAULT_MAX_TURNS = 10


def check_keyword_escalation(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in ESCALATION_KEYWORDS)


def check_max_turns(agent_message_count: int, max_turns: int = DEFAULT_MAX_TURNS) -> bool:
    return agent_message_count >= max_turns
