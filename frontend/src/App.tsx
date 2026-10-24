import React, { useEffect, useState, useCallback } from "react";
import { Header } from "./components/Header";
import { HeroStats } from "./components/HeroStats";
import { CaseFilters } from "./components/CaseFilters";
import { CaseTable } from "./components/CaseTable";
import { SettingsModal } from "./components/SettingsModal";
import { RunsPage } from "./pages/RunsPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { EvalPage } from "./pages/EvalPage";
import { UsagePage } from "./pages/UsagePage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { api } from "./api/client";
import type { CaseDetailResponse, CaseSummary, RunItem, StatsResponse } from "./types";
import "./styles/theme.css";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState("runs");
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loadingCases, setLoadingCases] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [runningBatch, setRunningBatch] = useState(false);
  const [selectedCase, setSelectedCase] = useState<CaseDetailResponse | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [connError, setConnError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoadingCases(true);
    setRefreshing(true);
    try {
      const [s, c, r] = await Promise.all([api.getStats(), api.getCases(0, 100), api.getRuns()]);
      setStats(s);
      setCases(c.cases);
      setRuns(r);
      setConnError(null);
    } catch {
      setConnError("Backend unreachable on 127.0.0.1:8000. Start local server or configure Render URL in API Key settings.");
    } finally {
      setLoadingCases(false);
      setRefreshing(false);
    }
  }, []);


  useEffect(() => { loadData(); }, [loadData]);

  const handleSelectCase = async (caseId: string) => {
    try {
      const detail = await api.getCaseDetail(caseId);
      setSelectedCase(detail);
    } catch (e) {
      console.error(e);
    }
  };

  const handleReRunCase = async (caseId: string) => {
    try {
      const detail = await api.auditCase(caseId);
      setSelectedCase(detail);
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleNavigateCase = (dir: "prev" | "next") => {
    if (!selectedCase) return;
    const idx = cases.findIndex((c) => c.case_id === selectedCase.case_id);
    const nextIdx = dir === "next" ? (idx + 1) % cases.length : (idx - 1 + cases.length) % cases.length;
    handleSelectCase(cases[nextIdx].case_id);
  };

  const handleRunBatch = async () => {
    setRunningBatch(true);
    try {
      await api.runBatchAudit();
      await loadData();
    } catch (e) {
      console.error(e);
    } finally {
      setRunningBatch(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#000000", color: "#ffffff" }}>
      <Header
        activeTab={activeTab}
        onTabChange={(t) => { setSelectedCase(null); setActiveTab(t); }}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onRefresh={loadData}
        isRefreshing={refreshing}
      />

      {connError && (
        <div style={{
          maxWidth: "1100px", margin: "16px auto 0", padding: "10px 18px",
          background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.4)",
          borderRadius: "8px", fontSize: "12.5px", color: "#fca5a5",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span>{connError}</span>
          <button className="btn-solid" onClick={() => setIsSettingsOpen(true)} style={{ height: "26px", fontSize: "11px", padding: "0 8px" }}>
            Configure URL
          </button>
        </div>
      )}

      <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "32px 32px 64px" }}>
        {selectedCase ? (
          <div>
            <button className="btn-ghost" onClick={() => setSelectedCase(null)} style={{ marginBottom: "16px", fontSize: "12px", padding: "6px 12px" }}>
              ← Back to Overview
            </button>
            <CaseDetailPage
              caseDetail={selectedCase}
              onReRun={handleReRunCase}
              onNavigate={handleNavigateCase}
            />
          </div>
        ) : (
          <>
            {activeTab === "runs" && (
              <RunsPage
                runs={runs}
                cases={cases}
                onStartRun={handleRunBatch}
                onOpenCase={handleSelectCase}
              />
            )}

            {activeTab === "cases" && (
              <div>
                <HeroStats stats={stats} onRunBatch={handleRunBatch} isRunningBatch={runningBatch} />
                <CaseFilters search={search} onSearchChange={setSearch} statusFilter={statusFilter} onStatusFilterChange={setStatusFilter} />
                <CaseTable
                  cases={cases.filter((c) => (!search || c.case_id.toLowerCase().includes(search.toLowerCase()) || c.email.toLowerCase().includes(search.toLowerCase())) && (!statusFilter || c.status === statusFilter))}
                  loading={loadingCases}
                  onSelectCase={handleSelectCase}
                  onAuditCase={handleReRunCase}
                />
              </div>
            )}

            {activeTab === "review" && <ReviewQueuePage onOpenCase={handleSelectCase} />}
            {activeTab === "eval" && <EvalPage />}
            {activeTab === "usage" && <UsagePage />}
          </>
        )}
      </main>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSaved={loadData}
      />
    </div>
  );
};

export default App;
