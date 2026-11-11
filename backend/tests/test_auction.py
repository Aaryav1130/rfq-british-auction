import sys
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

sys.path.append("D:\\British Auction\\backend")
from main import app
from database import SessionLocal
from models import RFQ, Bid, ActivityLog

client = TestClient(app)

def test_full_auction_lifecycle():
    print("--- 1. Testing Root Endpoint ---")
    res = client.get("/")
    assert res.status_code == 200, f"Root failed: {res.text}"
    print("Root API is healthy:", res.json())

    print("\n--- 2. Testing RFQ Creation with British Auction Config ---")
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
    print(f"Created RFQ #{rfq_id} successfully, initial status: {rfq_data['status']}")
    print(f"Initial Bid Close: {rfq_data['bid_close_time']}")
    print(f"Current Close: {rfq_data['current_close_time']}")
    print(f"Forced Close: {rfq_data['forced_close_time']}")

    print("\n--- 3. Testing Bid 1 Submission (Carrier A - ₹50,000) ---")
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
    print(f"Bid 1 submitted: Total = ₹{bid1['total_price']}, Rank = L{bid1['rank']}")
    assert bid1["rank"] == 1, "First bid must be L1"

    print("\n--- 4. Testing Bid 2 Submission (Carrier B - Higher ₹55,000, No L1 change) ---")
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
    print(f"Bid 2 submitted: Total = ₹{bid2['total_price']}, Rank = L{bid2['rank']}")
    assert bid2["rank"] == 2, "Second bid should be L2"

    # Detail check: Close time should NOT have extended because trigger_type is l1_rank_change and L1 did not change
    res = client.get(f"/api/rfqs/{rfq_id}")
    detail = res.json()
    print(f"Close time after higher bid: {detail['rfq']['current_close_time']}")
    assert detail['rfq']['current_close_time'] == rfq_data['current_close_time'], "Should not extend when L1 didn't change"

    print("\n--- 5. Testing Bid 3 Submission (Carrier C - Lower ₹45,000, L1 CHANGES!) ---")
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
    print(f"Bid 3 submitted: Total = ₹{bid3['total_price']}, Rank = L{bid3['rank']}")
    assert bid3["rank"] == 1, "Third bid must become the new L1"

    # Now verify extension happened
    res = client.get(f"/api/rfqs/{rfq_id}")
    detail = res.json()
    extended_close = datetime.fromisoformat(detail['rfq']['current_close_time'])
    original_close = datetime.fromisoformat(rfq_data['current_close_time'])
    print(f"Original Close: {original_close}")
    print(f"New Extended Close: {extended_close}")
    assert extended_close > original_close, "Auction close time must have been extended!"
    print("EXTENSION SUCCESSFUL! Time extended by 5 minutes due to L1 change.")

    print("\n--- 6. Testing Activity Logs ---")
    logs = detail["activity_logs"]
    print(f"Total activity logs recorded: {len(logs)}")
    for log in logs:
        print(f"  [{log['event_type']}] {log['description']}")
    
    assert any(l["event_type"] == "time_extended" for l in logs), "time_extended event must be logged"
    assert any(l["event_type"] == "bid_submitted" for l in logs), "bid_submitted event must be logged"

    print("\n--- 7. Testing Validation: Forced Close Ceiling ---")
    # For Bid 4 to be inside the trigger window:
    # Trigger window is 10 mins. So current_close must be within 10 minutes from now.
    # We set current_close to now + 3 minutes, and forced_close to now + 5 minutes.
    # Since extension_duration is 5 minutes, proposed_close = now + 8 minutes > forced_close (now + 5 minutes).
    # Therefore, new_close must be capped exactly at forced_close!
    test_now = datetime.now(timezone.utc)
    db = SessionLocal()
    rfq_obj = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    rfq_obj.current_close_time = test_now + timedelta(minutes=3)
    rfq_obj.forced_close_time = test_now + timedelta(minutes=5)
    db.commit()
    target_forced = rfq_obj.forced_close_time
    db.close()

    # Submit another winning bid (₹40,000) inside trigger window
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
    print(f"Current Close after near-forced extension: {cur_close}")
    print(f"Forced Close: {forced}")
    assert cur_close <= forced, "Auction current_close_time must NEVER exceed forced_close_time!"
    assert cur_close == forced, "Auction should be capped exactly at forced_close_time!"
    print("FORCED CLOSE CEILING VERIFIED: Successfully capped at forced_close_time without exceeding it!")

    print("\n=============================================")
    print("ALL TESTS PASSED! THE AUCTION SYSTEM WORKS END-TO-END.")
    print("=============================================")

if __name__ == "__main__":
    test_full_auction_lifecycle()
