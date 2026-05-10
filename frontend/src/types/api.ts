export type Status = "healthy" | "warning" | "critical" | "unknown" | "info";

export interface Device {
  id: number;
  hostname: string;
  ip_address: string;
  role: string;
  site: string;
  platform?: string | null;
  owner?: string | null;
  tags: string[];
  connection_type: string;
  tcp_ports: number[];
  http_urls: string[];
  ssh_enabled: boolean;
  notes?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DeviceInput {
  hostname: string;
  ip_address: string;
  role: string;
  site: string;
  platform: string;
  owner: string;
  tags: string[];
  connection_type: string;
  tcp_ports: number[];
  http_urls: string[];
  ssh_enabled: boolean;
  notes: string;
  is_active: boolean;
}

export interface HealthCheck {
  id: number;
  device_id: number;
  check_type: string;
  target: string;
  status: Status;
  latency_ms?: number | null;
  message: string;
  observed_value?: string | null;
  run_id?: string | null;
  created_at: string;
}

export interface DriftEvent {
  id: number;
  device_id: number;
  event_type: string;
  severity: string;
  title: string;
  description: string;
  previous_value?: string | null;
  current_value?: string | null;
  created_at: string;
}

export interface DeviceStatusSummary {
  device_id: number;
  hostname: string;
  ip_address: string;
  role: string;
  site: string;
  status: Status;
  last_check_at?: string | null;
  failed_checks: number;
  total_checks: number;
  availability_percent: number;
}

export interface DashboardSummary {
  total_devices: number;
  active_devices: number;
  healthy: number;
  warning: number;
  critical: number;
  unknown: number;
  failed_checks: HealthCheck[];
  recent_drift: DriftEvent[];
  devices: DeviceStatusSummary[];
}

export interface FleetCheckRun {
  run_id: string;
  checked_devices: number;
  healthy: number;
  warning: number;
  critical: number;
  unknown: number;
}

export interface MorningReport {
  generated_at: string;
  markdown: string;
  ai_summary?: string | null;
}

export interface AutomationRun {
  id: number;
  device_id: number;
  runbook_id: string;
  action_type: string;
  command_id: string;
  command: string;
  status: string;
  exit_code?: number | null;
  stdout: string;
  stderr: string;
  requested_by: string;
  started_at: string;
  completed_at?: string | null;
  duration_ms?: number | null;
}

export interface AutomationRunbookResult {
  device_id: number;
  hostname: string;
  runbook_id: string;
  status: string;
  runs: AutomationRun[];
}

export interface TriageResult {
  status: string;
  checked_devices: number;
  affected_devices: number;
  incidents_opened: number;
  incidents_resolved: number;
  automation_results: AutomationRunbookResult[];
  notification_sent: boolean;
}

export interface Incident {
  id: number;
  device_id: number;
  severity: string;
  title: string;
  description: string;
  status: string;
  opened_at: string;
  resolved_at?: string | null;
}
