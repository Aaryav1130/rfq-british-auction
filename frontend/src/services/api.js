import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

const API = axios.create({
  baseURL: API_BASE_URL,
});

// RFQ APIs

export function createRFQ(data) {
  return API.post("/rfqs", data);
}

export function fetchRFQs() {
  return API.get("/rfqs");
}

export function fetchRFQDetail(id) {
  return API.get(`/rfqs/${id}`);
}

// Bid APIs

export function submitBid(rfqId, data) {
  return API.post(`/rfqs/${rfqId}/bids`, data);
}
