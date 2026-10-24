import React, { useEffect, useState, useCallback } from "react";
import { Header } from "./components/Header";
import { HeroStats } from "./components/HeroStats";
import { CaseFilters } from "./components/CaseFilters";
import { CaseTable } from "./components/CaseTable";
import { CaseDrawer } from "./components/CaseDrawer";
import { SettingsModal } from "./components/SettingsModal";
import { api } from "./api/client";
import type { CaseDetailResponse, CaseSummary, StatsResponse } from "./types";
import "./styles/theme.css";

export const App: React.FC = () => {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [totalCases, setTotalCases] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loadingCases, setLoadingCases] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [runningBatch, setRunningBatch] = useState(false);
  const [caseDetail, setCaseDetail] = useState<CaseDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const loadStats = useCallback(async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (e) {
      console.error("Failed to load stats:", e);
    }
  }, []);

  const loadCases = useCallback(async () => {
    setLoadingCases(true);
    try {
      const res = await api.getCases(0, 50, search || undefined, statusFilter || undefined);
      setCases(res.cases);
      setTotalCases(res.total);
    } catch (e) {
      console.error("Failed to load cases:", e);
    } finally {
      setLoadingCases(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const handleSelectCase = async (caseId: string) => {
    setLoadingDetail(true);
    try {
      const detail = await api.getCaseDetail(caseId);
      setCaseDetail(detail);
    } catch (e) {
      console.error("Failed to load case detail:", e);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleAuditCase = async (caseId: string) => {
    setLoadingDetail(true);
    try {
      const detail = await api.auditCase(caseId);
      setCaseDetail(detail);
      loadStats();
      loadCases();
    } catch (e) {
      console.error("Failed to audit case:", e);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleRunBatch = async () => {
    setRunningBatch(true);
    try {
      await api.runBatchAudit();
      await loadStats();
      await loadCases();
    } catch (e) {
      console.error("Failed batch audit:", e);
    } finally {
      setRunningBatch(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadStats(), loadCases()]);
    setRefreshing(false);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#000000", color: "#ffffff" }}>
      <Header
        onOpenSettings={() => setIsSettingsOpen(true)}
        onRefresh={handleRefresh}
        isRefreshing={refreshing}
      />

      <HeroStats
        stats={stats}
        onRunBatch={handleRunBatch}
        isRunningBatch={runningBatch}
      />

      <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "0 32px 64px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 500, margin: 0 }}>
            Audit Requests ({totalCases})
          </h2>
        </div>

        <CaseFilters
          search={search}
          onSearchChange={setSearch}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
        />

        <CaseTable
          cases={cases}
          loading={loadingCases}
          onSelectCase={handleSelectCase}
          onAuditCase={handleAuditCase}
        />
      </main>

      <CaseDrawer
        caseDetail={caseDetail}
        loading={loadingDetail}
        onClose={() => setCaseDetail(null)}
      />


      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSaved={handleRefresh}
      />
    </div>
  );
};

export default App;
