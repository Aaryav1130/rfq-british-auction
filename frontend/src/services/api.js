import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000/api",
});

// ── RFQ endpoints ────────────────────────────────────────────────────────

export function createRFQ(data) {
  return API.post("/rfqs", data);
}

export function fetchRFQs() {
  return API.get("/rfqs");
}

export function fetchRFQDetail(id) {
  return API.get(`/rfqs/${id}`);
}

// ── Bid endpoints ────────────────────────────────────────────────────────

export function submitBid(rfqId, data) {
  return API.post(`/rfqs/${rfqId}/bids`, data);
}
