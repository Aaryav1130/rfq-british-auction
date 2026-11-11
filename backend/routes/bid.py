from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import RFQ, Bid, AuctionStatus
from schemas import BidCreate, BidResponse
from services.auction import process_new_bid, update_auction_status

router = APIRouter(prefix="/api/rfqs/{rfq_id}/bids", tags=["Bids"])


@router.post("", response_model=BidResponse, status_code=201)
def submit_bid(rfq_id: int, payload: BidCreate, db: Session = Depends(get_db)):
    """
    Submit a new bid / quote for an RFQ.
    Triggers the British Auction extension logic automatically.
    """
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    # make sure status is up-to-date before we check
    update_auction_status(db, rfq)

    if rfq.status != AuctionStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Auction is {rfq.status.value} — bids are no longer accepted."
        )

    now = datetime.now(timezone.utc)
    if now < rfq.bid_start_time:
        raise HTTPException(
            status_code=400,
            detail="Bidding has not started yet."
        )

    total = payload.freight_charges + payload.origin_charges + payload.destination_charges

    new_bid = Bid(
        rfq_id=rfq_id,
        carrier_name=payload.carrier_name,
        freight_charges=payload.freight_charges,
        origin_charges=payload.origin_charges,
        destination_charges=payload.destination_charges,
        total_price=total,
        transit_time=payload.transit_time,
        validity=payload.validity,
        submitted_at=now,
    )
    db.add(new_bid)
    db.flush()  # get the id assigned

    # run the british auction extension engine
    process_new_bid(db, rfq, new_bid)

    db.refresh(new_bid)
    return BidResponse.model_validate(new_bid)
