import React from "react";
import type { CaseSummary } from "../types";
import { Eye, Play } from "lucide-react";

interface CaseTableProps {
  cases: CaseSummary[];
  loading: boolean;
  onSelectCase: (caseId: string) => void;
  onAuditCase: (caseId: string) => void;
}

export const CaseTable: React.FC<CaseTableProps> = ({ cases, loading, onSelectCase, onAuditCase }) => {
  const getBadgeClass = (status: string | null) => {
    if (status === "COMPLETE") return "status-pill status-complete";
    if (status === "INCOMPLETE") return "status-pill status-incomplete";
    if (status === "NOT_APPLICABLE") return "status-pill status-na";
    return "status-pill";
  };

  if (loading) {
    return (
      <div className="card-glass" style={{ textAlign: "center", padding: "40px", color: "var(--muted)" }}>
        Loading audit records...
      </div>
    );
  }

  if (cases.length === 0) {
    return (
      <div className="card-glass" style={{ textAlign: "center", padding: "40px", color: "var(--muted)" }}>
        No cases found matching filters.
      </div>
    );
  }

  return (
    <div className="card-glass" style={{ overflowX: "auto", padding: "0" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13.5px" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--muted)", textAlign: "left" }}>
            <th style={{ padding: "14px 20px" }}>Case ID</th>
            <th style={{ padding: "14px 20px" }}>Email</th>
            <th style={{ padding: "14px 20px" }}>Audit Cutoff</th>
            <th style={{ padding: "14px 20px" }}>Workflow Claim</th>
            <th style={{ padding: "14px 20px" }}>Audit Verdict</th>
            <th style={{ padding: "14px 20px", textAlign: "right" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.case_id} style={{ borderBottom: "1px solid var(--border-soft)", transition: "background 0.2s" }}>
              <td style={{ padding: "14px 20px", fontWeight: 600 }}>{c.case_id}</td>
              <td style={{ padding: "14px 20px", color: "var(--stat)" }}>{c.email}</td>
              <td style={{ padding: "14px 20px", color: "var(--muted)", fontSize: "12px" }}>
                {new Date(c.audit_at).toLocaleDateString()}
              </td>
              <td style={{ padding: "14px 20px", fontSize: "12px", color: "var(--muted)" }}>
                {c.reported_status}
              </td>
              <td style={{ padding: "14px 20px" }}>
                <span className={getBadgeClass(c.status)}>
                  {c.status || "Pending"}
                </span>
              </td>
              <td style={{ padding: "14px 20px", textAlign: "right" }}>
                <div style={{ display: "inline-flex", gap: "8px" }}>
                  <button
                    className="liquid-pill"
                    style={{ height: "30px", padding: "0 10px", fontSize: "12px" }}
                    onClick={() => onAuditCase(c.case_id)}
                    title="Run Audit Engine on case"
                  >
                    <Play size={12} />
                    <span>Audit</span>
                  </button>
                  <button
                    className="btn-solid"
                    style={{ height: "30px", padding: "0 10px", fontSize: "12px" }}
                    onClick={() => onSelectCase(c.case_id)}
                  >
                    <Eye size={12} />
                    <span>Inspect</span>
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
