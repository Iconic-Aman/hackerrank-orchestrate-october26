import React, { useState } from "react";
import type { RunItem, CaseSummary } from "../types";
import { Play, Download, X } from "lucide-react";

import { api } from "../api/client";

interface RunsPageProps {
  runs: RunItem[];
  cases: CaseSummary[];
  onStartRun: (useCache: boolean, selectedIds?: string[]) => void;
  onOpenCase: (caseId: string) => void;
}

export const RunsPage: React.FC<RunsPageProps> = ({ runs, cases, onStartRun, onOpenCase }) => {
  const [selectedRun, setSelectedRun] = useState<RunItem | null>(null);
  const [useCache, setUseCache] = useState(true);
  const [filterStatus, setFilterStatus] = useState("");
  const [search, setSearch] = useState("");
  const [isStarting, setIsStarting] = useState(false);

  const filteredCases = cases.filter((c) => {
    const matchesSearch = !search || c.case_id.toLowerCase().includes(search.toLowerCase()) || c.email.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = !filterStatus || c.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const handleStart = async () => {
    setIsStarting(true);
    await onStartRun(useCache);
    setIsStarting(false);
  };

  return (
    <div style={{ padding: "0 0 40px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "22px", margin: "0 0 6px", fontWeight: 600 }}>Audit Runs</h2>
          <div style={{ fontSize: "13px", color: "var(--muted)" }}>Historical and active batch verification runs across 518 cases</div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <label style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--stat)", cursor: "pointer" }}>
            <input type="checkbox" checked={useCache} onChange={(e) => setUseCache(e.target.checked)} />
            <span>Use Cache (saves tokens)</span>
          </label>
          <button className="btn-solid" onClick={handleStart} disabled={isStarting}>
            <Play size={14} />
            <span>{isStarting ? "Starting..." : "Start New Run"}</span>
          </button>
        </div>
      </div>

      <div className="card-glass" style={{ padding: 0, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--muted)", textAlign: "left" }}>
              <th style={{ padding: "14px 20px" }}>Run ID</th>
              <th style={{ padding: "14px 20px" }}>Dataset Hash</th>
              <th style={{ padding: "14px 20px" }}>Start Time</th>
              <th style={{ padding: "14px 20px" }}>Status</th>
              <th style={{ padding: "14px 20px" }}>Counts (Comp / Incomp / NA)</th>
              <th style={{ padding: "14px 20px", textAlign: "right" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.run_id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                <td style={{ padding: "14px 20px", fontWeight: 600 }}>{r.run_id}</td>
                <td style={{ padding: "14px 20px", color: "var(--stat)" }}><code>{r.dataset_hash}</code></td>
                <td style={{ padding: "14px 20px", color: "var(--muted)" }}>{new Date(r.start_time).toLocaleTimeString()}</td>
                <td style={{ padding: "14px 20px" }}>
                  <span className={`status-pill ${r.status === "COMPLETED" ? "status-complete" : "status-incomplete"}`}>{r.status}</span>
                </td>
                <td style={{ padding: "14px 20px" }}>
                  <span style={{ color: "#4ade80" }}>{r.complete_count}</span> / <span style={{ color: "#f87171" }}>{r.incomplete_count}</span> / <span style={{ color: "#9ca3af" }}>{r.not_applicable_count}</span>
                </td>
                <td style={{ padding: "14px 20px", textAlign: "right" }}>
                  <button className="btn-ghost" onClick={() => setSelectedRun(r)} style={{ padding: "6px 12px", fontSize: "12px" }}>
                    Open Run
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedRun && (
        <div className="modal-backdrop" onClick={() => setSelectedRun(null)}>
          <div className="card-glass" onClick={(e) => e.stopPropagation()} style={{ width: "100%", maxWidth: "860px", maxHeight: "88vh", overflowY: "auto", background: "#0a0a0a" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <h3 style={{ margin: "0 0 4px", fontSize: "18px" }}>{selectedRun.name} ({selectedRun.run_id})</h3>
                <div style={{ fontSize: "12px", color: "var(--muted)" }}>Dataset: <code>{selectedRun.dataset_hash}</code></div>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <a href={api.getExportOutputUrl()} download="output.csv" className="btn-solid" style={{ textDecoration: "none" }}>
                  <Download size={14} />
                  <span>Export output.csv</span>
                </a>
                <button className="btn-ghost" onClick={() => setSelectedRun(null)}><X size={14} /></button>
              </div>
            </div>

            <div style={{ marginBottom: "20px", padding: "14px", background: "rgba(255, 255, 255, 0.03)", borderRadius: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "6px" }}>
                <span>Progress: {cases.length} / {selectedRun.total_cases} cases completed (100%)</span>
                <span style={{ color: "#4ade80" }}>Ready for submission</span>
              </div>
              <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                <div style={{ width: "100%", height: "100%", background: "#4ade80" }} />
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", marginBottom: "16px" }}>
              <input
                type="text"
                placeholder="Filter by case ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ flex: 1, padding: "8px 12px", background: "rgba(20,20,20,0.8)", border: "1px solid var(--border)", borderRadius: "6px", color: "#fff", fontSize: "13px" }}
              />
              {["", "COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"].map((st) => (
                <button key={st} className={`liquid-pill ${filterStatus === st ? "active" : ""}`} onClick={() => setFilterStatus(st)} style={{ fontSize: "12px", height: "34px" }}>
                  {st || "All"}
                </button>
              ))}
            </div>

            <div style={{ maxHeight: "320px", overflowY: "auto", border: "1px solid var(--border-soft)", borderRadius: "6px" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px" }}>
                <thead>
                  <tr style={{ background: "rgba(255,255,255,0.03)", color: "var(--muted)", textAlign: "left" }}>
                    <th style={{ padding: "10px 14px" }}>Case ID</th>
                    <th style={{ padding: "10px 14px" }}>Email</th>
                    <th style={{ padding: "10px 14px" }}>Reported Claim</th>
                    <th style={{ padding: "10px 14px" }}>Real Status</th>
                    <th style={{ padding: "10px 14px", textAlign: "right" }}>Inspect</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCases.slice(0, 50).map((c) => (
                    <tr key={c.case_id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                      <td style={{ padding: "10px 14px", fontWeight: 600 }}>{c.case_id}</td>
                      <td style={{ padding: "10px 14px", color: "var(--stat)" }}>{c.email}</td>
                      <td style={{ padding: "10px 14px", color: "var(--muted)" }}>{c.reported_status}</td>
                      <td style={{ padding: "10px 14px" }}>
                        <span className={`status-pill ${c.status === "COMPLETE" ? "status-complete" : c.status === "INCOMPLETE" ? "status-incomplete" : "status-na"}`}>
                          {c.status || "Pending"}
                        </span>
                      </td>
                      <td style={{ padding: "10px 14px", textAlign: "right" }}>
                        <button className="btn-ghost" onClick={() => onOpenCase(c.case_id)} style={{ padding: "4px 8px", fontSize: "11px" }}>
                          Open
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
