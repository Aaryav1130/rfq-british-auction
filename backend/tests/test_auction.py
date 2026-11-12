import os
import sys
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

# make sure our backend package is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app
from database import SessionLocal
from models import RFQ, Bid, ActivityLog

client = TestClient(app)

def test_full_auction_lifecycle():
    print("--- 1. Testing Root Endpoint ---")
    res = client.get("/")
    assert res.status_code == 200, f"Root failed: {res.text}"
    print("Root API is healthy:", res.json())

    print("\n--- 2. Creating RFQ with British Auction Config ---")
    now = datetime.now(timezone.utc)
    bid_start = now - timedelta(minutes=5)
    bid_close = now + timedelta(minutes=5)
    forced_close = now + timedelta(minutes=15)
    pickup = now + timedelta(days=2)

    rfq_payload = {
        "name": "Mumbai - Delhi Freight Route Q1",
        "reference_id": f"RFQ-TEST-{int(now.timestamp())}",
        "bid_start_time": bid_start.isoformat(),
        "bid_close_time": bid_close.isoformat(),
        "forced_close_time": forced_close.isoformat(),
        "pickup_date": pickup.isoformat(),
        "trigger_window_minutes": 10,  # inside window since bid_close is in 5 mins
        "extension_duration_minutes": 5,
        "trigger_type": "l1_rank_change"
    }

    res = client.post("/api/rfqs", json=rfq_payload)
    assert res.status_code == 201, f"Create RFQ failed: {res.text}"
    rfq_data = res.json()
    rfq_id = rfq_data["id"]
    print(f"Created RFQ #{rfq_id}, status: {rfq_data['status']}")
    print(f"Bid Close: {rfq_data['bid_close_time']}")
    print(f"Forced Close: {rfq_data['forced_close_time']}")

    # -- Bid 1: DHL at 50k (becomes L1 since its the only one)
    print("\n--- 3. Bid 1 (DHL - 50,000) ---")
    bid1_payload = {
        "carrier_name": "DHL Global Forwarding",
        "freight_charges": 40000.0,
        "origin_charges": 5000.0,
        "destination_charges": 5000.0,
        "transit_time": "3 Days",
        "validity": "7 Days"
    }
    res = client.post(f"/api/rfqs/{rfq_id}/bids", json=bid1_payload)
    assert res.status_code == 201, f"Bid 1 failed: {res.text}"
    bid1 = res.json()
    print(f"Total = {bid1['total_price']}, Rank = L{bid1['rank']}")
    assert bid1["rank"] == 1, "First bid must be L1"

    # -- Bid 2: Maersk at 55k, higher so L1 should NOT change
    print("\n--- 4. Bid 2 (Maersk - 55,000, no L1 change expected) ---")
    bid2_payload = {
        "carrier_name": "Maersk Logistics",
        "freight_charges": 45000.0,
        "origin_charges": 5000.0,
        "destination_charges": 5000.0,
        "transit_time": "4 Days",
        "validity": "5 Days"
    }
    res = client.post(f"/api/rfqs/{rfq_id}/bids", json=bid2_payload)
    assert res.status_code == 201, f"Bid 2 failed: {res.text}"
    bid2 = res.json()
    print(f"Total = {bid2['total_price']}, Rank = L{bid2['rank']}")
    assert bid2["rank"] == 2

    # close time should stay the same (no L1 change)
    res = client.get(f"/api/rfqs/{rfq_id}")
    detail = res.json()
    print(f"Close time after higher bid: {detail['rfq']['current_close_time']}")
    assert detail['rfq']['current_close_time'] == rfq_data['current_close_time'], \
        "Should not extend when L1 didn't change"

    # -- Bid 3: BlueDart at 45k, should become new L1 and trigger extension
    print("\n--- 5. Bid 3 (BlueDart - 45,000, L1 CHANGES) ---")
    bid3_payload = {
        "carrier_name": "BlueDart Express",
        "freight_charges": 35000.0,
        "origin_charges": 5000.0,
        "destination_charges": 5000.0,
        "transit_time": "2 Days",
        "validity": "10 Days"
    }
    res = client.post(f"/api/rfqs/{rfq_id}/bids", json=bid3_payload)
    assert res.status_code == 201, f"Bid 3 failed: {res.text}"
    bid3 = res.json()
    print(f"Total = {bid3['total_price']}, Rank = L{bid3['rank']}")
    assert bid3["rank"] == 1, "BlueDart should be new L1"

    # verify the extension actually happened
    res = client.get(f"/api/rfqs/{rfq_id}")
    detail = res.json()
    extended_close = datetime.fromisoformat(detail['rfq']['current_close_time'])
    original_close = datetime.fromisoformat(rfq_data['current_close_time'])
    print(f"Original Close: {original_close}")
    print(f"Extended Close: {extended_close}")
    assert extended_close > original_close, "Close time must have been extended!"
    print("EXTENSION WORKED")

    # -- Check activity logs
    print("\n--- 6. Activity Logs ---")
    logs = detail["activity_logs"]
    print(f"Total logs: {len(logs)}")
    for log in logs:
        print(f"  [{log['event_type']}] {log['description']}")
    
    assert any(l["event_type"] == "time_extended" for l in logs), "Missing time_extended log"
    assert any(l["event_type"] == "bid_submitted" for l in logs), "Missing bid_submitted log"

    # -- Forced close ceiling test
    # Set current_close to now+3min, forced to now+5min.
    # Extension of 5min would push to now+8min which exceeds forced.
    # So it should cap at forced_close.
    print("\n--- 7. Forced Close Ceiling ---")
    test_now = datetime.now(timezone.utc)
    db = SessionLocal()
    rfq_obj = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    rfq_obj.current_close_time = test_now + timedelta(minutes=3)
    rfq_obj.forced_close_time = test_now + timedelta(minutes=5)
    db.commit()
    target_forced = rfq_obj.forced_close_time
    db.close()

    bid4_payload = {
        "carrier_name": "FedEx Supply Chain",
        "freight_charges": 30000.0,
        "origin_charges": 5000.0,
        "destination_charges": 5000.0,
        "transit_time": "2 Days",
        "validity": "10 Days"
    }
    res = client.post(f"/api/rfqs/{rfq_id}/bids", json=bid4_payload)
    assert res.status_code == 201
    
    res = client.get(f"/api/rfqs/{rfq_id}")
    detail = res.json()
    cur_close = datetime.fromisoformat(detail['rfq']['current_close_time'])
    forced = datetime.fromisoformat(detail['rfq']['forced_close_time'])
    print(f"Current Close: {cur_close}")
    print(f"Forced Close: {forced}")
    assert cur_close <= forced, "current_close must NEVER exceed forced_close!"
    assert cur_close == forced, "Should be capped exactly at forced_close"
    print("FORCED CLOSE CEILING VERIFIED")

    print("\n=== ALL TESTS PASSED ===")

if __name__ == "__main__":
    test_full_auction_lifecycle()
