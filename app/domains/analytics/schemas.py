from __future__ import annotations

from pydantic import BaseModel


class ConversationMetrics(BaseModel):
    total: int
    resolved_by_ai: int
    resolved_by_human: int
    escalated: int
    active: int
    ai_resolution_rate: float


class BookingMetrics(BaseModel):
    total: int
    by_ai: int
    by_human: int
    ai_booking_rate: float
    upcoming_today: int


class RevenueMetrics(BaseModel):
    total: float
    from_ai: float
    from_human: float
    currency: str


class MessageMetrics(BaseModel):
    total: int
    from_ai: int
    from_customers: int
    from_humans: int


class DailyBookingTrend(BaseModel):
    date: str
    total: int
    by_ai: int
    by_human: int


class DailyRevenueTrend(BaseModel):
    date: str
    total: float
    from_ai: float
    from_human: float


class HomeAnalyticsResponse(BaseModel):
    conversations: ConversationMetrics
    bookings: BookingMetrics
    revenue: RevenueMetrics
    messages: MessageMetrics
    booking_trend: list[DailyBookingTrend]
    revenue_trend: list[DailyRevenueTrend]
    conversion_rate: float
    conversations_with_bookings: int
