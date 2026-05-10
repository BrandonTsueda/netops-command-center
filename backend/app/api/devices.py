import csv
import io

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.device import DeviceCreate, DeviceList, DeviceRead, DeviceUpdate
from app.schemas.health_check import DeviceCheckRun
from app.services.check_engine import run_device_checks
from app.services import device_service

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=DeviceList)
def list_devices(
    search: str | None = Query(default=None, max_length=120),
    active_only: bool = False,
    db: Session = Depends(get_db),
) -> DeviceList:
    items, total = device_service.list_devices(db=db, search=search, active_only=active_only)
    return DeviceList(items=items, total=total)


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)) -> DeviceRead:
    return device_service.create_device(db=db, payload=payload)


@router.get("/export.csv")
def export_devices_csv(active_only: bool = False, db: Session = Depends(get_db)) -> Response:
    items, _ = device_service.list_devices(db=db, active_only=active_only)
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "hostname",
            "ip_address",
            "role",
            "site",
            "platform",
            "owner",
            "tags",
            "connection_type",
            "tcp_ports",
            "http_urls",
            "ssh_enabled",
            "is_active",
            "updated_at",
        ],
    )
    writer.writeheader()
    for item in items:
        writer.writerow(
            {
                "id": item.id,
                "hostname": item.hostname,
                "ip_address": item.ip_address,
                "role": item.role,
                "site": item.site,
                "platform": item.platform or "",
                "owner": item.owner or "",
                "tags": ",".join(item.tags),
                "connection_type": item.connection_type,
                "tcp_ports": ",".join(str(port) for port in item.tcp_ports),
                "http_urls": ",".join(item.http_urls),
                "ssh_enabled": item.ssh_enabled,
                "is_active": item.is_active,
                "updated_at": item.updated_at.isoformat(),
            }
        )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="netops-inventory.csv"'},
    )


@router.get("/export.json", response_model=DeviceList)
def export_devices_json(active_only: bool = False, db: Session = Depends(get_db)) -> DeviceList:
    items, total = device_service.list_devices(db=db, active_only=active_only)
    return DeviceList(items=items, total=total)


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)) -> DeviceRead:
    return device_service.to_device_read(device_service.get_device(db=db, device_id=device_id))


@router.put("/{device_id}", response_model=DeviceRead)
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)) -> DeviceRead:
    return device_service.update_device(db=db, device_id=device_id, payload=payload)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int, db: Session = Depends(get_db)) -> Response:
    device_service.delete_device(db=db, device_id=device_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{device_id}/run-checks", response_model=DeviceCheckRun)
async def run_checks_for_device(device_id: int, db: Session = Depends(get_db)) -> DeviceCheckRun:
    return await run_device_checks(db=db, device_id=device_id)
