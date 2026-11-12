import React, { useState } from "react";
import { submitBid } from "../services/api";

function BidForm({ rfqId, onBidSubmitted }) {
  const [form, setForm] = useState({
    carrier_name: "",
    freight_charges: "",
    origin_charges: "",
    destination_charges: "",
    transit_time: "",
    validity: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSubmitting(true);

    try {
      const payload = {
        carrier_name: form.carrier_name,
        freight_charges: parseFloat(form.freight_charges),
        origin_charges: parseFloat(form.origin_charges),
        destination_charges: parseFloat(form.destination_charges),
        transit_time: form.transit_time,
        validity: form.validity,
      };
      const res = await submitBid(rfqId, payload);
      setSuccess(
        `Bid submitted! Total: ₹${res.data.total_price.toLocaleString()} — Rank: L${res.data.rank}`
      );
      // clear the form for another bid
      setForm({
        carrier_name: "",
        freight_charges: "",
        origin_charges: "",
        destination_charges: "",
        transit_time: "",
        validity: "",
      });
      // refresh the parent to show updated bids and log
      if (onBidSubmitted) onBidSubmitted();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to submit bid.");
    } finally {
      setSubmitting(false);
    }
  }

  const total =
    (parseFloat(form.freight_charges) || 0) +
    (parseFloat(form.origin_charges) || 0) +
    (parseFloat(form.destination_charges) || 0);

  return (
    <div className="section bid-form-section">
      <h3>Submit a Bid</h3>

      {error && <div className="error-box">{error}</div>}
      {success && <div className="success-box">{success}</div>}

      <form onSubmit={handleSubmit} className="bid-form">
        <div className="form-grid">
          <div className="form-group">
            <label>Carrier Name</label>
            <input
              name="carrier_name"
              value={form.carrier_name}
              onChange={handleChange}
              placeholder="e.g. BlueDart Logistics"
              required
            />
          </div>
          <div className="form-group">
            <label>Freight Charges (₹)</label>
            <input
              type="number"
              name="freight_charges"
              value={form.freight_charges}
              onChange={handleChange}
              placeholder="0.00"
              min="0"
              step="0.01"
              required
            />
          </div>
          <div className="form-group">
            <label>Origin Charges (₹)</label>
            <input
              type="number"
              name="origin_charges"
              value={form.origin_charges}
              onChange={handleChange}
              placeholder="0.00"
              min="0"
              step="0.01"
              required
            />
          </div>
          <div className="form-group">
            <label>Destination Charges (₹)</label>
            <input
              type="number"
              name="destination_charges"
              value={form.destination_charges}
              onChange={handleChange}
              placeholder="0.00"
              min="0"
              step="0.01"
              required
            />
          </div>
          <div className="form-group">
            <label>Transit Time</label>
            <input
              name="transit_time"
              value={form.transit_time}
              onChange={handleChange}
              placeholder="e.g. 3-5 days"
              required
            />
          </div>
          <div className="form-group">
            <label>Validity of Quote</label>
            <input
              name="validity"
              value={form.validity}
              onChange={handleChange}
              placeholder="e.g. 7 days"
              required
            />
          </div>
        </div>

        <div className="bid-total">
          Calculated Total: <strong>₹{total.toLocaleString()}</strong>
        </div>

        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Submitting..." : "Submit Bid"}
        </button>
      </form>
    </div>
  );
}

export default BidForm;
