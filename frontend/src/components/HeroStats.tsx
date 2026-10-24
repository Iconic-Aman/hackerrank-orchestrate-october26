import React from "react";
import type { StatsResponse } from "../types";

interface HeroStatsProps {
  stats: StatsResponse | null;
  onRunBatch: () => void;
  isRunningBatch: boolean;
}

export const HeroStats: React.FC<HeroStatsProps> = ({ stats, onRunBatch, isRunningBatch }) => {
  return (
    <section style={{ padding: "48px 32px 32px", maxWidth: "1200px", margin: "0 auto" }}>
      <div style={{ textAlign: "center", marginBottom: "36px" }}>
        <div style={{ display: "inline-block", marginBottom: "16px" }}>
          <div className="badge-vesper">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="white">
              <path d="M12 2.6C12.55 2.6 12.88 3.15 13.08 4.7c.62 4.7 1.52 5.6 6.22 6.22 1.55.2 2.1.53 2.1 1.08s-.55.88-2.1 1.08c-4.7.62-5.6 1.52-6.22 6.22-.2 1.55-.53 2.1-1.08 2.1s-.88-.55-1.08-2.1c-.62-4.7-1.52-5.6-6.22-6.22C3.15 12.88 2.6 12.55 2.6 12s.55-.88 2.1-1.08c4.7-.62 5.6-1.52 6.22-6.22C11.12 3.15 11.45 2.6 12 2.6Z" />
            </svg>
            <span>Operational Deletion-Audit Engine</span>
          </div>
        </div>

        <h1 style={{
          fontSize: "42px",
          fontWeight: 500,
          letterSpacing: "-0.04em",
          lineHeight: 1.15,
          margin: "0 0 14px",
        }}>
          Audit <em style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", color: "var(--muted)" }}>ghost data</em> across platforms.
        </h1>
        <p style={{
          fontSize: "15px",
          color: "var(--muted)",
          maxWidth: "540px",
          margin: "0 auto 24px",
          lineHeight: 1.5,
        }}>
          Reconstruct historical identifiers and verify deletion cutoff states across replicas, backups, and logs.
        </p>

        <button className="btn-solid" onClick={onRunBatch} disabled={isRunningBatch}>
          <span>{isRunningBatch ? "Executing 518 Audits..." : "Run Global Audit Engine"}</span>
        </button>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
        gap: "16px",
      }}>
        <div className="card-glass">
          <div style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
            Total Audit Scope
          </div>
          <div style={{ fontSize: "32px", fontWeight: 600 }}>{stats ? stats.total_cases : "518"}</div>
          <div style={{ fontSize: "13px", color: "var(--stat)", marginTop: "4px" }}>Active deletion requests analyzed</div>
        </div>

        <div className="card-glass">
          <div style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
            Compliance Verdicts
          </div>
          <div style={{ display: "flex", gap: "12px", alignItems: "baseline" }}>
            <span style={{ fontSize: "24px", fontWeight: 600, color: "#4ade80" }}>{stats?.complete_count ?? 0}</span>
            <span style={{ fontSize: "12px", color: "var(--muted)" }}>Complete</span>
            <span style={{ fontSize: "24px", fontWeight: 600, color: "#f87171", marginLeft: "12px" }}>{stats?.incomplete_count ?? 0}</span>
            <span style={{ fontSize: "12px", color: "var(--muted)" }}>Incomplete</span>
          </div>
          <div style={{ fontSize: "13px", color: "var(--stat)", marginTop: "4px" }}>
            {stats ? `${stats.not_applicable_count} Non-deletion filtered` : "Evaluating..."}
          </div>
        </div>

        <div className="card-glass">
          <div style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
            Policy Findings
          </div>
          <div style={{ fontSize: "32px", fontWeight: 600 }}>
            {stats ? Object.values(stats.findings_by_operation).reduce((a, b) => a + b, 0) : 0}
          </div>
          <div style={{ fontSize: "13px", color: "var(--stat)", marginTop: "4px" }}>
            Remaining copies, sync flows & restore risks
          </div>
        </div>
      </div>
    </section>
  );
};
