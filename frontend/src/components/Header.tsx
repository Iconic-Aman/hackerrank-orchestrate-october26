import React from "react";
import { Settings, RefreshCw } from "lucide-react";

interface HeaderProps {
  onOpenSettings: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onOpenSettings, onRefresh, isRefreshing }) => {
  return (
    <header style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "20px 32px",
      borderBottom: "1px solid var(--border-soft)",
      backdropFilter: "blur(12px)",
      position: "sticky",
      top: 0,
      zIndex: 50,
      background: "rgba(0, 0, 0, 0.8)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="white">
          <g transform="rotate(-30 12 12)">
            <circle cx="7.3" cy="3.2" r="1.45" />
            <rect x="5.5" y="4.7" width="3.6" height="14.6" rx="1.8" />
            <rect x="14.9" y="4.7" width="3.6" height="14.6" rx="1.8" />
            <circle cx="16.7" cy="20.8" r="1.45" />
          </g>
        </svg>
        <span style={{ fontSize: "16px", fontWeight: 600, letterSpacing: "-0.02em" }}>
          GhostData<span style={{ fontWeight: 400, color: "var(--muted)" }}>.audit</span>
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <button
          className="liquid-pill"
          onClick={onRefresh}
          disabled={isRefreshing}
          style={{ cursor: isRefreshing ? "wait" : "pointer" }}
        >
          <RefreshCw size={14} className={isRefreshing ? "spin" : ""} />
          <span>{isRefreshing ? "Auditing..." : "Sync"}</span>
        </button>

        <button className="btn-ghost" onClick={onOpenSettings}>
          <Settings size={15} />
          <span>API Key</span>
        </button>
      </div>
    </header>
  );
};
