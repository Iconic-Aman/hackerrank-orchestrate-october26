import React, { useState, useEffect } from "react";
import type { EvalMetrics, CaseEvalResult } from "../types";
import { api } from "../api/client";
import { Play, CheckCircle, AlertTriangle, Search, RefreshCw, FileText } from "lucide-react";

export const EvalPage: React.FC = () => {
  const [metrics, setMetrics] = useState<EvalMetrics | null>(null);
  const [selectedDataset, setSelectedDataset] = useState("samples");
  const [selectedCase, setSelectedCase] = useState<CaseEvalResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<"all" | "passed" | "failed">("all");
  const [search, setSearch] = useState("");
  const [showRawJson, setShowRawJson] = useState(false);

  const loadMetrics = async (ds: string, refresh = false) => {
    setLoading(true);
    try {
      const data = await api.getEval(ds, refresh);
      setMetrics(data);
      if (data.cases && data.cases.length > 0) {
        // Select first failed case if any, otherwise first case
        const firstFailed = data.cases.find((c) => !c.status_match || !c.step_match);
        setSelectedCase(firstFailed || data.cases[0]);
      } else {
        setSelectedCase(null);
      }
    } catch (e) {
      console.error("Evaluation error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics(selectedDataset, false);
  }, [selectedDataset]);

  const allCases = metrics?.cases || [];
  const filteredCases = allCases.filter((c) => {
    const isPassed = c.status_match && c.step_match;
    if (filter === "passed" && !isPassed) return false;
    if (filter === "failed" && isPassed) return false;
    if (search) {
      const q = search.toLowerCase();
      return c.case_id.toLowerCase().includes(q) || c.email.toLowerCase().includes(q);
    }
    return true;
  });

  const passedCount = allCases.filter((c) => c.status_match && c.step_match).length;
  const failedCount = allCases.length - passedCount;

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "0 0 40px" }}>
      {/* Header bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "22px", margin: "0 0 6px", fontWeight: 600 }}>Evaluation & Ground Truth Benchmarking</h2>
          <div style={{ fontSize: "13px", color: "var(--muted)" }}>
            Evaluate agent against golden answers in <code>sample_output.csv</code> (32 cases) with step-level and sequence validation
          </div>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <select
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            style={{
              background: "#111",
              border: "1px solid var(--border)",
              color: "#fff",
              padding: "8px 14px",
              borderRadius: "6px",
              fontSize: "13px",
            }}
          >
            <option value="samples">Sample Dataset (32 cases)</option>
            <option value="extra_cases">Participant Custom Cases (3 cases)</option>
            <option value="mutation_tests">Mutation Re-sync Drift Tests</option>
          </select>

          <button
            className="btn-solid"
            onClick={() => loadMetrics(selectedDataset, true)}
            disabled={loading}
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            {loading ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
            <span>{loading ? "Evaluating..." : "Run Evaluation"}</span>
          </button>
        </div>
      </div>

      {/* Accuracy KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "14px", marginBottom: "24px" }}>
        <div className="card-glass">
          <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>Status Accuracy</div>
          <div style={{ fontSize: "28px", fontWeight: 600, color: "#4ade80", marginTop: "4px" }}>
            {metrics ? `${(metrics.status_accuracy * 100).toFixed(1)}%` : "--"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--stat)", marginTop: "2px" }}>
            {metrics ? `${allCases.filter((c) => c.status_match).length} / ${allCases.length || 32} correct` : "Complete / Incomplete / NA"}
          </div>
        </div>

        <div className="card-glass">
          <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>Step Accuracy</div>
          <div style={{ fontSize: "28px", fontWeight: 600, color: "#60a5fa", marginTop: "4px" }}>
            {metrics ? `${(metrics.step_accuracy * 100).toFixed(1)}%` : "--"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--stat)", marginTop: "2px" }}>Operation & resource recall</div>
        </div>

        <div className="card-glass">
          <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>Field Accuracy</div>
          <div style={{ fontSize: "28px", fontWeight: 600, color: "#c084fc", marginTop: "4px" }}>
            {metrics ? `${(metrics.field_accuracy * 100).toFixed(1)}%` : "--"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--stat)", marginTop: "2px" }}>System, state & evidence match</div>
        </div>

        <div className="card-glass">
          <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>Sequence Accuracy</div>
          <div style={{ fontSize: "28px", fontWeight: 600, color: "#fbbf24", marginTop: "4px" }}>
            {metrics ? `${(metrics.sequence_accuracy * 100).toFixed(1)}%` : "--"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--stat)", marginTop: "2px" }}>Strict phase hierarchy order</div>
        </div>
      </div>

      {/* Main Master-Detail Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: "18px", alignItems: "start" }}>
        {/* Left Column: Case List with Filters */}
        <div className="card-glass" style={{ padding: "16px", maxHeight: "780px", display: "flex", flexDirection: "column" }}>
          {/* Filter Pills & Search */}
          <div style={{ display: "flex", gap: "6px", marginBottom: "12px" }}>
            <button
              onClick={() => setFilter("all")}
              style={{
                padding: "4px 10px",
                fontSize: "12px",
                borderRadius: "4px",
                border: "1px solid",
                borderColor: filter === "all" ? "var(--primary)" : "var(--border-soft)",
                background: filter === "all" ? "rgba(255,255,255,0.12)" : "transparent",
                color: "#fff",
                cursor: "pointer",
              }}
            >
              All ({allCases.length})
            </button>
            <button
              onClick={() => setFilter("passed")}
              style={{
                padding: "4px 10px",
                fontSize: "12px",
                borderRadius: "4px",
                border: "1px solid",
                borderColor: filter === "passed" ? "#4ade80" : "var(--border-soft)",
                background: filter === "passed" ? "rgba(74, 222, 128, 0.15)" : "transparent",
                color: "#4ade80",
                cursor: "pointer",
              }}
            >
              Passed ({passedCount})
            </button>
            <button
              onClick={() => setFilter("failed")}
              style={{
                padding: "4px 10px",
                fontSize: "12px",
                borderRadius: "4px",
                border: "1px solid",
                borderColor: filter === "failed" ? "#f87171" : "var(--border-soft)",
                background: filter === "failed" ? "rgba(248, 113, 113, 0.15)" : "transparent",
                color: "#f87171",
                cursor: "pointer",
              }}
            >
              Deviations ({failedCount})
            </button>
          </div>

          <div style={{ position: "relative", marginBottom: "12px" }}>
            <Search size={14} style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "var(--muted)" }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search case_id or email..."
              style={{
                width: "100%",
                padding: "6px 10px 6px 30px",
                background: "rgba(0,0,0,0.5)",
                border: "1px solid var(--border-soft)",
                borderRadius: "6px",
                color: "#fff",
                fontSize: "12px",
              }}
            />
          </div>

          {/* Scrollable Cases List */}
          <div style={{ overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: "6px", paddingRight: "4px" }}>
            {loading ? (
              <div style={{ padding: "40px 0", textAlign: "center", color: "var(--muted)", fontSize: "13px" }}>
                <RefreshCw size={20} className="animate-spin" style={{ margin: "0 auto 8px" }} />
                Auditing {selectedDataset} cases...
              </div>
            ) : filteredCases.length === 0 ? (
              <div style={{ padding: "40px 0", textAlign: "center", color: "var(--muted)", fontSize: "13px" }}>
                No cases match the selected filter.
              </div>
            ) : (
              filteredCases.map((c) => {
                const isSelected = selectedCase?.case_id === c.case_id;
                const isPassed = c.status_match && c.step_match;
                return (
                  <div
                    key={c.case_id}
                    onClick={() => setSelectedCase(c)}
                    style={{
                      padding: "10px",
                      borderRadius: "6px",
                      background: isSelected ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.35)",
                      border: isSelected ? "1px solid rgba(255,255,255,0.3)" : "1px solid var(--border-soft)",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: 600, fontSize: "13px", color: isPassed ? "#4ade80" : "#f87171" }}>
                        {c.case_id}
                      </span>
                      <span
                        style={{
                          fontSize: "10.5px",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: isPassed ? "rgba(74, 222, 128, 0.15)" : "rgba(248, 113, 113, 0.15)",
                          color: isPassed ? "#4ade80" : "#f87171",
                          fontWeight: 500,
                        }}
                      >
                        {isPassed ? "PASS" : "DEV"}
                      </span>
                    </div>

                    <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "3px", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                      {c.email}
                    </div>

                    <div style={{ display: "flex", gap: "8px", marginTop: "6px", fontSize: "11px" }}>
                      <span style={{ color: "var(--muted)" }}>
                        Status: <strong style={{ color: c.status_match ? "#4ade80" : "#f87171" }}>{c.actual_status}</strong>
                      </span>
                      {c.expected_status !== c.actual_status && (
                        <span style={{ color: "#f87171" }}>(exp: {c.expected_status})</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Case Deep-Dive & Diff View */}
        <div className="card-glass" style={{ padding: "20px" }}>
          {selectedCase ? (
            <div>
              {/* Selected Case Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <h3 style={{ margin: 0, fontSize: "18px", fontWeight: 600 }}>{selectedCase.case_id}</h3>
                    {selectedCase.status_match && selectedCase.step_match ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "#4ade80", fontSize: "12px", background: "rgba(74,222,128,0.15)", padding: "2px 8px", borderRadius: "4px" }}>
                        <CheckCircle size={12} /> Ground Truth Matched (100%)
                      </span>
                    ) : (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "#f87171", fontSize: "12px", background: "rgba(248,113,113,0.15)", padding: "2px 8px", borderRadius: "4px" }}>
                        <AlertTriangle size={12} /> Deviation Detected
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "4px" }}>
                    Requesting Email: <strong style={{ color: "#fff" }}>{selectedCase.email}</strong>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <button
                    onClick={() => setShowRawJson(!showRawJson)}
                    className="btn-ghost"
                    style={{ fontSize: "11.5px", padding: "4px 8px" }}
                  >
                    <FileText size={12} style={{ marginRight: "4px" }} />
                    {showRawJson ? "Formatted View" : "Raw JSON"}
                  </button>
                </div>
              </div>

              {/* Status Comparison Banner */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                  padding: "12px",
                  borderRadius: "6px",
                  background: "rgba(0,0,0,0.5)",
                  border: "1px solid var(--border-soft)",
                  marginBottom: "16px",
                }}
              >
                <div>
                  <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>Expected Status (Golden)</div>
                  <div style={{ fontSize: "14px", fontWeight: 600, color: "#4ade80", marginTop: "2px" }}>
                    {selectedCase.expected_status}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase" }}>Agent Status (Predicted)</div>
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: selectedCase.status_match ? "#4ade80" : "#f87171",
                      marginTop: "2px",
                    }}
                  >
                    {selectedCase.actual_status} {selectedCase.status_match ? "✓" : "✗ Mismatch"}
                  </div>
                </div>
              </div>

              {/* Reason / Diagnostic notes */}
              {selectedCase.reason && (
                <div style={{ fontSize: "12px", color: selectedCase.status_match && selectedCase.step_match ? "#4ade80" : "#fbbf24", marginBottom: "16px", background: "rgba(255,255,255,0.03)", padding: "8px 12px", borderRadius: "4px" }}>
                  <strong>Diagnostic:</strong> {selectedCase.reason}
                </div>
              )}

              {/* Side-by-Side Steps Comparison */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                {/* Left Panel: Expected Steps */}
                <div style={{ background: "rgba(0,0,0,0.6)", padding: "12px", borderRadius: "6px", border: "1px solid var(--border-soft)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <span style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase", fontWeight: 600 }}>
                      Expected Steps ({selectedCase.expected_steps?.length || 0})
                    </span>
                    <span style={{ fontSize: "11px", color: "#4ade80" }}>Golden</span>
                  </div>

                  {showRawJson ? (
                    <pre style={{ fontSize: "11px", color: "#4ade80", whiteSpace: "pre-wrap", margin: 0, maxHeight: "420px", overflowY: "auto" }}>
                      {JSON.stringify(selectedCase.expected_steps, null, 2)}
                    </pre>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "420px", overflowY: "auto" }}>
                      {selectedCase.expected_steps?.length === 0 ? (
                        <div style={{ fontSize: "12px", color: "var(--muted)", padding: "16px 0", textAlign: "center" }}>
                          No steps (NOT_APPLICABLE)
                        </div>
                      ) : (
                        selectedCase.expected_steps.map((st, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: "8px",
                              borderRadius: "4px",
                              background: "rgba(255,255,255,0.03)",
                              border: "1px solid rgba(74,222,128,0.2)",
                              fontSize: "11.5px",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", color: "#4ade80", fontWeight: 600 }}>
                              <span>#{st.step_no} {st.operation}</span>
                              <span style={{ fontSize: "10px", color: "var(--muted)" }}>{st.phase}</span>
                            </div>
                            <div style={{ color: "var(--muted)", marginTop: "2px", fontSize: "11px" }}>
                              {st.system_id} / <strong>{st.resource_id}</strong> &rarr; {st.state}
                            </div>
                            {st.evidence_id && (
                              <div style={{ fontSize: "10px", color: "#60a5fa", marginTop: "2px" }}>
                                Evidence: {st.evidence_id}
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>

                {/* Right Panel: Agent Steps */}
                <div style={{ background: "rgba(0,0,0,0.6)", padding: "12px", borderRadius: "6px", border: "1px solid var(--border-soft)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <span style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase", fontWeight: 600 }}>
                      Agent Predicted Steps ({selectedCase.actual_steps?.length || 0})
                    </span>
                    <span style={{ fontSize: "11px", color: selectedCase.step_match ? "#4ade80" : "#f87171" }}>
                      {selectedCase.step_match ? "Matches" : "Deviates"}
                    </span>
                  </div>

                  {showRawJson ? (
                    <pre
                      style={{
                        fontSize: "11px",
                        color: selectedCase.step_match ? "#4ade80" : "#f87171",
                        whiteSpace: "pre-wrap",
                        margin: 0,
                        maxHeight: "420px",
                        overflowY: "auto",
                      }}
                    >
                      {JSON.stringify(selectedCase.actual_steps, null, 2)}
                    </pre>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "420px", overflowY: "auto" }}>
                      {selectedCase.actual_steps?.length === 0 ? (
                        <div style={{ fontSize: "12px", color: "var(--muted)", padding: "16px 0", textAlign: "center" }}>
                          No steps (NOT_APPLICABLE)
                        </div>
                      ) : (
                        selectedCase.actual_steps.map((st, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: "8px",
                              borderRadius: "4px",
                              background: "rgba(255,255,255,0.03)",
                              border: "1px solid rgba(255,255,255,0.08)",
                              fontSize: "11.5px",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", color: "#fff", fontWeight: 600 }}>
                              <span>#{st.step_no} {st.operation}</span>
                              <span style={{ fontSize: "10px", color: "var(--muted)" }}>{st.phase}</span>
                            </div>
                            <div style={{ color: "var(--muted)", marginTop: "2px", fontSize: "11px" }}>
                              {st.system_id} / <strong>{st.resource_id}</strong> &rarr; {st.state}
                            </div>
                            {st.evidence_id && (
                              <div style={{ fontSize: "10px", color: "#60a5fa", marginTop: "2px" }}>
                                Evidence: {st.evidence_id}
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ padding: "60px 0", textAlign: "center", color: "var(--muted)", fontSize: "13px" }}>
              Select a case from the list on the left to inspect its ground-truth diff.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
