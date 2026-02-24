"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

import { runChart } from "@/lib/api";
import type { ChartRunResponse, ChartSpec, FilterValues } from "@/lib/types";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface ChartRendererProps {
  datasetId: string;
  chart: ChartSpec;
  filters: FilterValues;
  dense?: boolean;
}

function toFriendlyLabel(value: string): string {
  return value.replaceAll("_", " ").trim();
}

function toNumber(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatCompact(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function correlation(xs: number[], ys: number[]): number | null {
  if (xs.length !== ys.length || xs.length < 3) return null;
  const n = xs.length;
  const meanX = xs.reduce((a, b) => a + b, 0) / n;
  const meanY = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let denX = 0;
  let denY = 0;
  for (let i = 0; i < n; i += 1) {
    const dx = xs[i] - meanX;
    const dy = ys[i] - meanY;
    num += dx * dy;
    denX += dx * dx;
    denY += dy * dy;
  }
  const den = Math.sqrt(denX * denY);
  if (den === 0) return null;
  return num / den;
}

function buildDataStory(chart: ChartSpec, payload: ChartRunResponse | null): { meaning: string; reading: string } {
  const xField = toFriendlyLabel(payload?.x_field ?? chart.x);
  const yField = toFriendlyLabel(payload?.y_field ?? chart.y);

  if (!payload || payload.rows.length === 0) {
    return {
      meaning: `No rows were returned for ${yField} by ${xField} under current filters.`,
      reading: "Adjust filters or reset view to load more relevant chart data."
    };
  }

  const rows = payload.rows;
  const yNumbers = rows
    .map((row) => toNumber(row[payload.y_field]))
    .filter((value): value is number => value !== null);

  if (chart.type === "line") {
    if (yNumbers.length >= 2) {
      const first = yNumbers[0];
      const last = yNumbers[yNumbers.length - 1];
      const deltaPct = first !== 0 ? ((last - first) / Math.abs(first)) * 100 : 0;
      const peak = rows.reduce((best, row) => {
        const y = toNumber(row[payload.y_field]) ?? Number.NEGATIVE_INFINITY;
        const bestY = toNumber(best[payload.y_field]) ?? Number.NEGATIVE_INFINITY;
        return y > bestY ? row : best;
      }, rows[0]);
      return {
        meaning: `${yField} ${deltaPct >= 0 ? "increased" : "decreased"} by ${Math.abs(deltaPct).toFixed(1)}% across the visible ${xField} window.`,
        reading: `Peak ${yField} occurs at ${String(peak[payload.x_field])} with ${formatCompact(
          toNumber(peak[payload.y_field]) ?? 0
        )}.`
      };
    }
    return {
      meaning: `This line currently has limited points for ${yField} over ${xField}.`,
      reading: "Use a wider date/category filter to reveal a clearer trend."
    };
  }

  if (chart.type === "bar" || chart.type === "missingness") {
    const top = rows.reduce((best, row) => {
      const y = toNumber(row[payload.y_field]) ?? Number.NEGATIVE_INFINITY;
      const bestY = toNumber(best[payload.y_field]) ?? Number.NEGATIVE_INFINITY;
      return y > bestY ? row : best;
    }, rows[0]);
    const topX = String(top[payload.x_field]);
    const topY = toNumber(top[payload.y_field]) ?? 0;
    const total = yNumbers.reduce((acc, val) => acc + val, 0);
    const share = total > 0 ? (topY / total) * 100 : 0;
    return {
      meaning: `${topX} is the leading ${xField} with ${formatCompact(topY)} ${yField}.`,
      reading: `That top bar contributes ${share.toFixed(1)}% of the visible total (${formatCompact(total)}).`
    };
  }

  if (chart.type === "histogram") {
    const dominant = rows.reduce((best, row) => {
      const y = toNumber(row[payload.y_field]) ?? Number.NEGATIVE_INFINITY;
      const bestY = toNumber(best[payload.y_field]) ?? Number.NEGATIVE_INFINITY;
      return y > bestY ? row : best;
    }, rows[0]);
    return {
      meaning: `Most rows fall in bucket ${String(dominant[payload.x_field])} for ${yField}.`,
      reading: `That bucket contains ${formatCompact(toNumber(dominant[payload.y_field]) ?? 0)} rows, indicating where values are most concentrated.`
    };
  }

  if (chart.type === "scatter") {
    const pairs = rows
      .map((row) => {
        const x = toNumber(row[payload.x_field]);
        const y = toNumber(row[payload.y_field]);
        return x !== null && y !== null ? { x, y } : null;
      })
      .filter((item): item is { x: number; y: number } => item !== null);
    const corr = correlation(
      pairs.map((p) => p.x),
      pairs.map((p) => p.y)
    );
    if (corr === null) {
      return {
        meaning: `Scatter points compare ${xField} vs ${yField} for each row.`,
        reading: "Correlation is not stable yet with current filtered sample size."
      };
    }
    const strength = Math.abs(corr) >= 0.7 ? "strong" : Math.abs(corr) >= 0.4 ? "moderate" : "weak";
    const direction = corr >= 0 ? "positive" : "negative";
    return {
      meaning: `Observed ${strength} ${direction} relationship between ${xField} and ${yField} (r=${corr.toFixed(2)}).`,
      reading: "Each dot is one row. A tighter diagonal cloud indicates stronger relationship."
    };
  }

  return {
    meaning: `This chart summarizes ${yField} by ${xField}.`,
    reading: "Use the data preview to inspect exact row-level values."
  };
}

function buildOption(payload: ChartRunResponse): Record<string, unknown> {
  const xValues = payload.rows.map((row) => row[payload.x_field] ?? null);
  const yValues = payload.rows.map((row) => row[payload.y_field] ?? null);
  const includeZoom = xValues.length > 20;
  const palette = ["#2563eb", "#0ea5a4", "#f59e0b", "#ef4444", "#16a34a", "#06b6d4"];

  if (payload.type === "scatter") {
    return {
      tooltip: { trigger: "item" },
      xAxis: { type: "value", name: payload.x_field, nameLocation: "middle", nameGap: 30 },
      yAxis: { type: "value", name: payload.y_field, nameGap: 20 },
      grid: { left: 56, right: 18, top: 26, bottom: 56 },
      toolbox: {
        feature: {
          saveAsImage: {},
          dataZoom: {},
          restore: {}
        },
        right: 2
      },
      series: [
        {
          type: "scatter",
          symbolSize: 8,
          itemStyle: { color: "#2563eb", opacity: 0.72 },
          data: payload.rows.map((row) => [row[payload.x_field], row[payload.y_field]])
        }
      ],
      dataZoom: includeZoom ? [{ type: "inside" }, { type: "slider", height: 12 }] : undefined,
      animationDuration: 450
    };
  }

  const seriesType = payload.type === "line" ? "line" : "bar";
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 56, right: 18, top: 26, bottom: 56 },
    xAxis: {
      type: "category",
      data: xValues,
      name: payload.x_field,
      axisLabel: { rotate: xValues.length > 8 ? 30 : 0 }
    },
    yAxis: { type: "value", name: payload.y_field },
    toolbox: {
      feature: {
        saveAsImage: {},
        dataZoom: {},
        restore: {}
      },
      right: 2
    },
    series: [
      {
        type: seriesType,
        data: yValues,
        smooth: payload.type === "line",
        areaStyle:
          payload.type === "line"
            ? {
                color: {
                  type: "linear",
                  x: 0,
                  y: 0,
                  x2: 0,
                  y2: 1,
                  colorStops: [
                    { offset: 0, color: "rgba(37, 99, 235, 0.28)" },
                    { offset: 1, color: "rgba(37, 99, 235, 0.04)" }
                  ]
                }
              }
            : undefined,
        itemStyle: {
          color:
            payload.type === "line"
              ? "#2563eb"
              : (params: { dataIndex: number }) => palette[params.dataIndex % palette.length]
        },
        barMaxWidth: 38
      }
    ],
    dataZoom: includeZoom ? [{ type: "inside" }, { type: "slider", height: 12 }] : undefined,
    animationDuration: 450
  };
}

export function ChartRenderer({ datasetId, chart, filters, dense = false }: ChartRendererProps) {
  const [chartData, setChartData] = useState<ChartRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showTable, setShowTable] = useState(false);
  const [runMs, setRunMs] = useState<number | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const startedAtRef = useRef(0);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);
    startedAtRef.current = performance.now();

    runChart(datasetId, chart.chart_id, filters)
      .then((response) => {
        if (!isMounted) return;
        setChartData(response);
        setLastUpdated(new Date().toLocaleTimeString());
        setRunMs(Math.round(performance.now() - startedAtRef.current));
      })
      .catch((fetchError) => {
        if (!isMounted) return;
        const message = fetchError instanceof Error ? fetchError.message : "Chart execution failed.";
        setError(message);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [datasetId, chart.chart_id, filters, reloadToken]);

  const option = useMemo(() => (chartData ? buildOption(chartData) : null), [chartData]);
  const previewRows = useMemo(() => chartData?.rows.slice(0, 8) ?? [], [chartData]);
  const chartHeight = dense ? 260 : 340;
  const guide = useMemo(() => buildDataStory(chart, chartData), [chart, chartData]);

  const ySummary = useMemo(() => {
    if (!chartData || chartData.rows.length === 0) return null;
    const values = chartData.rows
      .map((row) => Number(row[chartData.y_field]))
      .filter((value) => Number.isFinite(value));
    if (values.length === 0) return null;
    const sum = values.reduce((acc, value) => acc + value, 0);
    const max = Math.max(...values);
    const min = Math.min(...values);
    return {
      sum: sum.toLocaleString(undefined, { maximumFractionDigits: 2 }),
      avg: (sum / values.length).toLocaleString(undefined, { maximumFractionDigits: 2 }),
      min: min.toLocaleString(undefined, { maximumFractionDigits: 2 }),
      max: max.toLocaleString(undefined, { maximumFractionDigits: 2 })
    };
  }, [chartData]);

  function exportCsv(): void {
    if (!chartData || chartData.rows.length === 0) return;
    const headers = Object.keys(chartData.rows[0]);
    const csv = [
      headers.join(","),
      ...chartData.rows.map((row) =>
        headers
          .map((header) => {
            const value = row[header];
            if (value === null || value === undefined) return "";
            const asString = String(value).replaceAll('"', '""');
            return `"${asString}"`;
          })
          .join(",")
      )
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${chart.chart_id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <article className={`chart-card${isExpanded ? " expanded" : ""}`}>
      <div className="chart-head">
        <div>
          <h3>{chart.title}</h3>
          <small>
            {chart.type}
            {chartData ? ` - ${chartData.rows.length} rows` : ""}
            {runMs !== null ? ` - ${runMs}ms` : ""}
            {lastUpdated ? ` - refreshed ${lastUpdated}` : ""}
          </small>
        </div>
        <div className="chart-actions">
          <button type="button" className="icon-btn" onClick={() => setReloadToken((current) => current + 1)}>
            Refresh
          </button>
          <button type="button" className="icon-btn ghost" onClick={() => setShowTable((current) => !current)}>
            {showTable ? "Hide Data" : "Data"}
          </button>
          <button type="button" className="icon-btn ghost" onClick={exportCsv} disabled={!chartData}>
            CSV
          </button>
          <button type="button" className="icon-btn ghost" onClick={() => setIsExpanded((current) => !current)}>
            {isExpanded ? "Collapse" : "Expand"}
          </button>
        </div>
      </div>
      <div className="chart-explain">
        <p>
          <strong>What this chart represents:</strong> {guide.meaning}
        </p>
        <p>
          <strong>How to read it:</strong> {guide.reading}
        </p>
        {ySummary ? (
          <div className="chart-stats">
            <span>Sum: {ySummary.sum}</span>
            <span>Avg: {ySummary.avg}</span>
            <span>Min: {ySummary.min}</span>
            <span>Max: {ySummary.max}</span>
          </div>
        ) : null}
      </div>

      {loading ? <div className="chart-state shimmer">Loading chart...</div> : null}
      {error ? <div className="chart-state error">{error}</div> : null}
      {!loading && !error && option ? (
        <ReactECharts option={option} style={{ height: chartHeight }} opts={{ renderer: "canvas" }} />
      ) : null}
      {showTable && previewRows.length > 0 ? (
        <div className="chart-preview">
          <table>
            <thead>
              <tr>
                {Object.keys(previewRows[0]).map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {previewRows.map((row, index) => (
                <tr key={`${chart.chart_id}-${index}`}>
                  {Object.keys(previewRows[0]).map((column) => (
                    <td key={column}>{String(row[column] ?? "")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <small>Showing first {previewRows.length} rows.</small>
        </div>
      ) : null}
    </article>
  );
}
