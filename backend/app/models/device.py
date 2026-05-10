from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.session import Base


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("hostname", "ip_address", name="uq_device_hostname_ip"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hostname: Mapped[str] = mapped_column(String(120), index=True)
    ip_address: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(80), default="unknown")
    site: Mapped[str] = mapped_column(String(80), default="default")
    platform: Mapped[str | None] = mapped_column(String(120), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tags: Mapped[str] = mapped_column(Text, default="")
    connection_type: Mapped[str] = mapped_column(String(40), default="icmp")
    tcp_ports: Mapped[str] = mapped_column(Text, default="")
    http_urls: Mapped[str] = mapped_column(Text, default="")
    ssh_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    check_results = relationship("CheckResult", back_populates="device", cascade="all, delete-orphan")
