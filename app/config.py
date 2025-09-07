import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Load .env if present (host/dev convenience; docker-compose also injects env)
load_dotenv()


def _get_env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _get_env_list(key: str, default: List[str] | None = None) -> List[str]:
    raw = os.getenv(key)
    if raw is None:
        return default or []
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


@dataclass
class Config:
    # server
    server_name: str = os.getenv("SERVER_NAME", "MCP ToDo Server")
    server_version: str = os.getenv("SERVER_VERSION", "0.2.0")
    protocol_revision: str = os.getenv("MCP_PROTOCOL_REV", "2025-06-18")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    port: int = int(os.getenv("PORT", "8081"))
    api_key: str | None = os.getenv("API_KEY")

    # cors
    allow_origins: List[str] = field(default_factory=lambda: _get_env_list("ALLOW_ORIGINS", []))

    # tool schema dir
    tool_schema_dir: str = os.getenv("TOOL_SCHEMA_DIR") or os.path.join(os.path.dirname(__file__), "tools")

    # http/client
    http_timeout: int = int(os.getenv("HTTP_TIMEOUT", "30"))

    # graph
    graph_base_url: str = os.getenv("GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0")

    # rate limiter
    rate_per_sec: float = float(os.getenv("RATE_PER_SEC", "5"))
    rate_burst: int = int(os.getenv("RATE_BURST", "5"))

    # circuit breaker
    cb_fails: int = int(os.getenv("CB_FAILS", "3"))
    cb_cooldown_sec: int = int(os.getenv("CB_COOLDOWN_SEC", "5"))

    # features
    sse_enabled: bool = _get_env_bool("SSE_ENABLED", True)

    # database
    db_url: str | None = os.getenv("DB_URL")
    db_echo: bool = _get_env_bool("DB_ECHO", False)
    db_auto_create: bool = _get_env_bool("DB_AUTO_CREATE", True)


cfg = Config()
