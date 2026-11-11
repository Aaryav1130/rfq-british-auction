from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routes import rfq, bid


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="RFQ British Auction System",
    description="Simplified RFQ system with British Auction-style bidding",
    version="1.0.0",
    lifespan=lifespan,
)

# allow the React dev server to talk to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rfq.router)
app.include_router(bid.router)


@app.get("/")
def root():
    return {"message": "RFQ British Auction API is running"}
