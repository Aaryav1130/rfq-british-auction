from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, field_validator


# ── Trigger type as plain string enum for pydantic ────────────────────────
TRIGGER_TYPES = ["bid_received", "any_rank_change", "l1_rank_change"]
AUCTION_STATUSES = ["active", "closed", "force_closed"]


# ── RFQ Schemas ───────────────────────────────────────────────────────────

class RFQCreate(BaseModel):
    name: str
    reference_id: str
    bid_start_time: datetime
    bid_close_time: datetime
    forced_close_time: datetime
    pickup_date: datetime
    trigger_window_minutes: int
    extension_duration_minutes: int
    trigger_type: str

    @field_validator("forced_close_time")
    @classmethod
    def forced_close_after_bid_close(cls, v, info):
        bid_close = info.data.get("bid_close_time")
        if bid_close and v <= bid_close:
            raise ValueError("Forced close time must be later than bid close time")
        return v

    @field_validator("trigger_type")
    @classmethod
    def valid_trigger_type(cls, v):
        if v not in TRIGGER_TYPES:
            raise ValueError(f"trigger_type must be one of {TRIGGER_TYPES}")
        return v

    @field_validator("trigger_window_minutes", "extension_duration_minutes")
    @classmethod
    def positive_minutes(cls, v):
        if v <= 0:
            raise ValueError("Minutes must be a positive number")
        return v


class RFQResponse(BaseModel):
    id: int
    name: str
    reference_id: str
    bid_start_time: datetime
    bid_close_time: datetime
    current_close_time: datetime
    forced_close_time: datetime
    pickup_date: datetime
    trigger_window_minutes: int
    extension_duration_minutes: int
    trigger_type: str
    status: str
    created_at: Optional[datetime] = None
    lowest_bid: Optional[float] = None

    model_config = {"from_attributes": True}


# ── Bid Schemas ───────────────────────────────────────────────────────────

class BidCreate(BaseModel):
    carrier_name: str
    freight_charges: float
    origin_charges: float
    destination_charges: float
    transit_time: str
    validity: str

    @field_validator("freight_charges", "origin_charges", "destination_charges")
    @classmethod
    def non_negative_charges(cls, v):
        if v < 0:
            raise ValueError("Charges cannot be negative")
        return v


class BidResponse(BaseModel):
    id: int
    rfq_id: int
    carrier_name: str
    freight_charges: float
    origin_charges: float
    destination_charges: float
    total_price: float
    transit_time: str
    validity: str
    submitted_at: datetime
    rank: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Activity Log Schema ──────────────────────────────────────────────────

class ActivityLogResponse(BaseModel):
    id: int
    rfq_id: int
    event_type: str
    description: str
    timestamp: datetime
    bid_id: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Combined detail response ─────────────────────────────────────────────

class AuctionDetailResponse(BaseModel):
    rfq: RFQResponse
    bids: List[BidResponse]
    activity_logs: List[ActivityLogResponse]
