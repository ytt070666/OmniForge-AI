from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = ROOT / "apps" / "omniops"
WEB_ROOT = APP_ROOT / "web"
DEFAULT_DATA_ROOT = ROOT / "artifacts" / "omnirag" / "omniops"


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    mode: str
    data_root: Path
    database_path: Path
    upload_root: Path
    ragflow_api_root: str
    ragflow_api_key: str
    ragflow_chat_id: str
    max_upload_mb: int
    enable_demo_seed: bool

    @property
    def ragflow_enabled(self) -> bool:
        return self.mode == "ragflow" and bool(self.ragflow_api_root and self.ragflow_api_key and self.ragflow_chat_id)


def load_settings() -> Settings:
    data_root = Path(os.getenv("OMNIOPS_DATA_ROOT", str(DEFAULT_DATA_ROOT))).expanduser().resolve()
    return Settings(
        host=os.getenv("OMNIOPS_HOST", "127.0.0.1"),
        port=int(os.getenv("OMNIOPS_PORT", "8090")),
        mode=os.getenv("OMNIOPS_MODE", "demo").strip().lower(),
        data_root=data_root,
        database_path=Path(os.getenv("OMNIOPS_DATABASE", str(data_root / "omniops.db"))).expanduser().resolve(),
        upload_root=Path(os.getenv("OMNIOPS_UPLOAD_ROOT", str(data_root / "uploads"))).expanduser().resolve(),
        ragflow_api_root=os.getenv("OMNIOPS_RAGFLOW_API_ROOT", "http://127.0.0.1:9380/api/v1").rstrip("/"),
        ragflow_api_key=os.getenv("OMNIOPS_RAGFLOW_API_KEY", "").strip(),
        ragflow_chat_id=os.getenv("OMNIOPS_RAGFLOW_CHAT_ID", "").strip(),
        max_upload_mb=max(1, int(os.getenv("OMNIOPS_MAX_UPLOAD_MB", "8"))),
        enable_demo_seed=_bool("OMNIOPS_ENABLE_DEMO_SEED", True),
    )
