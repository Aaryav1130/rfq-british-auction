# High-Level Design — RFQ British Auction System

## 1. System Overview

A web application that allows buyers to create RFQs (Request for Quotation) with British Auction–style bidding. Suppliers compete by submitting bids, and the auction clock auto-extends when activity occurs near the closing time — encouraging fair competition and preventing last-second sniping.

## 2. Architecture

```
┌─────────────────────────────┐
│        React Frontend       │
│   (Single Page Application) │
│                             │
│  - RFQ Creation Form        │
│  - Auction Listing Page     │
│  - Auction Detail Page      │
│  - Bid Submission Form      │
│  - Activity Log Display     │
└────────────┬────────────────┘
             │  HTTP / REST (JSON)
             │  Port 3000 → 8000
             ▼
┌─────────────────────────────┐
│     FastAPI Backend         │
│                             │
│  Routes:                    │
│  POST /api/rfqs             │
│  GET  /api/rfqs             │
│  GET  /api/rfqs/{id}        │
│  POST /api/rfqs/{id}/bids   │
│                             │
│  Services:                  │
│  - Auction Engine           │
│    (extension logic,        │
│     ranking, status mgmt)   │
└────────────┬────────────────┘
             │  SQLAlchemy ORM
             ▼
┌─────────────────────────────┐
│       PostgreSQL            │
│                             │
│  Tables:                    │
│  - rfqs                     │
│  - bids                     │
│  - activity_logs            │
└─────────────────────────────┘
```

## 3. Data Flow

### Creating an RFQ
1. Buyer fills the RFQ form with auction configuration (X, Y, trigger type)
2. Frontend sends `POST /api/rfqs` with all fields
3. Backend validates (forced close > bid close, positive minutes)
4. RFQ saved to DB with `current_close_time = bid_close_time`
5. Activity log entry: "RFQ created"

### Submitting a Bid
1. Supplier fills bid form (carrier name, charges, transit time, validity)
2. Frontend sends `POST /api/rfqs/{id}/bids`
3. Backend validates (auction is active, bidding period has started)
4. Bid saved, `total_price` calculated as freight + origin + destination
5. **Auction Engine runs:**
   - Captures old rankings / old L1 bidder
   - Recalculates all rankings (sort by total_price ascending)
   - Checks if current time falls within the trigger window
   - If yes → evaluates the configured trigger condition
   - If condition met → extends `current_close_time` by Y minutes (capped at forced_close_time)
   - Logs all events (bid submission + any extension with reason)

### Viewing Auction Status
1. List endpoint returns all RFQs with current lowest bid and live status
2. Detail endpoint returns full bids table (ranked), config, and activity log
3. Status auto-updates on each request (lazy evaluation instead of background jobs)

## 4. Database Schema

### rfqs
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| name | VARCHAR(255) | RFQ title |
| reference_id | VARCHAR(100) UNIQUE | e.g. RFQ-2024-001 |
| bid_start_time | TIMESTAMPTZ | When bidding opens |
| bid_close_time | TIMESTAMPTZ | Original close time |
| current_close_time | TIMESTAMPTZ | May be extended |
| forced_close_time | TIMESTAMPTZ | Hard stop, never exceeded |
| pickup_date | TIMESTAMPTZ | Service / pickup date |
| trigger_window_minutes | INT | X — monitoring window |
| extension_duration_minutes | INT | Y — extension amount |
| trigger_type | ENUM | bid_received / any_rank_change / l1_rank_change |
| status | ENUM | active / closed / force_closed |
| created_at | TIMESTAMPTZ | Record creation time |

### bids
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| rfq_id | INT FK → rfqs.id | |
| carrier_name | VARCHAR(255) | Supplier name |
| freight_charges | FLOAT | |
| origin_charges | FLOAT | |
| destination_charges | FLOAT | |
| total_price | FLOAT | Sum of three charges |
| transit_time | VARCHAR(100) | e.g. "3-5 days" |
| validity | VARCHAR(100) | e.g. "7 days" |
| submitted_at | TIMESTAMPTZ | |
| rank | INT | L1 = 1, L2 = 2, ... |

### activity_logs
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| rfq_id | INT FK → rfqs.id | |
| event_type | VARCHAR(50) | bid_submitted / time_extended / ... |
| description | TEXT | Human-readable log message |
| timestamp | TIMESTAMPTZ | |
| bid_id | INT FK → bids.id | Nullable, links to triggering bid |

## 5. British Auction Extension Logic

```
on_bid_received(rfq, new_bid):
    window_start = current_close_time - X minutes
    
    if NOW not in [window_start, current_close_time]:
        return   # outside trigger window, skip

    if trigger_type == "bid_received":
        extend = True

    elif trigger_type == "any_rank_change":
        extend = (rankings shifted after adding new_bid)

    elif trigger_type == "l1_rank_change":
        extend = (lowest bidder changed)

    if extend:
        new_close = current_close_time + Y minutes
        new_close = min(new_close, forced_close_time)   # hard cap
        rfq.current_close_time = new_close
        log("time_extended", reason)
```

## 6. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rfqs` | Create a new RFQ with auction config |
| GET | `/api/rfqs` | List all RFQs (with lowest bid, status) |
| GET | `/api/rfqs/{id}` | Full auction detail (bids, rankings, log) |
| POST | `/api/rfqs/{id}/bids` | Submit a bid (triggers auction engine) |

## 7. Key Design Decisions

1. **No background scheduler** — auction status is lazily evaluated on each request. This keeps the system simple and avoids needing Celery/Redis for the assignment scope.

2. **`current_close_time` separate from `bid_close_time`** — preserves the original deadline while tracking extensions independently.

3. **Ranking recalculated on each bid** — simple and correct for the expected data volume.

4. **Activity log captures everything** — provides full audit trail of bid submissions, extensions, and closures with human-readable reasons.
