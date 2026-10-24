import React from "react";
import type { CaseDetailResponse } from "../types";
import { X, AlertTriangle, Wrench, CheckCircle } from "lucide-react";

interface CaseDrawerProps {
  caseDetail: CaseDetailResponse | null;
  loading: boolean;
  onClose: () => void;
}

export const CaseDrawer: React.FC<CaseDrawerProps> = ({ caseDetail, loading, onClose }) => {
  if (!caseDetail && !loading) return null;

  const getPhaseIcon = (phase: string) => {
    if (phase === "FINDING") return <AlertTriangle size={15} color="#f87171" />;
    if (phase === "REMEDIATION") return <Wrench size={15} color="#fbbf24" />;
    return <CheckCircle size={15} color="#4ade80" />;
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="card-glass"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: "760px",
          maxHeight: "88vh",
          overflowY: "auto",
          position: "relative",
          background: "#080808",
          border: "1px solid rgba(255, 255, 255, 0.2)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <div>
            <h2 style={{ fontSize: "20px", margin: "0 0 4px" }}>
              {caseDetail ? caseDetail.case_id : "Loading Case..."}
            </h2>
            <div style={{ fontSize: "13px", color: "var(--stat)" }}>{caseDetail?.email}</div>
          </div>
          <button className="btn-ghost" onClick={onClose} style={{ padding: "6px 10px" }}>
            <X size={16} />
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "40px", color: "var(--muted)" }}>
            Running point-in-time audit evaluation...
          </div>
        ) : caseDetail ? (
          <div>
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "12px",
              marginBottom: "20px",
              padding: "14px",
              background: "rgba(255, 255, 255, 0.03)",
              borderRadius: "8px",
            }}>
              <div>
                <span style={{ fontSize: "11px", color: "var(--muted)" }}>Audit Cutoff</span>
                <div style={{ fontSize: "13px", fontWeight: 500 }}>{new Date(caseDetail.audit_at).toLocaleString()}</div>
              </div>
              <div>
                <span style={{ fontSize: "11px", color: "var(--muted)" }}>Workflow Claim</span>
                <div style={{ fontSize: "13px", fontWeight: 500 }}>{caseDetail.reported_status}</div>
              </div>
              <div>
                <span style={{ fontSize: "11px", color: "var(--muted)" }}>True Audit Verdict</span>
                <div>
                  <span className={`status-pill status-${caseDetail.status.toLowerCase().replace('_', '')}`}>
                    {caseDetail.status}
                  </span>
                </div>
              </div>
            </div>

            <div style={{ marginBottom: "20px" }}>
              <div style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", marginBottom: "6px" }}>
                Request Text
              </div>
              <div style={{
                fontSize: "13px",
                lineHeight: "1.5",
                padding: "12px",
                background: "rgba(0, 0, 0, 0.6)",
                border: "1px solid var(--border-soft)",
                borderRadius: "6px",
                color: "#e5e5e5",
              }}>
                {caseDetail.request_text}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", marginBottom: "12px" }}>
                Audit Pipeline Steps ({caseDetail.steps.length})
              </div>

              {caseDetail.steps.length === 0 ? (
                <div style={{ fontSize: "13px", color: "var(--muted)", fontStyle: "italic" }}>
                  No execution steps (Non-deletion request or verified immediate absence).
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {caseDetail.steps.map((s) => (
                    <div
                      key={s.step_no}
                      style={{
                        padding: "12px 14px",
                        background: "rgba(20, 20, 20, 0.6)",
                        border: "1px solid var(--border-soft)",
                        borderRadius: "6px",
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "12px",
                      }}
                    >
                      <div style={{ marginTop: "2px" }}>{getPhaseIcon(s.phase)}</div>
                      <div style={{ flex: 1, fontSize: "13px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                          <span style={{ fontWeight: 600 }}>
                            Step {s.step_no}: {s.operation}
                          </span>
                          <span style={{ fontSize: "11px", color: "var(--muted)" }}>{s.phase}</span>
                        </div>
                        <div style={{ color: "var(--stat)", fontSize: "12px" }}>
                          Resource: <code>{s.resource_id}</code> | System: <code>{s.system_id}</code> | State: <b>{s.state}</b>
                        </div>
                        {s.evidence_id && (
                          <div style={{ marginTop: "4px", fontSize: "11px", color: "#60a5fa" }}>
                            Evidence cited: <code>{s.evidence_id}</code>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
