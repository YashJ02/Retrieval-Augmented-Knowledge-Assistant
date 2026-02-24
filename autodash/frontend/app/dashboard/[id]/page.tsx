"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ChartRenderer } from "@/components/ChartRenderer";
import { FilterBar } from "@/components/FilterBar";
import { InsightPanel } from "@/components/InsightPanel";
import { KPIGrid } from "@/components/KPIGrid";
import { generateDashboard, getDashboard } from "@/lib/api";
import type { DashboardSpec, FilterValues } from "@/lib/types";

type LayoutMode = "auto" | "two" | "three";
type ChartTypeFilter = "all" | "line" | "bar" | "histogram" | "scatter" | "missingness" | "pie" | "radar";

export default function DashboardPage() {
  const params = useParams<{ id: string }>();
  const datasetId = params.id;
  const searchRef = useRef<HTMLInputElement>(null);

  const [dashboard, setDashboard] = useState<DashboardSpec | null>(null);
  const [filters, setFilters] = useState<FilterValues>({});
  const [denseMode, setDenseMode] = useState(false);
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("auto");
  const [chartQuery, setChartQuery] = useState("");
  const [chartTypeFilter, setChartTypeFilter] = useState<ChartTypeFilter>("all");
  const [hiddenCharts, setHiddenCharts] = useState<Record<string, boolean>>({});
  const [syncTick, setSyncTick] = useState(0);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditingSpec, setIsEditingSpec] = useState(false);
  const [specInput, setSpecInput] = useState("");

  const viewStorageKey = `autodash:view:${datasetId}`;
  const activeFilterCount = useMemo(() => Object.keys(filters).length, [filters]);
  const visibleCharts = useMemo(() => {
    if (!dashboard) return [];
    const query = chartQuery.trim().toLowerCase();
    return dashboard.charts.filter((chart) => {
      if (hiddenCharts[chart.chart_id]) return false;
      if (chartTypeFilter !== "all" && chart.type !== chartTypeFilter) return false;
      if (!query) return true;
      return (
        chart.title.toLowerCase().includes(query) ||
        chart.chart_id.toLowerCase().includes(query) ||
        chart.type.toLowerCase().includes(query)
      );
    });
  }, [chartQuery, chartTypeFilter, dashboard, hiddenCharts]);

  const loadDashboard = useCallback(async (): Promise<void> => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);

    try {
      const spec = await getDashboard(datasetId).catch(async () => generateDashboard(datasetId));
      setDashboard(spec);
      setLastSync(new Date().toLocaleTimeString());
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load dashboard.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard, syncTick]);

  useEffect(() => {
    if (!datasetId) return;
    const raw = window.localStorage.getItem(viewStorageKey);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as {
        denseMode?: boolean;
        layoutMode?: LayoutMode;
        chartTypeFilter?: ChartTypeFilter;
        hiddenCharts?: Record<string, boolean>;
      };
      setDenseMode(Boolean(parsed.denseMode));
      setLayoutMode(parsed.layoutMode ?? "auto");
      setChartTypeFilter(parsed.chartTypeFilter ?? "all");
      setHiddenCharts(parsed.hiddenCharts ?? {});
    } catch {
      window.localStorage.removeItem(viewStorageKey);
    }
  }, [datasetId, viewStorageKey]);

  useEffect(() => {
    if (!datasetId) return;
    window.localStorage.setItem(
      viewStorageKey,
      JSON.stringify({
        denseMode,
        layoutMode,
        chartTypeFilter,
        hiddenCharts
      })
    );
  }, [chartTypeFilter, datasetId, denseMode, hiddenCharts, layoutMode, viewStorageKey]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      const target = event.target as HTMLElement | null;
      const isTyping =
        target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.tagName === "SELECT";
      if (isTyping && event.key !== "Escape") return;

      if (event.key === "/") {
        event.preventDefault();
        searchRef.current?.focus();
        searchRef.current?.select();
      } else if (event.key.toLowerCase() === "d") {
        event.preventDefault();
        setDenseMode((value) => !value);
      } else if (event.key.toLowerCase() === "s") {
        event.preventDefault();
        setSyncTick((value) => value + 1);
      } else if (event.key.toLowerCase() === "l") {
        event.preventDefault();
        setLayoutMode((current) => {
          if (current === "auto") return "two";
          if (current === "two") return "three";
          return "auto";
        });
      } else if (event.key === "Escape") {
        setChartQuery("");
        setChartTypeFilter("all");
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function toggleChartVisibility(chartId: string): void {
    setHiddenCharts((current) => ({
      ...current,
      [chartId]: !current[chartId]
    }));
  }

  function resetView(): void {
    setChartQuery("");
    setChartTypeFilter("all");
    setLayoutMode("auto");
    setHiddenCharts({});
    setDenseMode(false);
  }

  function openSpecEditor(): void {
    if (!dashboard) return;
    setSpecInput(JSON.stringify(dashboard, null, 2));
    setIsEditingSpec(true);
  }

  function saveSpec(): void {
    try {
      const parsed = JSON.parse(specInput) as DashboardSpec;
      setDashboard(parsed);
      setIsEditingSpec(false);
      setError(null);
    } catch (err) {
      setError("Invalid JSON spec.");
    }
  }

  if (loading) {
    return (
      <main className="shell">
        <div className="panel shimmer">Preparing dashboard...</div>
      </main>
    );
  }

  if (error || !dashboard) {
    return (
      <main className="shell">
        <div className="panel">
          <p>{error ?? "Dashboard not found."}</p>
          <Link href="/">Return to upload</Link>
        </div>
      </main>
    );
  }

  return (
    <main className={`dashboard-shell${denseMode ? " dense" : ""}`}>
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">Dataset {dashboard.dataset_id}</p>
          <h1>Auto-generated Analytics Dashboard</h1>
          <p>Detected type: {dashboard.detected_type}</p>
        </div>
        <div className="header-actions">
          <button type="button" className="ghost" onClick={openSpecEditor}>
            Edit Spec
          </button>
          <button type="button" className="ghost" onClick={() => setSyncTick((value) => value + 1)}>
            Sync Spec
          </button>
          <button type="button" className="ghost" onClick={() => setDenseMode((value) => !value)}>
            {denseMode ? "Comfort View" : "Dense View"}
          </button>
          <Link href="/">Upload Another Dataset</Link>
        </div>
      </header>

      <section className="dashboard-meta">
        <div className="meta-chip">KPIs: {dashboard.kpis.length}</div>
        <div className="meta-chip">Charts: {visibleCharts.length} / {dashboard.charts.length}</div>
        <div className="meta-chip">Filters Active: {activeFilterCount}</div>
        <div className="meta-chip">Spec v{dashboard.version}</div>
        <div className="meta-chip">Synced: {lastSync ?? "pending"}</div>
      </section>

      {isEditingSpec && (
        <div className="modal-overlay">
          <div className="modal-content panel">
            <h2>Edit Dashboard Spec</h2>
            <textarea
              className="spec-editor"
              value={specInput}
              onChange={(e) => setSpecInput(e.target.value)}
              rows={20}
            />
            <div className="modal-actions">
              <button type="button" className="ghost" onClick={() => setIsEditingSpec(false)}>
                Cancel
              </button>
              <button type="button" onClick={saveSpec}>
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      <KPIGrid items={dashboard.kpis} />
      <FilterBar filters={dashboard.filters} onApply={setFilters} />

      <section className="dashboard-tools">
        <div className="tool-row">
          <div className="tool-group grow">
            <label htmlFor="chart-search">Chart Search</label>
            <input
              id="chart-search"
              ref={searchRef}
              className="tool-input"
              value={chartQuery}
              onChange={(event) => setChartQuery(event.target.value)}
              placeholder="Press / to focus. Search by title/type/id."
            />
          </div>
          <div className="tool-group">
            <label htmlFor="type-filter">Type</label>
            <select
              id="type-filter"
              className="tool-input"
              value={chartTypeFilter}
              onChange={(event) => setChartTypeFilter(event.target.value as ChartTypeFilter)}
            >
              <option value="all">All</option>
              <option value="line">Line</option>
              <option value="bar">Bar</option>
              <option value="histogram">Histogram</option>
              <option value="scatter">Scatter</option>
              <option value="missingness">Missingness</option>
              <option value="pie">Pie</option>
              <option value="radar">Radar</option>
            </select>
          </div>
          <div className="tool-group">
            <label htmlFor="layout-mode">Layout</label>
            <select
              id="layout-mode"
              className="tool-input"
              value={layoutMode}
              onChange={(event) => setLayoutMode(event.target.value as LayoutMode)}
            >
              <option value="auto">Auto</option>
              <option value="two">2 Columns</option>
              <option value="three">3 Columns</option>
            </select>
          </div>
          <div className="tool-group tool-actions">
            <button type="button" className="ghost" onClick={resetView}>
              Reset View
            </button>
          </div>
        </div>
        <div className="chart-nav">
          {dashboard.charts.map((chart) => (
            <button
              key={chart.chart_id}
              type="button"
              className={`nav-chip${hiddenCharts[chart.chart_id] ? " hidden" : ""}`}
              onClick={() => toggleChartVisibility(chart.chart_id)}
              title={hiddenCharts[chart.chart_id] ? "Show chart" : "Hide chart"}
            >
              {chart.title}
            </button>
          ))}
        </div>
      </section>

      <section className={`charts-grid layout-${layoutMode}`}>
        {visibleCharts.map((chart) => (
          <div key={chart.chart_id} id={`chart-${chart.chart_id}`} className="chart-wrap">
            <ChartRenderer datasetId={dashboard.dataset_id} chart={chart} filters={filters} dense={denseMode} />
          </div>
        ))}
      </section>
      {visibleCharts.length === 0 ? (
        <section className="panel">
          <p>No charts match your current view constraints. Reset search/type/visibility filters.</p>
        </section>
      ) : null}

      <InsightPanel insights={dashboard.insights} />
    </main>
  );
}

