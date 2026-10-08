import type { CompanyContext, Execution, ProcurementRequest, Recommendation, RequestDetail } from "./types";

const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `SourcePilot API returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getContext: () => request<CompanyContext>("/context"),
  listRequests: () => request<ProcurementRequest[]>("/requests"),
  getRequest: (id: string) => request<RequestDetail>(`/requests/${id}`),
  getExecution: (workflowId: string) => request<Execution>(`/workflows/${workflowId}`),
  createRequest: (text: string) =>
    request<ProcurementRequest>("/requests", {
      method: "POST",
      body: JSON.stringify({ request: text }),
    }),
  review: (id: string, decision: "approved" | "rejected", note?: string) =>
    request<Recommendation>(`/requests/${id}/recommendation/review`, {
      method: "POST",
      body: JSON.stringify({ decision, note: note || null }),
    }),
};
