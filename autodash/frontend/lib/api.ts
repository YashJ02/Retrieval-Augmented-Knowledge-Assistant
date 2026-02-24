import type { ChartRunResponse, DashboardSpec, FilterValues } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // No-op: keep fallback message.
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function uploadDataset(file: File): Promise<{ dataset_id: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/v1/datasets/upload`, {
    method: "POST",
    body: formData
  });
  return parseResponse<{ dataset_id: string }>(response);
}

export async function getDashboard(datasetId: string): Promise<DashboardSpec> {
  const response = await fetch(`${API_BASE_URL}/api/v1/datasets/${datasetId}/dashboard`, {
    method: "GET",
    cache: "no-store"
  });
  return parseResponse<DashboardSpec>(response);
}

export async function generateDashboard(datasetId: string): Promise<DashboardSpec> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/datasets/${datasetId}/dashboard/generate`,
    {
      method: "POST"
    }
  );
  return parseResponse<DashboardSpec>(response);
}

export async function runChart(
  datasetId: string,
  chartId: string,
  filters: FilterValues
): Promise<ChartRunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/datasets/${datasetId}/chart/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chart_id: chartId,
      filters
    })
  });
  return parseResponse<ChartRunResponse>(response);
}

