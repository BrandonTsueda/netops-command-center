import logging
import json
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError
from app.core.time import utc_now
from app.models.automation_run import AutomationRun
from app.schemas.automation import AutomationRunRead, AutomationRunbookResult, RunbookRead
from app.services.device_service import get_device

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass(frozen=True)
class RunbookCommand:
    id: str
    command: str


@dataclass(frozen=True)
class Runbook:
    id: str
    name: str
    description: str
    action_type: str
    commands: tuple[RunbookCommand, ...]


RUNBOOKS: dict[str, Runbook] = {
    "linux_basic_diagnostics": Runbook(
        id="linux_basic_diagnostics",
        name="Linux Basic Diagnostics",
        description="Collect uptime, disk, memory, failed services, network listeners, and recent warning/error logs.",
        action_type="diagnostics",
        commands=(
            RunbookCommand("uptime", "uptime || true"),
            RunbookCommand("disk", "df -h || true"),
            RunbookCommand("memory", "free -m || true"),
            RunbookCommand("failed_services", "systemctl --failed --no-pager || true"),
            RunbookCommand("listeners", "ss -tulpen || true"),
            RunbookCommand("recent_warnings", "journalctl -p warning -n 80 --no-pager || true"),
        ),
    ),
    "docker_diagnostics": Runbook(
        id="docker_diagnostics",
        name="Docker Diagnostics",
        description="Collect Docker container state, resource usage, and recent Docker service logs.",
        action_type="diagnostics",
        commands=(
            RunbookCommand("docker_ps", "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}' || true"),
            RunbookCommand("docker_stats", "docker stats --no-stream || true"),
            RunbookCommand("docker_events", "journalctl -u docker -n 80 --no-pager || true"),
        ),
    ),
    "proxmox_diagnostics": Runbook(
        id="proxmox_diagnostics",
        name="Proxmox Diagnostics",
        description="Collect Proxmox node status, storage, VM/LXC status, and cluster service health.",
        action_type="diagnostics",
        commands=(
            RunbookCommand("pve_version", "pveversion || true"),
            RunbookCommand("storage", "pvesm status || true"),
            RunbookCommand("vms", "qm list || true"),
            RunbookCommand("containers", "pct list || true"),
            RunbookCommand("cluster_services", "systemctl --failed --no-pager || true"),
        ),
    ),
    "linux_config_snapshot": Runbook(
        id="linux_config_snapshot",
        name="Linux Config Snapshot",
        description="Collect a read-only configuration snapshot for incident notes or change review.",
        action_type="backup",
        commands=(
            RunbookCommand("system_identity", "hostname; date -Iseconds; uname -a; uptime || true"),
            RunbookCommand("network_config", "ip -brief addr; ip route || true"),
            RunbookCommand("enabled_services", "systemctl list-unit-files --state=enabled --no-pager || true"),
            RunbookCommand("failed_services", "systemctl --failed --no-pager || true"),
            RunbookCommand("scheduled_tasks", "crontab -l 2>/dev/null || true; ls -la /etc/cron.d 2>/dev/null || true"),
            RunbookCommand("key_configs", "ls -la /etc/systemd/system 2>/dev/null || true; ls -la /etc/nginx/sites-enabled 2>/dev/null || true"),
        ),
    ),
    "proxmox_config_snapshot": Runbook(
        id="proxmox_config_snapshot",
        name="Proxmox Config Snapshot",
        description="Collect read-only Proxmox node, VM, LXC, and storage configuration.",
        action_type="backup",
        commands=(
            RunbookCommand("node_identity", "hostname; date -Iseconds; pveversion || true"),
            RunbookCommand("storage", "pvesm status || true"),
            RunbookCommand("vm_configs", "qm list; for id in $(qm list | awk 'NR>1 {print $1}'); do echo === VM $id ===; qm config $id; done || true"),
            RunbookCommand("lxc_configs", "pct list; for id in $(pct list | awk 'NR>1 {print $1}'); do echo === CT $id ===; pct config $id; done || true"),
            RunbookCommand("failed_services", "systemctl --failed --no-pager || true"),
        ),
    ),
}


def list_runbooks() -> list[RunbookRead]:
    return [
        RunbookRead(
            id=runbook.id,
            name=runbook.name,
            description=runbook.description,
            action_type=runbook.action_type,
            commands=[command.id for command in runbook.commands],
        )
        for runbook in RUNBOOKS.values()
    ]


def list_automation_runs(db: Session, device_id: int | None = None, limit: int = 100) -> tuple[list[AutomationRunRead], int]:
    statement = select(AutomationRun)
    count_statement = select(func.count()).select_from(AutomationRun)
    if device_id is not None:
        statement = statement.where(AutomationRun.device_id == device_id)
        count_statement = count_statement.where(AutomationRun.device_id == device_id)
    total = db.scalar(count_statement) or 0
    rows = db.scalars(statement.order_by(AutomationRun.started_at.desc()).limit(limit)).all()
    return [AutomationRunRead.model_validate(row) for row in rows], total


def run_diagnostics(
    db: Session,
    device_id: int,
    runbook_id: str = "linux_basic_diagnostics",
    ssh_username: str | None = None,
) -> AutomationRunbookResult:
    runbook = _get_runbook(runbook_id)
    return _run_runbook(db=db, device_id=device_id, runbook=runbook, ssh_username=ssh_username)


def restart_service(db: Session, device_id: int, service_name: str, ssh_username: str | None = None) -> AutomationRunbookResult:
    command = RunbookCommand("restart_service", f"sudo systemctl restart {service_name} && systemctl is-active {service_name}")
    runbook = Runbook(
        id=f"restart_service:{service_name}",
        name=f"Restart {service_name}",
        description="Restart one validated systemd service and confirm it is active.",
        action_type="remediation",
        commands=(command,),
    )
    return _run_runbook(db=db, device_id=device_id, runbook=runbook, ssh_username=ssh_username)


def restart_container(db: Session, device_id: int, container_name: str, ssh_username: str | None = None) -> AutomationRunbookResult:
    command = RunbookCommand("restart_container", f"docker restart {container_name} && docker ps --filter name={container_name}")
    runbook = Runbook(
        id=f"restart_container:{container_name}",
        name=f"Restart container {container_name}",
        description="Restart one validated Docker container and show the resulting container state.",
        action_type="remediation",
        commands=(command,),
    )
    return _run_runbook(db=db, device_id=device_id, runbook=runbook, ssh_username=ssh_username)


def collect_config_snapshot(db: Session, device_id: int, ssh_username: str | None = None) -> AutomationRunbookResult:
    device = get_device(db, device_id)
    runbook_id = "proxmox_config_snapshot" if "proxmox" in device.role.lower() else "linux_config_snapshot"
    return _run_runbook(db=db, device_id=device_id, runbook=_get_runbook(runbook_id), ssh_username=ssh_username)


def _run_runbook(db: Session, device_id: int, runbook: Runbook, ssh_username: str | None = None) -> AutomationRunbookResult:
    if shutil.which("ssh") is None:
        raise ConflictError("OpenSSH client is not available on this workstation.")

    device = get_device(db, device_id)
    username = ssh_username or settings.automation_default_ssh_user
    runs = []

    for command in runbook.commands:
        row = _execute_ssh_command(
            db=db,
            device_id=device.id,
            host=device.ip_address,
            username=username,
            runbook=runbook,
            command=command,
        )
        runs.append(row)

    status = "completed" if all(row.status == "completed" for row in runs) else "failed"
    return AutomationRunbookResult(
        device_id=device.id,
        hostname=device.hostname,
        runbook_id=runbook.id,
        status=status,
        runs=[AutomationRunRead.model_validate(row) for row in runs],
    )


def _execute_ssh_command(
    db: Session,
    device_id: int,
    host: str,
    username: str,
    runbook: Runbook,
    command: RunbookCommand,
) -> AutomationRun:
    started = utc_now()
    row = AutomationRun(
        device_id=device_id,
        runbook_id=runbook.id,
        action_type=runbook.action_type,
        command_id=command.id,
        command=command.command,
        status="running",
        requested_by=settings.automation_requested_by,
        started_at=started,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    host_config = _host_config(host)
    ssh_command = _build_ssh_command(host=host, username=username, command=command.command, host_config=host_config)

    logger.info("Running automation command id=%s device_id=%s runbook=%s", command.id, device_id, runbook.id)
    start_counter = time.perf_counter()
    try:
        result = subprocess.run(
            ssh_command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=settings.automation_ssh_timeout_seconds + 8,
        )
        row.exit_code = result.returncode
        row.stdout = _trim_output(result.stdout)
        row.stderr = _trim_output(result.stderr)
        row.status = _classify_result_status(result.returncode, result.stderr)
    except subprocess.TimeoutExpired as exc:
        row.exit_code = None
        row.stdout = _trim_output(exc.stdout or "")
        row.stderr = _trim_output((exc.stderr or "") + "\nSSH command timed out.")
        row.status = "timeout"
    except OSError as exc:
        row.exit_code = None
        row.stdout = ""
        row.stderr = str(exc)
        row.status = "failed"
    finally:
        row.completed_at = utc_now()
        row.duration_ms = int((time.perf_counter() - start_counter) * 1000)
        db.commit()
        db.refresh(row)

    return row


def _get_runbook(runbook_id: str) -> Runbook:
    runbook = RUNBOOKS.get(runbook_id)
    if not runbook:
        raise ConflictError(f"Unknown runbook: {runbook_id}")
    return runbook


def _trim_output(value: str | bytes | None, limit: int = 12000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[output truncated]..."


def _classify_result_status(exit_code: int, stderr: str) -> str:
    if exit_code == 0:
        return "completed"
    lowered = stderr.lower()
    if "permission denied" in lowered or "no such identity" in lowered:
        return "configuration_required"
    if "could not resolve hostname" in lowered or "host key verification failed" in lowered:
        return "configuration_required"
    return "failed"


def _host_config(host: str) -> dict:
    try:
        with open(settings.automation_host_config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.warning("Automation host config is invalid JSON: %s", settings.automation_host_config_path)
        return {}
    return config.get("hosts", {}).get(host, {})


def _build_ssh_command(host: str, username: str, command: str, host_config: dict) -> list[str]:
    method = host_config.get("method", "ssh")
    resolved_host = host_config.get("host", host)
    resolved_user = host_config.get("user", username)
    identity_file = host_config.get("identity_file")
    port = str(host_config.get("port", 22))

    remote_command = command
    if method == "proxmox_lxc":
        container_id = str(host_config["container_id"])
        remote_command = f"pct exec {container_id} -- bash -lc {shlex.quote(command)}"
        resolved_host = host_config["proxmox_host"]
        resolved_user = host_config.get("proxmox_user", "root")
        identity_file = host_config.get("proxmox_identity_file", identity_file)
        port = str(host_config.get("proxmox_port", 22))

    ssh_command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={settings.automation_ssh_timeout_seconds}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-p",
        port,
    ]
    if identity_file:
        ssh_command.extend(["-i", identity_file])
    ssh_command.extend([f"{resolved_user}@{resolved_host}", remote_command])
    return ssh_command
