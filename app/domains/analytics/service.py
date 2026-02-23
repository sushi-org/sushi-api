from __future__ import annotations

import datetime
from uuid import UUID

from sqlalchemy import Date, and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company.models import BookedVia, Booking, BookingStatus
from app.domains.messaging.models import (
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_home_analytics(
        self, company_id: UUID, branch_id: UUID | None = None
    ) -> dict:
        conversations = await self._conversation_metrics(company_id, branch_id)
        bookings = await self._booking_metrics(company_id, branch_id)
        revenue = await self._revenue_metrics(company_id, branch_id)
        messages = await self._message_metrics(company_id, branch_id)
        booking_trend, revenue_trend = await self._daily_trends(company_id, branch_id)
        conv_with_bookings = await self._conversations_with_bookings(
            company_id, branch_id
        )

        total_conv = conversations["total"]
        conversion_rate = (
            round(conv_with_bookings / total_conv * 100, 1) if total_conv > 0 else 0.0
        )

        return {
            "conversations": conversations,
            "bookings": bookings,
            "revenue": revenue,
            "messages": messages,
            "booking_trend": booking_trend,
            "revenue_trend": revenue_trend,
            "conversion_rate": conversion_rate,
            "conversations_with_bookings": conv_with_bookings,
        }

    # ── Conversation metrics ──────────────────────────────────────────────

    async def _conversation_metrics(
        self, company_id: UUID, branch_id: UUID | None
    ) -> dict:
        filters = [Conversation.company_id == company_id]
        if branch_id:
            filters.append(Conversation.branch_id == branch_id)

        stmt = select(
            func.count().label("total"),
            func.count(
                case(
                    (
                        and_(
                            Conversation.status == ConversationStatus.resolved,
                            Conversation.escalated_at.is_(None),
                        ),
                        1,
                    ),
                )
            ).label("resolved_by_ai"),
            func.count(
                case(
                    (
                        and_(
                            Conversation.status == ConversationStatus.resolved,
                            Conversation.escalated_at.isnot(None),
                        ),
                        1,
                    ),
                )
            ).label("resolved_by_human"),
            func.count(
                case(
                    (Conversation.status == ConversationStatus.escalated, 1),
                )
            ).label("escalated"),
            func.count(
                case(
                    (Conversation.status == ConversationStatus.active, 1),
                )
            ).label("active"),
        ).where(and_(*filters))

        result = await self.session.execute(stmt)
        row = result.one()

        concluded = row.resolved_by_ai + row.resolved_by_human + row.escalated
        rate = (row.resolved_by_ai / concluded * 100) if concluded > 0 else 0.0

        return {
            "total": row.total,
            "resolved_by_ai": row.resolved_by_ai,
            "resolved_by_human": row.resolved_by_human,
            "escalated": row.escalated,
            "active": row.active,
            "ai_resolution_rate": round(rate, 1),
        }

    # ── Booking metrics ───────────────────────────────────────────────────

    async def _booking_metrics(
        self, company_id: UUID, branch_id: UUID | None
    ) -> dict:
        filters = [
            Booking.company_id == company_id,
            Booking.status.in_([BookingStatus.confirmed, BookingStatus.completed]),
        ]
        if branch_id:
            filters.append(Booking.branch_id == branch_id)

        today = datetime.date.today()

        stmt = select(
            func.count().label("total"),
            func.count(
                case((Booking.booked_via == BookedVia.agent, 1))
            ).label("by_ai"),
            func.count(
                case((Booking.booked_via == BookedVia.member, 1))
            ).label("by_human"),
            func.count(
                case(
                    (
                        and_(
                            Booking.date == today,
                            Booking.status == BookingStatus.confirmed,
                        ),
                        1,
                    ),
                )
            ).label("upcoming_today"),
        ).where(and_(*filters))

        result = await self.session.execute(stmt)
        row = result.one()

        total = row.total or 0
        by_ai = row.by_ai or 0
        rate = (by_ai / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "by_ai": by_ai,
            "by_human": row.by_human or 0,
            "ai_booking_rate": round(rate, 1),
            "upcoming_today": row.upcoming_today or 0,
        }

    # ── Revenue metrics ───────────────────────────────────────────────────

    async def _revenue_metrics(
        self, company_id: UUID, branch_id: UUID | None
    ) -> dict:
        filters = [
            Booking.company_id == company_id,
            Booking.status.in_([BookingStatus.confirmed, BookingStatus.completed]),
        ]
        if branch_id:
            filters.append(Booking.branch_id == branch_id)

        stmt = select(
            func.coalesce(func.sum(Booking.price), 0).label("total"),
            func.coalesce(
                func.sum(
                    case(
                        (Booking.booked_via == BookedVia.agent, Booking.price),
                        else_=0,
                    )
                ),
                0,
            ).label("from_ai"),
            func.coalesce(
                func.sum(
                    case(
                        (Booking.booked_via == BookedVia.member, Booking.price),
                        else_=0,
                    )
                ),
                0,
            ).label("from_human"),
        ).where(and_(*filters))

        result = await self.session.execute(stmt)
        row = result.one()

        currency_stmt = (
            select(Booking.currency)
            .where(Booking.company_id == company_id)
            .limit(1)
        )
        currency_row = (await self.session.execute(currency_stmt)).scalar_one_or_none()

        return {
            "total": float(row.total),
            "from_ai": float(row.from_ai),
            "from_human": float(row.from_human),
            "currency": currency_row or "USD",
        }

    # ── Message metrics ───────────────────────────────────────────────────

    async def _message_metrics(
        self, company_id: UUID, branch_id: UUID | None
    ) -> dict:
        filters = [Conversation.company_id == company_id]
        if branch_id:
            filters.append(Conversation.branch_id == branch_id)

        stmt = (
            select(
                func.count().label("total"),
                func.count(
                    case((Message.role == MessageRole.agent, 1))
                ).label("from_ai"),
                func.count(
                    case((Message.role == MessageRole.customer, 1))
                ).label("from_customers"),
                func.count(
                    case((Message.role == MessageRole.member, 1))
                ).label("from_humans"),
            )
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(and_(*filters))
        )

        result = await self.session.execute(stmt)
        row = result.one()

        return {
            "total": row.total or 0,
            "from_ai": row.from_ai or 0,
            "from_customers": row.from_customers or 0,
            "from_humans": row.from_humans or 0,
        }

    # ── Daily trends (last 30 days) ──────────────────────────────────────

    async def _daily_trends(
        self, company_id: UUID, branch_id: UUID | None
    ) -> tuple[list[dict], list[dict]]:
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=29)

        # Group by when the booking was created, not appointment date
        created_date = cast(Booking.created_at, Date)

        filters = [
            Booking.company_id == company_id,
            Booking.status.in_([BookingStatus.confirmed, BookingStatus.completed]),
            created_date >= start_date,
            created_date <= today,
        ]
        if branch_id:
            filters.append(Booking.branch_id == branch_id)

        stmt = (
            select(
                created_date.label("date"),
                func.count().label("total"),
                func.count(
                    case((Booking.booked_via == BookedVia.agent, 1))
                ).label("by_ai"),
                func.count(
                    case((Booking.booked_via == BookedVia.member, 1))
                ).label("by_human"),
                func.coalesce(func.sum(Booking.price), 0).label("rev_total"),
                func.coalesce(
                    func.sum(
                        case(
                            (Booking.booked_via == BookedVia.agent, Booking.price),
                            else_=0,
                        )
                    ),
                    0,
                ).label("rev_ai"),
                func.coalesce(
                    func.sum(
                        case(
                            (Booking.booked_via == BookedVia.member, Booking.price),
                            else_=0,
                        )
                    ),
                    0,
                ).label("rev_human"),
            )
            .where(and_(*filters))
            .group_by(created_date)
            .order_by(created_date)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        data_by_date: dict[datetime.date, object] = {}
        for row in rows:
            data_by_date[row.date] = row

        booking_trend: list[dict] = []
        revenue_trend: list[dict] = []

        for i in range(30):
            d = start_date + datetime.timedelta(days=i)
            date_str = d.isoformat()
            row = data_by_date.get(d)

            if row:
                booking_trend.append(
                    {
                        "date": date_str,
                        "total": row.total,
                        "by_ai": row.by_ai,
                        "by_human": row.by_human,
                    }
                )
                revenue_trend.append(
                    {
                        "date": date_str,
                        "total": float(row.rev_total),
                        "from_ai": float(row.rev_ai),
                        "from_human": float(row.rev_human),
                    }
                )
            else:
                booking_trend.append(
                    {"date": date_str, "total": 0, "by_ai": 0, "by_human": 0}
                )
                revenue_trend.append(
                    {"date": date_str, "total": 0.0, "from_ai": 0.0, "from_human": 0.0}
                )

        return booking_trend, revenue_trend

    # ── Conversion rate ───────────────────────────────────────────────────

    async def _conversations_with_bookings(
        self, company_id: UUID, branch_id: UUID | None
    ) -> int:
        filters = [
            Booking.company_id == company_id,
            Booking.conversation_id.isnot(None),
            Booking.status.in_([BookingStatus.confirmed, BookingStatus.completed]),
        ]
        if branch_id:
            filters.append(Booking.branch_id == branch_id)

        stmt = select(
            func.count(func.distinct(Booking.conversation_id))
        ).where(and_(*filters))

        result = await self.session.execute(stmt)
        return result.scalar_one()
