import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createRFQ } from "../services/api";

const TRIGGER_OPTIONS = [
  { value: "bid_received", label: "Any bid received in trigger window" },
  { value: "any_rank_change", label: "Any supplier rank change in trigger window" },
  { value: "l1_rank_change", label: "Lowest bidder (L1) change in trigger window" },
];

function RFQForm() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    name: "",
    reference_id: "",
    bid_start_time: "",
    bid_close_time: "",
    forced_close_time: "",
    pickup_date: "",
    trigger_window_minutes: 10,
    extension_duration_minutes: 5,
    trigger_type: "bid_received",
  });

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    // basic client-side check
    if (new Date(form.forced_close_time) <= new Date(form.bid_close_time)) {
      setError("Forced close time must be later than bid close time.");
      return;
    }

    setSubmitting(true);
    try {
      // convert datetime-local strings to ISO format
      const payload = {
        ...form,
        trigger_window_minutes: Number(form.trigger_window_minutes),
        extension_duration_minutes: Number(form.extension_duration_minutes),
        bid_start_time: new Date(form.bid_start_time).toISOString(),
        bid_close_time: new Date(form.bid_close_time).toISOString(),
        forced_close_time: new Date(form.forced_close_time).toISOString(),
        pickup_date: new Date(form.pickup_date).toISOString(),
      };
      await createRFQ(payload);
      navigate("/");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to create RFQ.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="form-container">
      <h2>Create New RFQ</h2>
      <p className="form-subtitle">Set up a British Auction for supplier bidding</p>

      {error && <div className="error-box">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-section">
          <h3>Basic Details</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>RFQ Name</label>
              <input
                name="name"
                value={form.name}
                onChange={handleChange}
                placeholder="e.g. Mumbai-Delhi Freight Q4"
                required
              />
            </div>
            <div className="form-group">
              <label>Reference ID</label>
              <input
                name="reference_id"
                value={form.reference_id}
                onChange={handleChange}
                placeholder="e.g. RFQ-2024-001"
                required
              />
            </div>
          </div>
        </div>

        <div className="form-section">
          <h3>Schedule</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Bid Start Time</label>
              <input
                type="datetime-local"
                name="bid_start_time"
                value={form.bid_start_time}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Bid Close Time</label>
              <input
                type="datetime-local"
                name="bid_close_time"
                value={form.bid_close_time}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Forced Bid Close Time</label>
              <input
                type="datetime-local"
                name="forced_close_time"
                value={form.forced_close_time}
                onChange={handleChange}
                required
              />
              <span className="hint">Must be after bid close time</span>
            </div>
            <div className="form-group">
              <label>Pickup / Service Date</label>
              <input
                type="datetime-local"
                name="pickup_date"
                value={form.pickup_date}
                onChange={handleChange}
                required
              />
            </div>
          </div>
        </div>

        <div className="form-section">
          <h3>British Auction Configuration</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Trigger Window (X minutes)</label>
              <input
                type="number"
                name="trigger_window_minutes"
                value={form.trigger_window_minutes}
                onChange={handleChange}
                min="1"
                required
              />
              <span className="hint">
                Monitor bidding activity in the last X minutes before close
              </span>
            </div>
            <div className="form-group">
              <label>Extension Duration (Y minutes)</label>
              <input
                type="number"
                name="extension_duration_minutes"
                value={form.extension_duration_minutes}
                onChange={handleChange}
                min="1"
                required
              />
              <span className="hint">
                Add Y minutes when a trigger condition is met
              </span>
            </div>
            <div className="form-group full-width">
              <label>Extension Trigger</label>
              <select
                name="trigger_type"
                value={form.trigger_type}
                onChange={handleChange}
              >
                {TRIGGER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Creating..." : "Create RFQ"}
        </button>
      </form>
    </div>
  );
}

export default RFQForm;
