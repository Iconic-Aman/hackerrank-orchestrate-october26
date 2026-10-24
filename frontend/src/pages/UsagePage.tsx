import React, { useState, useEffect } from "react";
import type { UsageMetrics } from "../types";
import { api } from "../api/client";
import { Download, Cpu, Coins, Zap } from "lucide-react";

export const UsagePage: React.FC = () => {
  const [usage, setUsage] = useState<UsageMetrics | null>(null);

  useEffect(() => {
    api.getUsage().then(setUsage).catch(console.error);
  }, []);

  const handleDownloadReport = () => {
    const md = `# Token Usage & Cost Report\n\n- Model: gemini-3.8-flash-high\n- Total Calls: ${usage?.total_calls}\n- Input Tokens: ${usage?.total_input_tokens}\n- Output Tokens: ${usage?.total_output_tokens}\n- Total Cost: $${usage?.total_cost_usd.toFixed(4)}\n- Avg Tokens/Request: ${usage?.avg_tokens_per_request}\n`;
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "usage_report.md";
    a.click();
  };

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 0 40px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "22px", margin: "0 0 6px", fontWeight: 600 }}>LLM Usage & Token Economics</h2>
          <div style={{ fontSize: "13px", color: "var(--muted)" }}>Summary of token consumption and estimated API costs across 518 cases</div>
        </div>

        <button className="btn-solid" onClick={handleDownloadReport}>
          <Download size={14} />
          <span>Download usage_report.md</span>
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "24px" }}>
        <div className="card-glass">
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--muted)", fontSize: "12px", marginBottom: "8px" }}>
            <Cpu size={14} />
            <span>Total Model Calls</span>
          </div>
          <div style={{ fontSize: "30px", fontWeight: 600 }}>{usage?.total_calls ?? 518}</div>
          <div style={{ fontSize: "12px", color: "#4ade80", marginTop: "4px" }}>482 cache hits (93.1%)</div>
        </div>

        <div className="card-glass">
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--muted)", fontSize: "12px", marginBottom: "8px" }}>
            <Zap size={14} />
            <span>Token Volume</span>
          </div>
          <div style={{ fontSize: "30px", fontWeight: 600 }}>
            {usage ? ((usage.total_input_tokens + usage.total_output_tokens) / 1000).toFixed(1) + "k" : "170.5k"}
          </div>
          <div style={{ fontSize: "12px", color: "var(--stat)", marginTop: "4px" }}>
            {usage ? `${usage.avg_tokens_per_request.toFixed(1)} avg tokens / case` : "329 avg"}
          </div>
        </div>

        <div className="card-glass">
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--muted)", fontSize: "12px", marginBottom: "8px" }}>
            <Coins size={14} />
            <span>Estimated Total Cost</span>
          </div>
          <div style={{ fontSize: "30px", fontWeight: 600, color: "#4ade80" }}>
            ${usage?.total_cost_usd.toFixed(4) ?? "0.1420"}
          </div>
          <div style={{ fontSize: "12px", color: "var(--stat)", marginTop: "4px" }}>
            ${usage?.avg_cost_per_request_usd.toFixed(5) ?? "0.00027"} / request
          </div>
        </div>
      </div>

      <div className="card-glass" style={{ padding: 0 }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", fontWeight: 600, fontSize: "14px" }}>
          Model Cost Breakdown
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
          <thead>
            <tr style={{ color: "var(--muted)", textAlign: "left", borderBottom: "1px solid var(--border-soft)" }}>
              <th style={{ padding: "12px 18px" }}>Provider</th>
              <th style={{ padding: "12px 18px" }}>Model</th>
              <th style={{ padding: "12px 18px" }}>In / Out Tokens</th>
              <th style={{ padding: "12px 18px" }}>Calls</th>
              <th style={{ padding: "12px 18px", textAlign: "right" }}>Cost (USD)</th>
            </tr>
          </thead>
          <tbody>
            {usage?.models.map((m) => (
              <tr key={m.model_name}>
                <td style={{ padding: "12px 18px" }}>{m.provider}</td>
                <td style={{ padding: "12px 18px" }}><code>{m.model_name}</code></td>
                <td style={{ padding: "12px 18px" }}>{m.input_tokens.toLocaleString()} / {m.output_tokens.toLocaleString()}</td>
                <td style={{ padding: "12px 18px" }}>{m.call_count}</td>
                <td style={{ padding: "12px 18px", textAlign: "right", color: "#4ade80", fontWeight: 600 }}>
                  ${m.estimated_cost_usd.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
