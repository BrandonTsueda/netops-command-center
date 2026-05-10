import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, AlertTriangle, Archive, CheckCircle2, Clock, FileText, Plus, RefreshCw, Server, Shield, Stethoscope, Trash2, XCircle } from "lucide-react";
import { api } from "./lib/api";
import type { AutomationRun, DashboardSummary, Device, DeviceInput, Incident, MorningReport, Status } from "./types/api";
import "./styles.css";

const emptyDevice: DeviceInput = {
  hostname: "",
  ip_address: "",
  role: "server",
  site: "home-lab",
  platform: "",
  owner: "",
  tags: [],
  connection_type: "icmp",
  tcp_ports: [22],
  http_urls: [],
  ssh_enabled: true,
  notes: "",
  is_active: true
};

function App() {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [form, setForm] = useState<DeviceInput>(emptyDevice);
  const [report, setReport] = useState<MorningReport | null>(null);
  const [automationRuns, setAutomationRuns] = useState<AutomationRun[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [sshUsername, setSshUsername] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setError(null);
    const [dashboardData, deviceData, automationData, incidentData] = await Promise.all([
      api.dashboard(),
      api.devices(),
      api.automationRuns(),
      api.incidents()
    ]);
    setDashboard(dashboardData);
    setDevices(deviceData.items);
    setAutomationRuns(automationData.items);
    setIncidents(incidentData.items);
  }

  useEffect(() => {
    load().catch((err: Error) => setError(err.message));
  }, []);

  async function saveDevice(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createDevice(form);
      setForm(emptyDevice);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function runChecks() {
    setBusy(true);
    setError(null);
    try {
      await api.runFleetChecks();
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function runChecksAndTriage() {
    setBusy(true);
    setError(null);
    try {
      await api.runFleetChecks(true);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteDevice(device: Device) {
    setBusy(true);
    setError(null);
    try {
      await api.deleteDevice(device.id);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function generateReport() {
    setBusy(true);
    setError(null);
    try {
      setReport(await api.morningReport(false));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function runDiagnostics(device: Device) {
    setBusy(true);
    setError(null);
    try {
      const runbookId = device.role.includes("proxmox") ? "proxmox_diagnostics" : "linux_basic_diagnostics";
      await api.runDiagnostics(device.id, runbookId, sshUsername || undefined);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function collectSnapshot(device: Device) {
    setBusy(true);
    setError(null);
    try {
      await api.collectConfigSnapshot(device.id, sshUsername || undefined);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const statusCards = useMemo(() => {
    const base = dashboard ?? { healthy: 0, warning: 0, critical: 0, unknown: 0, total_devices: 0, active_devices: 0 };
    return [
      { label: "Healthy", value: base.healthy, status: "healthy" as Status, icon: CheckCircle2 },
      { label: "Warning", value: base.warning, status: "warning" as Status, icon: AlertTriangle },
      { label: "Critical", value: base.critical, status: "critical" as Status, icon: XCircle },
      { label: "Unknown", value: base.unknown, status: "unknown" as Status, icon: Clock }
    ];
  }, [dashboard]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Network Automation / NOC Operations</p>
          <h1>NetOps Command Center</h1>
        </div>
        <div className="topbar-actions">
          <a className="secondary button-link" href="/api/v1/devices/export.csv" target="_blank" rel="noreferrer">
            <FileText size={18} />
            Export CSV
          </a>
          <button className="secondary" onClick={runChecks} disabled={busy}>
            <RefreshCw size={18} />
            Check
          </button>
          <button className="primary" onClick={runChecksAndTriage} disabled={busy}>
            <Stethoscope size={18} />
            Check + Triage
          </button>
        </div>
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="source-strip">
        <div>
          <p className="eyebrow">Source Of Truth</p>
          <h2>Track devices, checks, incidents, automation runs, and exports from one local command surface.</h2>
        </div>
        <div className="source-actions">
          <a href="/api/v1/devices/export.json" target="_blank" rel="noreferrer">JSON inventory</a>
          <a href="/api/v1/reports/morning.md" target="_blank" rel="noreferrer">Morning report</a>
          <a href="/api/v1/automation/runs?limit=100" target="_blank" rel="noreferrer">Automation history</a>
        </div>
      </section>

      <section className="metrics">
        <div className="metric total">
          <Server size={22} />
          <span>Total Devices</span>
          <strong>{dashboard?.total_devices ?? 0}</strong>
        </div>
        <div className="metric total">
          <Shield size={22} />
          <span>Active Devices</span>
          <strong>{dashboard?.active_devices ?? 0}</strong>
        </div>
        {statusCards.map((card) => {
          const Icon = card.icon;
          return (
            <div className={`metric ${card.status}`} key={card.label}>
              <Icon size={22} />
              <span>{card.label}</span>
              <strong>{card.value}</strong>
            </div>
          );
        })}
      </section>

      <section className="workspace">
        <div className="panel inventory-panel">
          <div className="panel-header">
            <h2>Device Inventory</h2>
            <span>{devices.length} devices</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Device</th>
                  <th>Role</th>
                  <th>Site</th>
                  <th>Checks</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {devices.map((device) => {
                  const status = dashboard?.devices.find((item) => item.device_id === device.id);
                  return (
                    <tr key={device.id}>
                      <td>
                        <strong>{device.hostname}</strong>
                        <small>{device.ip_address}</small>
                      </td>
                      <td>{device.role}</td>
                      <td>{device.site}</td>
                      <td>{[...device.tcp_ports.map((port) => `:${port}`), ...device.http_urls].join(", ") || "icmp"}</td>
                      <td><StatusPill status={status?.status ?? "unknown"} /></td>
                      <td>
                        <button className="icon-button" onClick={() => runDiagnostics(device)} disabled={busy} title="Collect diagnostics">
                          <Stethoscope size={16} />
                        </button>
                        <button className="icon-button" onClick={() => collectSnapshot(device)} disabled={busy} title="Collect config snapshot">
                          <Archive size={16} />
                        </button>
                        <button className="icon-button danger" onClick={() => deleteDevice(device)} disabled={busy} title="Delete device">
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <form className="panel form-panel" onSubmit={saveDevice}>
          <div className="panel-header">
            <h2>Add Device</h2>
            <Plus size={20} />
          </div>
          <label>
            Hostname
            <input value={form.hostname} onChange={(event) => setForm({ ...form, hostname: event.target.value })} required />
          </label>
          <label>
            IP Address
            <input value={form.ip_address} onChange={(event) => setForm({ ...form, ip_address: event.target.value })} required />
          </label>
          <div className="split">
            <label>
              Role
              <input value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} />
            </label>
            <label>
              Site
              <input value={form.site} onChange={(event) => setForm({ ...form, site: event.target.value })} />
            </label>
          </div>
          <label>
            TCP Ports
            <input
              value={form.tcp_ports.join(",")}
              onChange={(event) => setForm({ ...form, tcp_ports: parsePorts(event.target.value) })}
              placeholder="22,80,443"
            />
          </label>
          <label>
            HTTP URLs
            <input
              value={form.http_urls.join(",")}
              onChange={(event) => setForm({ ...form, http_urls: parseList(event.target.value) })}
              placeholder="https://host.local/health"
            />
          </label>
          <label>
            Tags
            <input
              value={form.tags.join(",")}
              onChange={(event) => setForm({ ...form, tags: parseList(event.target.value) })}
              placeholder="proxmox,critical,edge"
            />
          </label>
          <label className="check-row">
            <input type="checkbox" checked={form.ssh_enabled} onChange={(event) => setForm({ ...form, ssh_enabled: event.target.checked })} />
            SSH availability
          </label>
          <button className="primary full" disabled={busy}>
            <Plus size={18} />
            Add Device
          </button>
        </form>
      </section>

      <section className="lower-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Failed Checks</h2>
            <Activity size={20} />
          </div>
          <FeedList items={dashboard?.failed_checks.map((check) => ({
            title: `${check.check_type.toUpperCase()} ${check.target}`,
            detail: check.message,
            status: check.status
          })) ?? []} />
        </div>
        <div className="panel">
          <div className="panel-header">
            <h2>Recent Drift</h2>
            <AlertTriangle size={20} />
          </div>
          <FeedList items={dashboard?.recent_drift.map((event) => ({
            title: event.title,
            detail: event.description,
            status: event.severity === "critical" ? "critical" : event.severity === "warning" ? "warning" : "info"
          })) ?? []} />
        </div>
        <div className="panel report-panel">
          <div className="panel-header">
            <h2>Morning Report</h2>
            <button className="secondary" onClick={generateReport} disabled={busy}>
              <FileText size={16} />
              Generate
            </button>
          </div>
          <pre>{report?.markdown ?? "No report generated yet."}</pre>
        </div>
        <div className="panel automation-panel">
          <div className="panel-header">
            <h2>Automation Runs</h2>
            <Stethoscope size={20} />
          </div>
          <label>
            SSH User
            <input value={sshUsername} onChange={(event) => setSshUsername(event.target.value)} placeholder="auto from host config" />
          </label>
          <FeedList items={automationRuns.map((run) => ({
            title: `${run.command_id} on ${deviceName(run.device_id, devices)}`,
            detail: automationDetail(run),
            status: automationStatus(run)
          }))} />
        </div>
        <div className="panel">
          <div className="panel-header">
            <h2>Incidents</h2>
            <AlertTriangle size={20} />
          </div>
          <FeedList items={incidents.map((incident) => ({
            title: incident.title,
            detail: `${incident.status} - ${incident.description || "No details"}`,
            status: incident.status === "resolved" ? "healthy" : incident.severity
          }))} />
        </div>
      </section>
    </main>
  );
}

function StatusPill({ status }: { status: Status }) {
  return <span className={`status-pill ${status}`}>{status}</span>;
}

function FeedList({ items }: { items: { title: string; detail: string; status: Status | string }[] }) {
  if (!items.length) {
    return <div className="empty">No entries</div>;
  }
  return (
    <ul className="feed">
      {items.map((item, index) => (
        <li key={`${item.title}-${index}`}>
          <StatusPill status={(item.status as Status) || "unknown"} />
          <div>
            <strong>{item.title}</strong>
            <small>{item.detail}</small>
          </div>
        </li>
      ))}
    </ul>
  );
}

function parseList(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function parsePorts(value: string): number[] {
  return parseList(value).map(Number).filter((port) => Number.isInteger(port) && port > 0 && port <= 65535);
}

function deviceName(deviceId: number, devices: Device[]): string {
  return devices.find((device) => device.id === deviceId)?.hostname ?? `device ${deviceId}`;
}

function automationStatus(run: AutomationRun): Status {
  if (run.status === "completed") {
    return "healthy";
  }
  if (run.status === "configuration_required" || run.status === "running") {
    return "info";
  }
  return "critical";
}

function automationDetail(run: AutomationRun): string {
  const exit = run.exit_code !== null && run.exit_code !== undefined ? `, exit ${run.exit_code}` : "";
  const reason = run.stderr ? ` - ${run.stderr.trim().slice(0, 180)}` : "";
  return `${run.status}${exit} - ${run.command}${reason}`;
}

createRoot(document.getElementById("root")!).render(<App />);
