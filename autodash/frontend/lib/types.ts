export type DatasetType =
  | "TIME_SERIES_BUSINESS"
  | "CATEGORICAL_BREAKDOWN"
  | "EVENT_LOG"
  | "NUMERIC_ANALYSIS";

export type ChartType = "line" | "bar" | "histogram" | "scatter" | "missingness";

export interface KPIItem {
  kpi_id: string;
  title: string;
  value: number;
  format: "number" | "percent";
  description?: string;
}

export interface ChartSpec {
  chart_id: string;
  title: string;
  type: ChartType;
  sql: string;
  x: string;
  y: string;
  group_by?: string;
  limits?: Record<string, string | number>;
}

export interface FilterSpec {
  filter_id: string;
  label: string;
  type: "date_range" | "categorical" | "numeric_range";
  column: string;
  options: string[];
  min?: number | string;
  max?: number | string;
}

export interface InsightItem {
  insight_id: string;
  title: string;
  description: string;
  severity: "info" | "warning";
}

export interface DashboardSpec {
  dataset_id: string;
  detected_type: DatasetType;
  kpis: KPIItem[];
  charts: ChartSpec[];
  filters: FilterSpec[];
  insights: InsightItem[];
  version: number;
  created_at: string;
}

export interface ChartRunResponse {
  chart_id: string;
  title: string;
  type: ChartType;
  x_field: string;
  y_field: string;
  rows: Record<string, unknown>[];
}

export type FilterValues = Record<string, unknown>;

