import React, { useState, useEffect } from "react";
import type { ReviewItem } from "../types";
import { api } from "../api/client";
import { AlertTriangle, CheckCheck, Eye } from "lucide-react";

interface ReviewQueuePageProps {
  onOpenCase: (caseId: string) => void;
}

export const ReviewQueuePage: React.FC<ReviewQueuePageProps> = ({ onOpenCase }) => {
  const [queue, setQueue] = useState<ReviewItem[]>([]);
  const [reviewedIds, setReviewedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    api.getReviewQueue().then(setQueue).catch(console.error);
  }, []);

  const handleMarkReviewed = (caseId: string) => {
    setReviewedIds((prev) => new Set(prev).add(caseId));
  };

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 0 40px" }}>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "22px", margin: "0 0 6px", fontWeight: 600 }}>Human-in-the-Loop Review Queue</h2>
        <div style={{ fontSize: "13px", color: "var(--muted)" }}>
          Cases flagged due to non-deletion intent, claim-versus-evidence mismatches, or low confidence
        </div>
      </div>

      <div className="card-glass" style={{ padding: 0, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
          <thead>
            <tr style={{ color: "var(--muted)", textAlign: "left", borderBottom: "1px solid var(--border)" }}>
              <th style={{ padding: "12px 18px" }}>Case ID</th>
              <th style={{ padding: "12px 18px" }}>Flag Reason</th>
              <th style={{ padding: "12px 18px" }}>Reported Claim</th>
              <th style={{ padding: "12px 18px" }}>Real Status</th>
              <th style={{ padding: "12px 18px" }}>Confidence</th>
              <th style={{ padding: "12px 18px", textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {queue.map((item) => {
              const isDone = reviewedIds.has(item.case_id);
              return (
                <tr key={item.case_id} style={{ borderBottom: "1px solid var(--border-soft)", opacity: isDone ? 0.4 : 1 }}>
                  <td style={{ padding: "12px 18px", fontWeight: 600 }}>{item.case_id}</td>
                  <td style={{ padding: "12px 18px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <AlertTriangle size={14} color="#f59e0b" />
                      <span>{item.reason}</span>
                    </div>
                  </td>
                  <td style={{ padding: "12px 18px", color: "var(--muted)" }}>{item.reported_status}</td>
                  <td style={{ padding: "12px 18px" }}>
                    <span className={`status-pill ${item.status === "COMPLETE" ? "status-complete" : item.status === "INCOMPLETE" ? "status-incomplete" : "status-na"}`}>
                      {item.status}
                    </span>
                  </td>
                  <td style={{ padding: "12px 18px" }}>{(item.confidence * 100).toFixed(0)}%</td>
                  <td style={{ padding: "12px 18px", textAlign: "right" }}>
                    <div style={{ display: "inline-flex", gap: "8px" }}>
                      <button className="btn-ghost" onClick={() => handleMarkReviewed(item.case_id)} disabled={isDone} style={{ padding: "4px 8px", fontSize: "11px" }}>
                        <CheckCheck size={12} />
                        <span>{isDone ? "Reviewed" : "Mark Done"}</span>
                      </button>
                      <button className="btn-solid" onClick={() => onOpenCase(item.case_id)} style={{ padding: "4px 10px", fontSize: "11px" }}>
                        <Eye size={12} />
                        <span>Open Case</span>
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
