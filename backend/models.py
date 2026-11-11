import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    Enum, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from database import Base


class AuctionStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    FORCE_CLOSED = "force_closed"


class TriggerType(str, enum.Enum):
    BID_RECEIVED = "bid_received"
    ANY_RANK_CHANGE = "any_rank_change"
    L1_RANK_CHANGE = "l1_rank_change"


class RFQ(Base):
    __tablename__ = "rfqs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    reference_id = Column(String(100), unique=True, nullable=False)

    bid_start_time = Column(DateTime(timezone=True), nullable=False)
    bid_close_time = Column(DateTime(timezone=True), nullable=False)       # original close
    current_close_time = Column(DateTime(timezone=True), nullable=False)   # may be extended
    forced_close_time = Column(DateTime(timezone=True), nullable=False)

    pickup_date = Column(DateTime(timezone=True), nullable=False)

    # british auction config
    trigger_window_minutes = Column(Integer, nullable=False)       # X
    extension_duration_minutes = Column(Integer, nullable=False)   # Y
    trigger_type = Column(Enum(TriggerType), nullable=False)

    status = Column(
        Enum(AuctionStatus),
        default=AuctionStatus.ACTIVE,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    bids = relationship("Bid", back_populates="rfq", order_by="Bid.total_price")
    activity_logs = relationship(
        "ActivityLog", back_populates="rfq",
        order_by="ActivityLog.timestamp.desc()"
    )


class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    rfq_id = Column(Integer, ForeignKey("rfqs.id"), nullable=False)

    carrier_name = Column(String(255), nullable=False)
    freight_charges = Column(Float, nullable=False)
    origin_charges = Column(Float, nullable=False)
    destination_charges = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)     # freight + origin + dest

    transit_time = Column(String(100), nullable=False)
    validity = Column(String(100), nullable=False)  # e.g. "7 days"

    submitted_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    rank = Column(Integer, nullable=True)

    rfq = relationship("RFQ", back_populates="bids")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    rfq_id = Column(Integer, ForeignKey("rfqs.id"), nullable=False)

    event_type = Column(String(50), nullable=False)   # bid_submitted | time_extended
    description = Column(Text, nullable=False)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    bid_id = Column(Integer, ForeignKey("bids.id"), nullable=True)

    rfq = relationship("RFQ", back_populates="activity_logs")
