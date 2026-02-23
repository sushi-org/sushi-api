from __future__ import annotations

DEFAULT_TOOLS_ENABLED: dict[str, bool] = {
    "check_availability": True,
    "book_appointment": True,
    "list_bookings": True,
    "cancel_booking": True,
    "edit_booking": True,
    "escalate": True,
}

DEFAULT_REPLY_TEMPLATES: dict[str, dict[str, str]] = {
    "greeting": {
        "name": "Greeting",
        "content": (
            "👋 Hi! Welcome to [company_name] — [branch_name]. "
            "I can help you book an appointment 📅, answer questions about our services, "
            "or connect you with our team. How can I help you today?"
        ),
    },
    "availability_found": {
        "name": "Availability Found",
        "content": (
            "Great news! ✨ Here are the available slots for [service]:\n"
            "[slots]\n"
            "Which one works best for you?"
        ),
    },
    "availability_none": {
        "name": "No Availability",
        "content": (
            "😔 Unfortunately there are no openings for [service] in that time range. "
            "Would you like me to check other dates or another therapist?"
        ),
    },
    "booking_confirmed": {
        "name": "Booking Confirmation",
        "content": (
            "✅ You're all set! Here are your booking details:\n\n"
            "🔹 Service: [service]\n"
            "🔹 Therapist: [staff]\n"
            "🔹 Date: [date] at [time]\n"
            "🔹 Price: [price]\n\n"
            "Please arrive 10 minutes early. See you then! 😊"
        ),
    },
    "booking_slot_unavailable": {
        "name": "Slot Unavailable",
        "content": "😕 Sorry, that slot was just taken! Let me check what else is available for you.",
    },
    "escalation": {
        "name": "Escalation",
        "content": "🙋 Let me connect you with our team. Someone will be with you shortly!",
    },
}
