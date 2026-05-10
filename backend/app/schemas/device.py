from datetime import datetime
from ipaddress import ip_address
from pydantic import BaseModel, ConfigDict, Field, field_validator


VALID_CONNECTION_TYPES = {"icmp", "tcp", "http", "ssh", "agent", "manual"}


class DeviceBase(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=120, examples=["core-switch-01"])
    ip_address: str = Field(..., min_length=3, max_length=64, examples=["192.168.68.1"])
    role: str = Field(default="unknown", max_length=80, examples=["core-switch"])
    site: str = Field(default="default", max_length=80, examples=["home-lab"])
    platform: str | None = Field(default=None, max_length=120, examples=["Debian 12"])
    owner: str | None = Field(default=None, max_length=120, examples=["network-team"])
    tags: list[str] = Field(default_factory=list, examples=[["proxmox", "critical"]])
    connection_type: str = Field(default="icmp", examples=["icmp"])
    tcp_ports: list[int] = Field(default_factory=list, examples=[[22, 80, 443]])
    http_urls: list[str] = Field(default_factory=list, examples=[["https://example.local/health"]])
    ssh_enabled: bool = False
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool = True

    @field_validator("hostname", "role", "site", "connection_type", mode="before")
    @classmethod
    def strip_lower_fields(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str) -> str:
        value = value.strip()
        try:
            ip_address(value)
        except ValueError as exc:
            raise ValueError("ip_address must be a valid IPv4 or IPv6 address") from exc
        return value

    @field_validator("connection_type")
    @classmethod
    def validate_connection_type(cls, value: str) -> str:
        if value not in VALID_CONNECTION_TYPES:
            raise ValueError(f"connection_type must be one of: {', '.join(sorted(VALID_CONNECTION_TYPES))}")
        return value

    @field_validator("tcp_ports")
    @classmethod
    def validate_tcp_ports(cls, value: list[int]) -> list[int]:
        invalid = [port for port in value if port < 1 or port > 65535]
        if invalid:
            raise ValueError("tcp_ports must contain values between 1 and 65535")
        return sorted(set(value))

    @field_validator("http_urls")
    @classmethod
    def validate_http_urls(cls, value: list[str]) -> list[str]:
        cleaned = []
        for url in value:
            candidate = url.strip()
            if not candidate.startswith(("http://", "https://")):
                raise ValueError("http_urls must start with http:// or https://")
            cleaned.append(candidate)
        return cleaned


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    hostname: str | None = Field(default=None, min_length=1, max_length=120)
    ip_address: str | None = Field(default=None, min_length=3, max_length=64)
    role: str | None = Field(default=None, max_length=80)
    site: str | None = Field(default=None, max_length=80)
    platform: str | None = Field(default=None, max_length=120)
    owner: str | None = Field(default=None, max_length=120)
    tags: list[str] | None = None
    connection_type: str | None = None
    tcp_ports: list[int] | None = None
    http_urls: list[str] | None = None
    ssh_enabled: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None

    @field_validator("hostname", "role", "site", "connection_type", mode="before")
    @classmethod
    def strip_optional_lower_fields(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return str(value).strip().lower()

    @field_validator("ip_address")
    @classmethod
    def validate_optional_ip_address(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return DeviceBase.validate_ip_address(value)

    @field_validator("connection_type")
    @classmethod
    def validate_optional_connection_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return DeviceBase.validate_connection_type(value)

    @field_validator("tcp_ports")
    @classmethod
    def validate_optional_tcp_ports(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        return DeviceBase.validate_tcp_ports(value)

    @field_validator("http_urls")
    @classmethod
    def validate_optional_http_urls(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return DeviceBase.validate_http_urls(value)


class DeviceRead(DeviceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceList(BaseModel):
    items: list[DeviceRead]
    total: int
