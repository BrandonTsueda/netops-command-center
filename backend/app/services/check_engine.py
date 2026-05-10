import asyncio
import json
import logging
import platform
import socket
import subprocess
import time
from dataclasses import dataclass
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.check_result import CheckResult
from app.models.device import Device
from app.schemas.health_check import DeviceCheckRun, FleetCheckRun, HealthCheckRead
from app.services.device_service import _load_list, get_device
from app.services.drift_service import record_drift_for_run

logger = logging.getLogger(__name__)
settings = get_settings()

STATUS_RANK = {"healthy": 0, "unknown": 1, "warning": 2, "critical": 3}


@dataclass
class ProbeResult:
    check_type: str
    target: str
    status: str
    latency_ms: int | None
    message: str
    observed_value: str | None = None


def _classify_overall(results: list[ProbeResult]) -> str:
    if not results:
        return "unknown"
    return max((result.status for result in results), key=lambda status: STATUS_RANK.get(status, 1))


def _ping_command(target: str) -> list[str]:
    if platform.system().lower() == "windows":
        return ["ping", "-n", "1", "-w", str(int(settings.ping_timeout_seconds * 1000)), target]
    return ["ping", "-c", "1", "-W", str(max(1, int(settings.ping_timeout_seconds))), target]


async def ping_check(target: str) -> ProbeResult:
    started = time.perf_counter()
    try:
        process = await asyncio.to_thread(
            subprocess.run,
            _ping_command(target),
            capture_output=True,
            text=True,
            timeout=settings.ping_timeout_seconds + 1,
        )
        latency = int((time.perf_counter() - started) * 1000)
        if process.returncode == 0:
            return ProbeResult("ping", target, "healthy", latency, "ICMP ping successful", process.stdout[-500:])
        return ProbeResult("ping", target, "critical", latency, "ICMP ping failed", process.stderr[-500:] or process.stdout[-500:])
    except (subprocess.TimeoutExpired, OSError) as exc:
        return ProbeResult("ping", target, "critical", None, f"ICMP ping error: {exc}")


async def tcp_check(host: str, port: int, check_type: str = "tcp") -> ProbeResult:
    target = f"{host}:{port}"
    started = time.perf_counter()
    try:
        await asyncio.wait_for(asyncio.to_thread(_connect_socket, host, port, settings.tcp_timeout_seconds), settings.tcp_timeout_seconds + 0.5)
        latency = int((time.perf_counter() - started) * 1000)
        return ProbeResult(check_type, target, "healthy", latency, f"TCP port {port} is open")
    except (TimeoutError, OSError, asyncio.TimeoutError) as exc:
        latency = int((time.perf_counter() - started) * 1000)
        return ProbeResult(check_type, target, "critical", latency, f"TCP port {port} is not reachable: {exc}")


def _connect_socket(host: str, port: int, timeout: float) -> None:
    with socket.create_connection((host, port), timeout=timeout):
        return


async def http_check(url: str) -> ProbeResult:
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds, verify=False) as client:
            response = await client.get(url)
        latency = int((time.perf_counter() - started) * 1000)
        if response.status_code < 400:
            return ProbeResult("http", url, "healthy", latency, f"HTTP {response.status_code}", str(response.status_code))
        if response.status_code in {401, 403}:
            return ProbeResult(
                "http",
                url,
                "healthy",
                latency,
                f"HTTP {response.status_code}; protected endpoint is reachable",
                str(response.status_code),
            )
        if response.status_code < 500:
            return ProbeResult("http", url, "warning", latency, f"HTTP returned client error {response.status_code}", str(response.status_code))
        return ProbeResult("http", url, "critical", latency, f"HTTP returned server error {response.status_code}", str(response.status_code))
    except httpx.HTTPError as exc:
        latency = int((time.perf_counter() - started) * 1000)
        return ProbeResult("http", url, "critical", latency, f"HTTP check failed: {exc}")


async def run_device_checks(db: Session, device_id: int, run_id: str | None = None) -> DeviceCheckRun:
    device = get_device(db, device_id)
    run_id = run_id or uuid4().hex
    previous_results = _latest_results_by_target(db, device.id)

    probes: list[ProbeResult] = []
    if device.connection_type in {"icmp", "agent", "manual"}:
        probes.append(await ping_check(device.ip_address))

    tcp_ports = _load_list(device.tcp_ports)
    probes.extend(await asyncio.gather(*(tcp_check(device.ip_address, int(port)) for port in tcp_ports)))

    if device.ssh_enabled and 22 not in [int(port) for port in tcp_ports]:
        probes.append(await tcp_check(device.ip_address, 22, "ssh"))

    http_urls = _load_list(device.http_urls)
    probes.extend(await asyncio.gather(*(http_check(url) for url in http_urls)))

    if not probes:
        probes.append(ProbeResult("inventory", device.ip_address, "unknown", None, "No active checks are configured for this device"))

    saved = _save_probe_results(db, device, probes, run_id)
    record_drift_for_run(db, device=device, previous_results=previous_results, current_results=saved)
    overall = _classify_overall(probes)

    return DeviceCheckRun(
        device_id=device.id,
        hostname=device.hostname,
        overall_status=overall,
        run_id=run_id,
        results=[HealthCheckRead.model_validate(result) for result in saved],
    )


async def run_fleet_checks(db: Session, active_only: bool = True) -> FleetCheckRun:
    run_id = uuid4().hex
    statement = select(Device)
    if active_only:
        statement = statement.where(Device.is_active.is_(True))
    devices = db.scalars(statement.order_by(Device.hostname)).all()
    runs = []
    for device in devices:
        runs.append(await run_device_checks(db, device.id, run_id=run_id))

    counts = {"healthy": 0, "warning": 0, "critical": 0, "unknown": 0}
    for run in runs:
        counts[run.overall_status] += 1

    return FleetCheckRun(run_id=run_id, checked_devices=len(runs), results=runs, **counts)


def _save_probe_results(db: Session, device: Device, probes: list[ProbeResult], run_id: str) -> list[CheckResult]:
    results = []
    for probe in probes:
        row = CheckResult(
            device_id=device.id,
            check_type=probe.check_type,
            target=probe.target,
            status=probe.status,
            latency_ms=probe.latency_ms,
            message=probe.message,
            observed_value=probe.observed_value,
            run_id=run_id,
        )
        db.add(row)
        results.append(row)
    db.commit()
    for row in results:
        db.refresh(row)
    logger.info("Saved %s check results for device id=%s run_id=%s", len(results), device.id, run_id)
    return results


def _latest_results_by_target(db: Session, device_id: int) -> dict[str, CheckResult]:
    rows = db.scalars(
        select(CheckResult)
        .where(CheckResult.device_id == device_id)
        .order_by(CheckResult.created_at.desc())
        .limit(200)
    ).all()
    latest: dict[str, CheckResult] = {}
    for row in rows:
        key = json.dumps({"check_type": row.check_type, "target": row.target}, sort_keys=True)
        if key not in latest:
            latest[key] = row
    return latest
