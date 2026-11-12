# RFQ British Auction System

A simplified RFQ (Request for Quotation) system with British Auction–style bidding, built with **FastAPI**, **ReactJS**, and **PostgreSQL**.

Suppliers compete by submitting bids on RFQs. If bidding activity occurs near the auction close time, the deadline automatically extends — preventing last-second sniping and encouraging fair competition.

---

## 🌐 Live Demo & Deployment

- **Live Web Application:** [https://rfq-british-frontend.onrender.com](https://rfq-british-frontend.onrender.com)
- **Backend API & Swagger Docs:** [https://rfq-auction-backend.onrender.com/docs](https://rfq-auction-backend.onrender.com/docs)

---

## Features

- **Create RFQs** with configurable British Auction settings (trigger window, extension duration, trigger type)
- **Submit bids** with freight, origin, and destination charges
- **Auto-extending auctions** — clock extends when activity is detected in the trigger window
- **Forced close** — hard deadline that can never be exceeded
- **Live rankings** — suppliers ranked L1, L2, L3… by total price
- **Activity log** — full audit trail of bids, extensions, and closure events
- **Auction listing** — overview of all RFQs with status and current lowest bid

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, FastAPI, SQLAlchemy |
| Database | PostgreSQL |
| Frontend | React 18, React Router, Axios |
| Styling | Plain CSS |

---

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── database.py              # DB connection setup
│   ├── models.py                # SQLAlchemy ORM models
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── routes/
│   │   ├── rfq.py               # RFQ CRUD endpoints
│   │   └── bid.py               # Bid submission + auction logic
│   ├── services/
│   │   └── auction.py           # British Auction extension engine
│   ├── requirements.txt
│   └── .env.example             # Template for local environment vars
├── frontend/
│   ├── public/index.html
│   ├── src/
│   │   ├── App.js               # Root component with routing
│   │   ├── App.css              # All styles
│   │   ├── components/
│   │   │   ├── RFQForm.js       # Create RFQ form
│   │   │   ├── AuctionList.js   # Auction listing page
│   │   │   ├── AuctionDetail.js # Detail page (bids + log)
│   │   │   ├── BidForm.js       # Bid submission form
│   │   │   └── ActivityLog.js   # Activity log component
│   │   └── services/
│   │       └── api.js           # Axios API calls
│   └── package.json
├── docs/
│   └── HLD.md                   # High-level design document
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm
- PostgreSQL running locally

### 1. Database Setup

Create the database in PostgreSQL:

```sql
CREATE DATABASE rfq_auction;
```

Copy `.env.example` to `.env` and set your PostgreSQL connection string:

```bash
# inside backend/
cp .env.example .env    # On Windows: copy .env.example .env
```

```
DATABASE_URL=postgresql+psycopg2://postgres:yourpassword@localhost:5432/rfq_auction
```

### 2. Backend Setup

```bash
cd backend

# create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# install dependencies
pip install -r requirements.txt

# start the server
uvicorn main:app --reload --port 8000

# run automated tests
pytest --rootdir=. tests/test_auction.py
```

The API will be available at `http://localhost:8000`. You can check the auto-generated docs at `http://localhost:8000/docs`.

### 3. Frontend Setup

```bash
cd frontend

npm install
npm start
```

The React app will open at `http://localhost:3000`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/rfqs` | Create a new RFQ |
| `GET` | `/api/rfqs` | List all RFQs |
| `GET` | `/api/rfqs/{id}` | Get auction detail (bids, rankings, log) |
| `POST` | `/api/rfqs/{id}/bids` | Submit a bid |

---

## How the British Auction Works

1. **Trigger Window (X minutes):** The system monitors bidding in the last X minutes before the auction closes.

2. **Extension Duration (Y minutes):** When a trigger fires, the close time extends by Y minutes.

3. **Trigger Types:**
   - *Bid Received* — any bid in the window extends the clock
   - *Any Rank Change* — extension only when supplier rankings change
   - *L1 Rank Change* — extension only when the lowest bidder changes

4. **Forced Close:** The auction can never extend beyond the forced close time, no matter how many triggers fire.

---

## Design Decisions

- **No background workers** — status updates happen lazily on each API call (keeps things simple, no need for Celery/Redis).
- **Separate `current_close_time`** — the original close time is preserved; only the current close time gets extended.
- **Rankings recalculated per bid** — works well for the expected data volume and keeps logic straightforward.
