"""
Auction engine – handles bid-time extension logic for British Auctions.

The three trigger modes:
  1) bid_received      – any bid in the trigger window extends the clock
  2) any_rank_change   – extend only when supplier rankings shuffle
  3) l1_rank_change    – extend only when the lowest-priced bidder changes
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from models import RFQ, Bid, ActivityLog, TriggerType, AuctionStatus


def update_auction_status(db: Session, rfq: RFQ):
    """
    Check the clock and move the auction to closed / force_closed
    if the time has passed.  Called before most read operations so
    the status stays fresh without needing a background scheduler.
    """
    if rfq.status != AuctionStatus.ACTIVE:
        return

    now = datetime.now(timezone.utc)

    if now >= rfq.forced_close_time:
        rfq.status = AuctionStatus.FORCE_CLOSED
        db.add(ActivityLog(
            rfq_id=rfq.id,
            event_type="auction_force_closed",
            description="Auction force-closed — forced bid close time reached.",
            timestamp=now,
        ))
        db.commit()
    elif now >= rfq.current_close_time:
        rfq.status = AuctionStatus.CLOSED
        db.add(ActivityLog(
            rfq_id=rfq.id,
            event_type="auction_closed",
            description="Auction closed — bid close time reached with no further extension.",
            timestamp=now,
        ))
        db.commit()


def recalculate_rankings(db: Session, rfq_id: int):
    """Re-rank all bids for an RFQ by total_price ascending (L1 = cheapest)."""
    bids = (
        db.query(Bid)
        .filter(Bid.rfq_id == rfq_id)
        .order_by(Bid.total_price.asc())
        .all()
    )
    for position, bid in enumerate(bids, start=1):
        bid.rank = position
    db.flush()


def process_new_bid(db: Session, rfq: RFQ, new_bid: Bid):
    """
    Called right after a new bid is saved.
    1. Capture old rankings / L1
    2. Recalculate rankings
    3. If inside the trigger window, check the extension condition
    4. Extend auction clock if appropriate (never past forced close)
    5. Log everything
    """
    now = datetime.now(timezone.utc)

    # ── 1. snapshot old state ──────────────────────────────────────────
    old_bids = (
        db.query(Bid)
        .filter(Bid.rfq_id == rfq.id, Bid.id != new_bid.id)
        .order_by(Bid.total_price.asc())
        .all()
    )
    old_l1_id = old_bids[0].id if old_bids else None
    old_rankings = {b.id: b.rank for b in old_bids}

    # ── 2. recalculate rankings including the new bid ─────────────────
    recalculate_rankings(db, rfq.id)

    # reload to get updated ranks
    all_bids = (
        db.query(Bid)
        .filter(Bid.rfq_id == rfq.id)
        .order_by(Bid.total_price.asc())
        .all()
    )
    new_l1_id = all_bids[0].id if all_bids else None

    # ── 3. log the bid submission ─────────────────────────────────────
    db.add(ActivityLog(
        rfq_id=rfq.id,
        event_type="bid_submitted",
        description=(
            f"{new_bid.carrier_name} submitted a bid of ₹{new_bid.total_price:,.2f} "
            f"(freight: ₹{new_bid.freight_charges:,.2f}, origin: ₹{new_bid.origin_charges:,.2f}, "
            f"dest: ₹{new_bid.destination_charges:,.2f})"
        ),
        timestamp=now,
        bid_id=new_bid.id,
    ))

    # ── 4. check if we are inside the trigger window ──────────────────
    window_start = rfq.current_close_time - timedelta(minutes=rfq.trigger_window_minutes)
    in_trigger_window = window_start <= now <= rfq.current_close_time

    if not in_trigger_window:
        db.commit()
        return  # nothing to extend

    # ── 5. evaluate the configured trigger condition ──────────────────
    should_extend = False
    reason = ""

    if rfq.trigger_type == TriggerType.BID_RECEIVED:
        should_extend = True
        reason = f"Bid received from {new_bid.carrier_name} during trigger window"

    elif rfq.trigger_type == TriggerType.ANY_RANK_CHANGE:
        # check whether any existing supplier's rank shifted
        rank_changed = False
        for bid in all_bids:
            if bid.id == new_bid.id:
                continue
            prev_rank = old_rankings.get(bid.id)
            if prev_rank is not None and prev_rank != bid.rank:
                rank_changed = True
                break
        # a brand-new bid entering also counts as a ranking change
        if not old_bids:
            rank_changed = False  # first bid ever, no prior ranking existed
        elif new_bid.id not in old_rankings:
            # new entrant — rankings shifted if it didn't land last
            if new_bid.rank < len(all_bids):
                rank_changed = True

        if rank_changed:
            should_extend = True
            reason = f"Supplier rankings changed after bid from {new_bid.carrier_name}"

    elif rfq.trigger_type == TriggerType.L1_RANK_CHANGE:
        if old_l1_id is not None and new_l1_id != old_l1_id:
            new_l1_name = all_bids[0].carrier_name
            old_l1 = next((b for b in all_bids if b.id == old_l1_id), None)
            old_l1_name = old_l1.carrier_name if old_l1 else "unknown"
            should_extend = True
            reason = (
                f"Lowest bidder (L1) changed from {old_l1_name} to {new_l1_name}"
            )

    # ── 6. extend the clock if triggered ──────────────────────────────
    if should_extend:
        proposed_close = rfq.current_close_time + timedelta(
            minutes=rfq.extension_duration_minutes
        )
        # hard rule: never exceed forced close
        new_close = min(proposed_close, rfq.forced_close_time)

        if new_close > rfq.current_close_time:
            old_close_str = rfq.current_close_time.strftime("%H:%M:%S")
            rfq.current_close_time = new_close
            new_close_str = new_close.strftime("%H:%M:%S")

            db.add(ActivityLog(
                rfq_id=rfq.id,
                event_type="time_extended",
                description=(
                    f"Auction extended from {old_close_str} to {new_close_str} UTC. "
                    f"Reason: {reason}"
                ),
                timestamp=now,
                bid_id=new_bid.id,
            ))

    db.commit()
