import React, { useState } from "react";
import type { CaseDetailResponse } from "../types";
import { Copy, RefreshCw, ChevronLeft, ChevronRight, Eye, EyeOff, CheckCircle2 } from "lucide-react";


interface CaseDetailPageProps {
  caseDetail: CaseDetailResponse;
  onReRun: (caseId: string) => void;
  onNavigate: (direction: "prev" | "next") => void;
  onClose?: () => void;
}

const STAGES = ["S0 Profile", "S1 Classify", "S2 Identity", "S4 Match", "S5 State", "S6 Policy", "S7 Compare", "S8 Status", "S9 Plan", "S10 Output"];

export const CaseDetailPage: React.FC<CaseDetailPageProps> = ({ caseDetail, onReRun, onNavigate }) => {
  const [showRaw, setShowRaw] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isReRunning, setIsReRunning] = useState(false);

  const mask = (str: string) => showRaw ? str : str.replace(/(.{2})(.*)(@.*)/, "$1***$3");

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(caseDetail.steps, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleReRun = async () => {
    setIsReRunning(true);
    await onReRun(caseDetail.case_id);
    setIsReRunning(false);
  };

  const isMismatch = caseDetail.reported_status !== caseDetail.status && caseDetail.status !== "NOT_APPLICABLE";

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 0 40px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <h2 style={{ fontSize: "24px", margin: 0, fontWeight: 600 }}>{caseDetail.case_id}</h2>
          <span className={`status-pill status-${caseDetail.status.toLowerCase().replace('_', '')}`}>
            {caseDetail.status}
          </span>
          {isMismatch && (
            <span style={{ fontSize: "11px", padding: "3px 8px", background: "rgba(239,68,68,0.2)", color: "#f87171", border: "1px solid rgba(239,68,68,0.4)", borderRadius: "4px" }}>
              Mismatch: Workflow claimed {caseDetail.reported_status}
            </span>
          )}
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button className="btn-ghost" onClick={() => setShowRaw(!showRaw)} style={{ padding: "6px 12px", fontSize: "12px" }}>
            {showRaw ? <EyeOff size={14} /> : <Eye size={14} />}
            <span>{showRaw ? "Mask PII" : "Reveal PII"}</span>
          </button>
          <button className="btn-solid" onClick={handleCopyJson} style={{ padding: "6px 12px", fontSize: "12px" }}>
            <Copy size={14} />
            <span>{copied ? "Copied JSON" : "Copy Steps JSON"}</span>
          </button>
          <button className="btn-ghost" onClick={handleReRun} disabled={isReRunning} style={{ padding: "6px 12px", fontSize: "12px" }}>
            <RefreshCw size={14} className={isReRunning ? "spin" : ""} />
            <span>{isReRunning ? "Auditing..." : "Re-run Case"}</span>
          </button>
          <button className="btn-ghost" onClick={() => onNavigate("prev")} style={{ padding: "6px 10px" }}><ChevronLeft size={16} /></button>
          <button className="btn-ghost" onClick={() => onNavigate("next")} style={{ padding: "6px 10px" }}><ChevronRight size={16} /></button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px", marginBottom: "20px" }}>
        <div className="card-glass">
          <div style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", marginBottom: "8px" }}>Identity & Request Details</div>
          <div style={{ fontSize: "13px", lineHeight: "1.6", color: "var(--stat)" }}>
            <div>Subject Email: <b>{mask(caseDetail.email)}</b></div>
            <div>Requested At: <b>{new Date(caseDetail.requested_at).toLocaleString()}</b></div>
            <div>Audit Cutoff: <b>{new Date(caseDetail.audit_at).toLocaleString()}</b></div>
            <div style={{ marginTop: "10px", padding: "10px", background: "rgba(0,0,0,0.6)", borderRadius: "6px", border: "1px solid var(--border-soft)", fontSize: "12.5px" }}>
              {caseDetail.request_text}
            </div>
          </div>
        </div>

        <div className="card-glass">
          <div style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", marginBottom: "10px" }}>Stage Verification Gates</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {STAGES.map((st, i) => (
              <div key={st} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px" }}>
                <span>{st}</span>
                {caseDetail.status === "NOT_APPLICABLE" && i > 1 ? (
                  <span style={{ color: "var(--muted)", fontSize: "11px" }}>Bypassed</span>
                ) : (
                  <CheckCircle2 size={14} color="#4ade80" />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card-glass" style={{ padding: 0, overflowX: "auto" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", fontWeight: 600, fontSize: "14px" }}>
          Execution Steps ({caseDetail.steps.length})
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px" }}>
          <thead>
            <tr style={{ background: "rgba(255,255,255,0.02)", color: "var(--muted)", textAlign: "left" }}>
              <th style={{ padding: "10px 14px" }}>#</th>
              <th style={{ padding: "10px 14px" }}>Phase</th>
              <th style={{ padding: "10px 14px" }}>Operation</th>
              <th style={{ padding: "10px 14px" }}>System</th>
              <th style={{ padding: "10px 14px" }}>Resource</th>
              <th style={{ padding: "10px 14px" }}>State</th>
              <th style={{ padding: "10px 14px" }}>Evidence Citation</th>
            </tr>
          </thead>
          <tbody>
            {caseDetail.steps.map((s) => {
              const bg = s.phase === "FINDING" ? "rgba(239,68,68,0.08)" : s.phase === "REMEDIATION" ? "rgba(245,158,11,0.08)" : "rgba(34,197,94,0.08)";
              return (
                <tr key={s.step_no} style={{ borderBottom: "1px solid var(--border-soft)", background: bg }}>
                  <td style={{ padding: "10px 14px", fontWeight: 600 }}>{s.step_no}</td>
                  <td style={{ padding: "10px 14px" }}><b>{s.phase}</b></td>
                  <td style={{ padding: "10px 14px" }}><code>{s.operation}</code></td>
                  <td style={{ padding: "10px 14px" }}>{s.system_id}</td>
                  <td style={{ padding: "10px 14px" }}><code>{s.resource_id}</code></td>
                  <td style={{ padding: "10px 14px" }}><b>{s.state}</b></td>
                  <td style={{ padding: "10px 14px" }}>{s.evidence_id ? <code>{s.evidence_id}</code> : <span style={{ color: "var(--muted)" }}>None (future action)</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
