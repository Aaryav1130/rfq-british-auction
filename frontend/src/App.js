import React from "react";
import { Routes, Route, Link } from "react-router-dom";
import AuctionList from "./components/AuctionList";
import RFQForm from "./components/RFQForm";
import AuctionDetail from "./components/AuctionDetail";

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="logo">
          RFQ Auction System
        </Link>
        <nav>
          <Link to="/">All Auctions</Link>
          <Link to="/create">Create RFQ</Link>
        </nav>
      </header>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<AuctionList />} />
          <Route path="/create" element={<RFQForm />} />
          <Route path="/rfq/:id" element={<AuctionDetail />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
