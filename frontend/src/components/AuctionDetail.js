import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchRFQDetail } from "../services/api";
import BidForm from "./BidForm";
import ActivityLog from "./ActivityLog";

const TRIGGER_LABELS = {
  bid_received: "Any bid received in trigger window",
  any_rank_change: "Any supplier rank change in trigger window",
  l1_rank_change: "Lowest bidder (L1) change in trigger window",
};

function AuctionDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadDetail();
    const interval = setInterval(loadDetail, 10000);
    return () => clearInterval(interval);
  }, [id]); // re-fetch when RFQ id changes

  async function loadDetail() {
    try {
      const res = await fetchRFQDetail(id);
      setData(res.data);
      setError("");
    } catch (err) {
      setError("Failed to load auction details.");
    } finally {
      setLoading(false);
    }
  }

  function formatTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString();
  }

  function statusLabel(status) {
    if (status === "force_closed") return "Force Closed";
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  if (loading) return <p className="loading">Loading auction details...</p>;
  if (error) return <p className="error-box">{error}</p>;
  if (!data) return null;

  const { rfq, bids, activity_logs } = data;
  const isActive = rfq.status === "active";

  return (
    <div className="detail-page">
      {/* RFQ header info */}
      <div className="detail-header">
        <div>
          <h2>{rfq.name}</h2>
          <p className="ref-id">Ref: {rfq.reference_id}</p>
        </div>
        <span
          className="status-badge large"
          style={{
            backgroundColor:
              rfq.status === "active"
                ? "#16a34a"
                : rfq.status === "closed"
                ? "#6b7280"
                : "#dc2626",
          }}
        >
          {statusLabel(rfq.status)}
        </span>
      </div>

      {/* Time and configuration */}
      <div className="info-cards">
        <div className="info-card">
          <h4>Schedule</h4>
          <div className="info-row">
            <span>Bid Start:</span>
            <span>{formatTime(rfq.bid_start_time)}</span>
          </div>
          <div className="info-row">
            <span>Original Close:</span>
            <span>{formatTime(rfq.bid_close_time)}</span>
          </div>
          <div className="info-row highlight">
            <span>Current Close:</span>
            <span>{formatTime(rfq.current_close_time)}</span>
          </div>
          <div className="info-row">
            <span>Forced Close:</span>
            <span>{formatTime(rfq.forced_close_time)}</span>
          </div>
          <div className="info-row">
            <span>Pickup Date:</span>
            <span>{formatTime(rfq.pickup_date)}</span>
          </div>
        </div>

        <div className="info-card">
          <h4>Auction Configuration</h4>
          <div className="info-row">
            <span>Trigger Window (X):</span>
            <span>{rfq.trigger_window_minutes} minutes</span>
          </div>
          <div className="info-row">
            <span>Extension Duration (Y):</span>
            <span>{rfq.extension_duration_minutes} minutes</span>
          </div>
          <div className="info-row">
            <span>Extension Trigger:</span>
            <span>{TRIGGER_LABELS[rfq.trigger_type] || rfq.trigger_type}</span>
          </div>
        </div>
      </div>

      {/* Bid form (active auction only) */}
      {isActive && (
        <BidForm rfqId={rfq.id} onBidSubmitted={loadDetail} />
      )}

      {/* Supplier bids / rankings */}
      <div className="section">
        <h3>Supplier Bids &amp; Rankings</h3>
        {bids.length === 0 ? (
          <p className="muted">No bids submitted yet.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Carrier</th>
                  <th>Freight</th>
                  <th>Origin</th>
                  <th>Destination</th>
                  <th>Total Price</th>
                  <th>Transit Time</th>
                  <th>Validity</th>
                  <th>Submitted At</th>
                </tr>
              </thead>
              <tbody>
                {bids.map((bid) => (
                  <tr key={bid.id} className={bid.rank === 1 ? "l1-row" : ""}>
                    <td>
                      <span className={`rank-badge rank-${bid.rank}`}>
                        L{bid.rank}
                      </span>
                    </td>
                    <td className="bold">{bid.carrier_name}</td>
                    <td>₹{bid.freight_charges.toLocaleString()}</td>
                    <td>₹{bid.origin_charges.toLocaleString()}</td>
                    <td>₹{bid.destination_charges.toLocaleString()}</td>
                    <td className="bold">₹{bid.total_price.toLocaleString()}</td>
                    <td>{bid.transit_time}</td>
                    <td>{bid.validity}</td>
                    <td>{formatTime(bid.submitted_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Activity log */}
      <ActivityLog logs={activity_logs} />
    </div>
  );
}

export default AuctionDetail;
