from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NetOps Command Center"
    environment: str = "local"
    database_url: str = "sqlite:///./data/netops.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    scheduler_enabled: bool = False
    health_check_interval_seconds: int = 300
    ping_timeout_seconds: float = 1.5
    tcp_timeout_seconds: float = 2.0
    http_timeout_seconds: float = 4.0
    ssh_timeout_seconds: float = 3.0
    automation_ssh_timeout_seconds: int = 12
    automation_default_ssh_user: str = "root"
    automation_requested_by: str = "netops-local"
    automation_host_config_path: str = "./config/automation_hosts.local.json"
    auto_triage_enabled: bool = False
    notification_webhook_url: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ai_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlite_path(self) -> Path | None:
        if not self.database_url.startswith("sqlite:///"):
            return None
        return Path(self.database_url.replace("sqlite:///", "", 1))


@lru_cache
def get_settings() -> Settings:
    return Settings()
