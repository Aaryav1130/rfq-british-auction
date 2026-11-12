from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import RFQ, Bid, ActivityLog, AuctionStatus
from schemas import (
    RFQCreate, RFQResponse, AuctionDetailResponse,
    BidResponse, ActivityLogResponse,
)
from services.auction import update_auction_status

router = APIRouter(prefix="/api/rfqs", tags=["RFQs"])


@router.post("", response_model=RFQResponse, status_code=201)
def create_rfq(payload: RFQCreate, db: Session = Depends(get_db)):
    """Create a new RFQ with British Auction configuration."""

    # check uniqueness of reference_id
    exists = db.query(RFQ).filter(RFQ.reference_id == payload.reference_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="Reference ID already exists")

    rfq = RFQ(
        name=payload.name,
        reference_id=payload.reference_id,
        bid_start_time=payload.bid_start_time,
        bid_close_time=payload.bid_close_time,
        current_close_time=payload.bid_close_time,   # starts equal to bid_close
        forced_close_time=payload.forced_close_time,
        pickup_date=payload.pickup_date,
        trigger_window_minutes=payload.trigger_window_minutes,
        extension_duration_minutes=payload.extension_duration_minutes,
        trigger_type=payload.trigger_type,
        status=AuctionStatus.ACTIVE,
    )
    db.add(rfq)

    # log creation
    db.flush()  # so rfq.id is available
    db.add(ActivityLog(
        rfq_id=rfq.id,
        event_type="rfq_created",
        description=f"RFQ '{rfq.name}' created with British Auction enabled.",
        timestamp=datetime.now(timezone.utc),
    ))
    db.commit()
    db.refresh(rfq)

    return _rfq_to_response(db, rfq)


@router.get("", response_model=List[RFQResponse])
def list_rfqs(db: Session = Depends(get_db)):
    """List all RFQs with their current lowest bid."""
    rfqs = db.query(RFQ).order_by(RFQ.created_at.desc()).all()

    results = []
    for rfq in rfqs:
        update_auction_status(db, rfq)
        results.append(_rfq_to_response(db, rfq))
    return results


@router.get("/{rfq_id}", response_model=AuctionDetailResponse)
def get_rfq_detail(rfq_id: int, db: Session = Depends(get_db)):
    """Get full auction detail: RFQ info, all bids ranked, activity log."""
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    update_auction_status(db, rfq)

    bids = (
        db.query(Bid)
        .filter(Bid.rfq_id == rfq_id)
        .order_by(Bid.total_price.asc())
        .all()
    )
    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.rfq_id == rfq_id)
        .order_by(ActivityLog.timestamp.desc())
        .all()
    )

    return AuctionDetailResponse(
        rfq=_rfq_to_response(db, rfq),
        bids=[BidResponse.model_validate(b) for b in bids],
        activity_logs=[ActivityLogResponse.model_validate(l) for l in logs],
    )


# Helper to attach lowest bid to response

def _rfq_to_response(db: Session, rfq: RFQ) -> RFQResponse:
    """Build an RFQResponse including the current lowest bid amount."""
    lowest = (
        db.query(Bid.total_price)
        .filter(Bid.rfq_id == rfq.id)
        .order_by(Bid.total_price.asc())
        .first()
    )
    return RFQResponse(
        id=rfq.id,
        name=rfq.name,
        reference_id=rfq.reference_id,
        bid_start_time=rfq.bid_start_time,
        bid_close_time=rfq.bid_close_time,
        current_close_time=rfq.current_close_time,
        forced_close_time=rfq.forced_close_time,
        pickup_date=rfq.pickup_date,
        trigger_window_minutes=rfq.trigger_window_minutes,
        extension_duration_minutes=rfq.extension_duration_minutes,
        trigger_type=rfq.trigger_type.value if hasattr(rfq.trigger_type, 'value') else rfq.trigger_type,
        status=rfq.status.value if hasattr(rfq.status, 'value') else rfq.status,
        created_at=rfq.created_at,
        lowest_bid=lowest[0] if lowest else None,
    )
