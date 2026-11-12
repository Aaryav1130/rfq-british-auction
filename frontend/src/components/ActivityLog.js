import React from "react";

const EVENT_ICONS = {
  rfq_created: "📋",
  bid_submitted: "💰",
  time_extended: "⏰",
  auction_closed: "🔒",
  auction_force_closed: "🛑",
};

function ActivityLog({ logs }) {
  function formatTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString();
  }

  function eventLabel(type) {
    return type
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }

  return (
    <div className="section">
      <h3>Activity Log</h3>
      {logs.length === 0 ? (
        <p className="muted">No activity recorded yet.</p>
      ) : (
        <div className="activity-log">
          {logs.map((log) => (
            <div key={log.id} className={`log-entry log-${log.event_type}`}>
              <div className="log-icon">
                {EVENT_ICONS[log.event_type] || "📌"}
              </div>
              <div className="log-content">
                <div className="log-header">
                  <span className="log-type">{eventLabel(log.event_type)}</span>
                  <span className="log-time">{formatTime(log.timestamp)}</span>
                </div>
                <p className="log-desc">{log.description}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ActivityLog;
