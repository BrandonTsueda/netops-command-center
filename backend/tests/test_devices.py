import os

os.environ["DATABASE_URL"] = "sqlite:///./data/test_netops.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_device_crud_flow() -> None:
    payload = {
        "hostname": "edge-fw-01",
        "ip_address": "192.168.68.1",
        "role": "firewall",
        "site": "home-lab",
        "platform": "opnsense",
        "owner": "network",
        "tags": ["edge", "critical"],
        "connection_type": "icmp",
        "tcp_ports": [22, 443],
        "http_urls": ["https://192.168.68.1"],
        "ssh_enabled": True,
    }

    created = client.post("/api/v1/devices", json=payload)
    assert created.status_code == 201
    device = created.json()
    assert device["hostname"] == "edge-fw-01"
    assert device["tcp_ports"] == [22, 443]

    listed = client.get("/api/v1/devices")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = client.put(f"/api/v1/devices/{device['id']}", json={"role": "perimeter-firewall"})
    assert updated.status_code == 200
    assert updated.json()["role"] == "perimeter-firewall"

    deleted = client.delete(f"/api/v1/devices/{device['id']}")
    assert deleted.status_code == 204


def test_health_check_requires_existing_device() -> None:
    response = client.post(
        "/api/v1/health-checks",
        json={
            "device_id": 999,
            "check_type": "ping",
            "target": "192.168.68.1",
            "status": "unknown",
            "message": "not checked yet",
        },
    )
    assert response.status_code == 404


def test_automation_runbooks_are_available() -> None:
    response = client.get("/api/v1/automation/runbooks")
    assert response.status_code == 200
    runbook_ids = {item["id"] for item in response.json()}
    assert "linux_basic_diagnostics" in runbook_ids
    assert "proxmox_diagnostics" in runbook_ids


def test_automation_runs_list_is_empty_initially() -> None:
    response = client.get("/api/v1/automation/runs")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0


def test_device_inventory_exports() -> None:
    payload = {
        "hostname": "mini-pc-01",
        "ip_address": "192.168.68.65",
        "role": "mini-pc",
        "site": "home-lab",
        "tags": ["lab", "edge"],
        "connection_type": "icmp",
        "tcp_ports": [22],
        "ssh_enabled": True,
    }
    created = client.post("/api/v1/devices", json=payload)
    assert created.status_code == 201

    json_export = client.get("/api/v1/devices/export.json")
    assert json_export.status_code == 200
    assert json_export.json()["total"] == 1

    csv_export = client.get("/api/v1/devices/export.csv")
    assert csv_export.status_code == 200
    assert "mini-pc-01" in csv_export.text
    assert "netops-inventory.csv" in csv_export.headers["content-disposition"]
