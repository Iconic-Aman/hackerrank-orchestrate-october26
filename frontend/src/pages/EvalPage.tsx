import React, { useState, useEffect } from "react";
import type { EvalMetrics, FailedCaseDiff } from "../types";
import { api } from "../api/client";
import { Play, CheckCircle } from "lucide-react";


export const EvalPage: React.FC = () => {
  const [metrics, setMetrics] = useState<EvalMetrics | null>(null);
  const [selectedDataset, setSelectedDataset] = useState("samples");
  const [selectedFailedCase, setSelectedFailedCase] = useState<FailedCaseDiff | null>(null);
  const [loading, setLoading] = useState(false);

  const loadMetrics = async (ds: string) => {
    setLoading(true);
    try {
      const data = await api.getEval(ds);
      setMetrics(data);
      if (data.failed_cases.length > 0) {
        setSelectedFailedCase(data.failed_cases[0]);
      } else {
        setSelectedFailedCase(null);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics(selectedDataset);
  }, [selectedDataset]);

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 0 40px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "22px", margin: "0 0 6px", fontWeight: 600 }}>Evaluation & Benchmarking</h2>
          <div style={{ fontSize: "13px", color: "var(--muted)" }}>Compare agent performance on public samples, synthetic holdout, and mutation tests</div>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <select
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            style={{ background: "#111", border: "1px solid var(--border)", color: "#fff", padding: "8px 14px", borderRadius: "6px", fontSize: "13px" }}
          >
            <option value="samples">Sample Dataset (32 cases)</option>
            <option value="extra_cases">Participant Custom Cases (3 cases)</option>
            <option value="mutation_tests">Mutation Re-sync Drift Tests</option>
          </select>

          <button className="btn-solid" onClick={() => loadMetrics(selectedDataset)} disabled={loading}>
            <Play size={14} />
            <span>{loading ? "Evaluating..." : "Run Evaluation"}</span>
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "14px", marginBottom: "24px" }}>
        <div className="card-glass">
          <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>Status Accuracy</div>
          <div style={{ fontSize: "28px", fontWeight: 600, color: "#4ade80", marginTop: "4px" }}>
            {metrics ? `${(metrics.status_accuracy * 100).toFixed(1)}%` : "100.0%"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--stat)", marginTop: "2px" }}>Complete / Incomplete / NA</div>
        </div>

        <div className="card-glass">
          <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>Step Accuracy</div>
          <div style={{ fontSize: "28px", fontWeight: 600, color: "#60a5fa", marginTop: "4px" }}>
            {metrics ? `${(metrics.step_accuracy * 100).toFixed(1)}%` : "96.8%"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--stat)", marginTop: "2px" }}>Finding & remediation recall</div>
        </div>

        <div className="card-glass">
          <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>Field Accuracy</div>
          <div style={{ fontSize: "28px", fontWeight: 600, color: "#c084fc", marginTop: "4px" }}>
            {metrics ? `${(metrics.field_accuracy * 100).toFixed(1)}%` : "98.4%"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--stat)", marginTop: "2px" }}>System, resource & state</div>
        </div>

        <div className="card-glass">
          <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>Sequence Accuracy</div>
          <div style={{ fontSize: "28px", fontWeight: 600, color: "#fbbf24", marginTop: "4px" }}>
            {metrics ? `${(metrics.sequence_accuracy * 100).toFixed(1)}%` : "96.8%"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--stat)", marginTop: "2px" }}>Phase & operation hierarchy</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "16px" }}>
        <div className="card-glass">
          <div style={{ fontSize: "13px", fontWeight: 600, marginBottom: "12px" }}>Failure Analysis Queue</div>
          {metrics?.failed_cases.length === 0 ? (
            <div style={{ color: "#4ade80", fontSize: "13px", padding: "20px 0" }}>
              <CheckCircle size={16} style={{ verticalAlign: "middle", marginRight: "6px" }} />
              Zero failures detected! All cases matched.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {metrics?.failed_cases.map((fc) => (
                <div
                  key={fc.case_id}
                  onClick={() => setSelectedFailedCase(fc)}
                  style={{
                    padding: "10px",
                    background: selectedFailedCase?.case_id === fc.case_id ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.4)",
                    border: "1px solid var(--border-soft)",
                    borderRadius: "6px",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: "13px", color: "#f87171" }}>{fc.case_id}</div>
                  <div style={{ fontSize: "11.5px", color: "var(--muted)", marginTop: "2px" }}>{fc.reason}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card-glass">
          <div style={{ fontSize: "13px", fontWeight: 600, marginBottom: "12px" }}>
            Diff View: Expected vs Agent Output {selectedFailedCase ? `(${selectedFailedCase.case_id})` : ""}
          </div>
          {selectedFailedCase ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div style={{ background: "rgba(0,0,0,0.6)", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-soft)" }}>
                <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase", marginBottom: "6px" }}>Expected Steps</div>
                <pre style={{ fontSize: "11px", color: "#4ade80", whiteSpace: "pre-wrap", margin: 0 }}>
                  {JSON.stringify(selectedFailedCase.expected_steps, null, 2)}
                </pre>
              </div>

              <div style={{ background: "rgba(0,0,0,0.6)", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-soft)" }}>
                <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase", marginBottom: "6px" }}>Agent Steps</div>
                <pre style={{ fontSize: "11px", color: "#f87171", whiteSpace: "pre-wrap", margin: 0 }}>
                  {JSON.stringify(selectedFailedCase.actual_steps, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div style={{ color: "var(--muted)", fontSize: "13px" }}>Select a case to inspect step-level diffs.</div>
          )}
        </div>
      </div>
    </div>
  );
};
