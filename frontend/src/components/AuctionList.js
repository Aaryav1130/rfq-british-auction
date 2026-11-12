import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchRFQs } from "../services/api";

const STATUS_COLORS = {
  active: "#16a34a",
  closed: "#6b7280",
  force_closed: "#dc2626",
};

function AuctionList() {
  const [rfqs, setRfqs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRFQs();
    // refresh every 15 seconds to keep statuses current
    const interval = setInterval(loadRFQs, 15000);
    return () => clearInterval(interval);
  }, []);

  async function loadRFQs() {
    try {
      const res = await fetchRFQs();
      setRfqs(res.data);
    } catch (err) {
      console.error("Failed to load RFQs:", err);
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

  if (loading) {
    return <p className="loading">Loading auctions...</p>;
  }

  return (
    <div>
      <div className="page-header">
        <h2>All Auctions</h2>
        <Link to="/create" className="btn-primary">
          + Create RFQ
        </Link>
      </div>

      {rfqs.length === 0 ? (
        <div className="empty-state">
          <p>No auctions yet. Create your first RFQ to get started.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>RFQ Name</th>
                <th>Reference ID</th>
                <th>Lowest Bid</th>
                <th>Current Close Time</th>
                <th>Forced Close Time</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rfqs.map((rfq) => (
                <tr key={rfq.id}>
                  <td className="bold">{rfq.name}</td>
                  <td>{rfq.reference_id}</td>
                  <td>
                    {rfq.lowest_bid != null
                      ? `₹${rfq.lowest_bid.toLocaleString()}`
                      : "No bids yet"}
                  </td>
                  <td>{formatTime(rfq.current_close_time)}</td>
                  <td>{formatTime(rfq.forced_close_time)}</td>
                  <td>
                    <span
                      className="status-badge"
                      style={{
                        backgroundColor: STATUS_COLORS[rfq.status] || "#6b7280",
                      }}
                    >
                      {statusLabel(rfq.status)}
                    </span>
                  </td>
                  <td>
                    <Link to={`/rfq/${rfq.id}`} className="btn-link">
                      View Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default AuctionList;
