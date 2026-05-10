# NetOps Command Center

NetOps Command Center is a network automation and NOC operations platform built for real infrastructure work: device inventory, active health checks, operational history, drift detection, dashboard visibility, Morning NOC reports, and optional local AI summaries.

The project is designed as a portfolio-ready system for network engineering, NOC operations, infrastructure monitoring, automation, and self-hosted tooling.

## Features

- Device inventory CRUD for hostname, IP, role, site, platform, owner, tags, connection type, TCP ports, HTTP URLs, SSH flag, and notes.
- Active health checks for ICMP ping, TCP ports, HTTP/HTTPS endpoints, and SSH availability.
- Status classification: `healthy`, `warning`, `critical`, and `unknown`.
- SQLite persistence with a structure that can move to PostgreSQL later.
- Check result history with run IDs.
- Drift detection for status changes, newly tracked services, and removed service checks.
- Dashboard summary API and React dashboard.
- Morning NOC Report export as Markdown.
- Optional Ollama summaries; AI is never required for the core app.
- Optional scheduled fleet checks.
- SSH-backed automation runbooks for diagnostics and controlled remediation.
- Automatic failed-check triage that can open incidents, run diagnostics, resolve recovered devices, and send webhook notifications.
- Config snapshot runbooks for Linux and Proxmox targets.
- Docker Compose deployment with backend, frontend, and persistent SQLite volume.

## Project Structure

```text
netops-command-center/
  backend/
    app/
      api/              # Versioned FastAPI routers
      core/             # Config, logging, exception handling, time helpers
      db/               # SQLAlchemy engine/session setup
      models/           # SQLAlchemy database models
      schemas/          # Pydantic request/response models
      services/         # Business logic, checks, drift, reports, AI, scheduler
      main.py           # FastAPI application entrypoint
    tests/
    Dockerfile
    requirements.txt
    .env.example
  frontend/
    src/
      lib/              # API client
      types/            # TypeScript API types
      main.tsx          # React dashboard
      styles.css
    Dockerfile
    nginx.conf
    package.json
  docker-compose.yml
```

## Local Backend Setup

```powershell
cd "C:\Dev\Repos\netops-command-center"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

## Local Frontend Setup

In a second terminal:

```powershell
cd "C:\Dev\Repos\netops-command-center\frontend"
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## Docker Compose

```powershell
cd "C:\Dev\Repos\netops-command-center"
docker compose up --build
```

Open:

```text
http://127.0.0.1:8080
```

API:

```text
http://127.0.0.1:8000/docs
```

The Compose deployment enables scheduled checks every 300 seconds by default. Local development leaves scheduling disabled unless you set `SCHEDULER_ENABLED=true`.

## Core API Routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | API health status |
| `GET` | `/api/v1/dashboard/summary` | Dashboard metrics, failed checks, drift, device statuses |
| `GET` | `/api/v1/devices` | List devices |
| `POST` | `/api/v1/devices` | Create device |
| `GET` | `/api/v1/devices/{device_id}` | Get one device |
| `PUT` | `/api/v1/devices/{device_id}` | Update device |
| `DELETE` | `/api/v1/devices/{device_id}` | Delete device |
| `GET` | `/api/v1/devices/export.csv` | Export inventory as CSV |
| `GET` | `/api/v1/devices/export.json` | Export inventory as JSON |
| `POST` | `/api/v1/devices/{device_id}/run-checks` | Run checks for one device |
| `GET` | `/api/v1/health-checks` | List check history |
| `POST` | `/api/v1/health-checks/run` | Run checks for active fleet |
| `GET` | `/api/v1/drift-events` | List detected operational drift |
| `GET` | `/api/v1/incidents` | List open and resolved operational incidents |
| `GET` | `/api/v1/reports/morning` | JSON Morning NOC Report |
| `GET` | `/api/v1/reports/morning.md` | Markdown Morning NOC Report |
| `GET` | `/api/v1/automation/runbooks` | List available automation runbooks |
| `GET` | `/api/v1/automation/runs` | List automation action history |
| `POST` | `/api/v1/automation/devices/{device_id}/diagnostics` | Run a safe diagnostic runbook over SSH |
| `POST` | `/api/v1/automation/devices/{device_id}/config-snapshot` | Collect a safe config snapshot over SSH |
| `POST` | `/api/v1/automation/triage` | Open incidents and run diagnostics for currently failed devices |
| `POST` | `/api/v1/automation/devices/{device_id}/restart-service` | Restart a validated systemd service |
| `POST` | `/api/v1/automation/devices/{device_id}/restart-container` | Restart a validated Docker container |

## Example Device

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/devices" `
  -ContentType "application/json" `
  -Body '{
    "hostname": "proxmox-media",
    "ip_address": "192.168.68.72",
    "role": "proxmox-host",
    "site": "home-lab",
    "platform": "Debian/Proxmox",
    "owner": "Brandon",
    "tags": ["proxmox", "critical", "homelab"],
    "connection_type": "icmp",
    "tcp_ports": [22, 8006],
    "http_urls": ["https://192.168.68.72:8006"],
    "ssh_enabled": true
  }'
```

Run checks:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/health-checks/run"
```

Export the inventory:

```powershell
Invoke-WebRequest "http://127.0.0.1:8000/api/v1/devices/export.csv" -OutFile ".\netops-inventory.csv"
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/devices/export.json"
```

Export the report:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/reports/morning.md"
```

## Import Brandon's Homelab Workbook

The repo includes a reusable importer for the homelab workbook. It merges rows by IP address, aggregates TCP ports and HTTP endpoints, avoids credential fields, and upserts through the FastAPI API so normal validation still applies.

```powershell
cd "C:\Dev\Repos\netops-command-center"
python .\scripts\import_inventory.py `
  --workbook "C:\Users\bratsu\Downloads\bratsu_network_inventory_updated.xlsx" `
  --api-base http://127.0.0.1:8000
```

Expected workbook result:

```text
Total source devices: 20
```

The current local inventory also includes Brandon's mini PC, bringing the active lab inventory to 21 devices.

## Source-Of-Truth Workflow

NetOps is intended to become the operational source of truth for the homelab:

1. Import or add devices with role, site, platform, tags, ports, URLs, SSH state, and notes.
2. Run fleet checks to keep current status attached to inventory instead of scattered notes.
3. Use drift events and incidents to track what changed and what needs follow-up.
4. Export CSV/JSON inventory before major maintenance, rebuilds, or documentation updates.
5. Keep secrets outside the repo in SSH agent, `.env`, or local host mapping files.

## Optional Ollama Summary

Set these in `backend/.env` or Docker Compose:

```text
AI_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

Then request:

```text
GET /api/v1/reports/morning?include_ai=true
```

If Ollama is unavailable, the app still generates the standard operational report.

## Automation Engine

NetOps includes an SSH-backed automation engine. It intentionally does not expose arbitrary shell execution from the UI. Actions run through named runbooks or validated remediation parameters, and every command result is stored in action history.

Current runbooks:

- `linux_basic_diagnostics`: uptime, disk, memory, failed services, network listeners, recent warning/error logs.
- `docker_diagnostics`: Docker container state, resource usage, Docker service logs.
- `proxmox_diagnostics`: Proxmox version, storage, VM list, LXC list, failed services.
- `linux_config_snapshot`: system identity, network config, enabled services, failed services, scheduled tasks, and key config paths.
- `proxmox_config_snapshot`: Proxmox version, storage, VM inventory, LXC inventory, cluster status, and selected config references.

Environment settings:

| Variable | Purpose | Default |
| --- | --- | --- |
| `AUTOMATION_DEFAULT_SSH_USER` | Default SSH username for runbooks | `root` |
| `AUTOMATION_SSH_TIMEOUT_SECONDS` | SSH connection/command timeout | `12` |
| `AUTOMATION_REQUESTED_BY` | Stored actor label in action history | `netops-local` |
| `AUTOMATION_HOST_CONFIG_PATH` | Local SSH/Proxmox target map | `./config/automation_hosts.local.json` |
| `AUTO_TRIAGE_ENABLED` | Run triage after scheduled fleet checks | `false` |
| `NOTIFICATION_WEBHOOK_URL` | Optional webhook endpoint for triage notifications | empty |

Host mappings live in `backend/config/automation_hosts.local.json`, which is ignored by git. The example file `backend/config/automation_hosts.example.json` shows the structure. Supported methods:

- `ssh`: connect directly to the device with a configured username and identity file.
- `proxmox_lxc`: connect to the Proxmox host and run commands inside an LXC with `pct exec`.

This lets NetOps automate containers through the Proxmox host without installing a separate SSH key in every container.

Run diagnostics from PowerShell:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/automation/devices/1/diagnostics?runbook_id=linux_basic_diagnostics" `
  -ContentType "application/json" `
  -Body '{}'
```

Collect a config snapshot:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/automation/devices/1/config-snapshot" `
  -ContentType "application/json" `
  -Body '{}'
```

Run fleet checks and immediately triage failures:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/health-checks/run?auto_triage=true"
```

Run triage against the current dashboard state without starting a new check run:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/automation/triage"
```

Restart a systemd service:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/automation/devices/1/restart-service" `
  -ContentType "application/json" `
  -Body '{"service_name":"nginx"}'
```

Restart a Docker container:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/automation/devices/1/restart-container" `
  -ContentType "application/json" `
  -Body '{"container_name":"open-webui"}'
```

Operational notes:

- SSH keys must already be configured on the workstation or server running the backend.
- Commands run with `BatchMode=yes`; the API will not pause for passwords.
- Remediation parameters only allow conservative service/container name characters.
- Triage only runs approved diagnostic runbooks; it does not restart services or containers automatically.
- Incidents are opened for warning or critical devices and resolved when later checks report the device as healthy.
- Store secrets in your OS/SSH agent or vault, not in this repository.

## Tests and Builds

Backend:

```powershell
cd "C:\Dev\Repos\netops-command-center\backend"
python -m pytest
```

Frontend:

```powershell
cd "C:\Dev\Repos\netops-command-center\frontend"
npm run build
```

## Portfolio Talking Points

- Models a real NOC workflow: inventory, checks, history, drift, dashboard, and report generation.
- Adds practical automation: diagnostics, config snapshots, incident creation/resolution, and notification hooks.
- Uses backend service boundaries that can grow into Netmiko, NAPALM, Paramiko, Redis/RQ, PostgreSQL, and richer alerting.
- Keeps AI optional and local-first with Ollama support.
- Demonstrates practical API design, validation, logging, persistence, and Docker deployment.
- Designed for self-hosted homelab and small-business managed IT scenarios.
