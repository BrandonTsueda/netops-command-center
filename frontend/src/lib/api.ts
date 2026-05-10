import type { AutomationRun, AutomationRunbookResult, DashboardSummary, Device, DeviceInput, FleetCheckRun, Incident, MorningReport, TriageResult } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof body.detail === "string" ? body.detail : "Request failed");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  dashboard: () => request<DashboardSummary>("/api/v1/dashboard/summary"),
  devices: () => request<{ items: Device[]; total: number }>("/api/v1/devices"),
  createDevice: (payload: DeviceInput) =>
    request<Device>("/api/v1/devices", { method: "POST", body: JSON.stringify(payload) }),
  updateDevice: (id: number, payload: Partial<DeviceInput>) =>
    request<Device>(`/api/v1/devices/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteDevice: (id: number) => request<void>(`/api/v1/devices/${id}`, { method: "DELETE" }),
  runFleetChecks: (autoTriage = false) => request<FleetCheckRun>(`/api/v1/health-checks/run?auto_triage=${autoTriage}`, { method: "POST" }),
  morningReport: (includeAi = false) => request<MorningReport>(`/api/v1/reports/morning?include_ai=${includeAi}`),
  automationRuns: () => request<{ items: AutomationRun[]; total: number }>("/api/v1/automation/runs?limit=20"),
  incidents: () => request<{ items: Incident[]; total: number }>("/api/v1/incidents?limit=20"),
  runDiagnostics: (deviceId: number, runbookId = "linux_basic_diagnostics", sshUsername?: string) =>
    request<AutomationRunbookResult>(`/api/v1/automation/devices/${deviceId}/diagnostics?runbook_id=${runbookId}`, {
      method: "POST",
      body: JSON.stringify(sshUsername ? { ssh_username: sshUsername } : {})
    }),
  collectConfigSnapshot: (deviceId: number, sshUsername?: string) =>
    request<AutomationRunbookResult>(`/api/v1/automation/devices/${deviceId}/config-snapshot`, {
      method: "POST",
      body: JSON.stringify(sshUsername ? { ssh_username: sshUsername } : {})
    }),
  triage: () => request<TriageResult>("/api/v1/automation/triage", { method: "POST" })
};
