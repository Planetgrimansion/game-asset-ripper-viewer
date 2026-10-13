"""Runtime settings — defaults, file overrides, env overrides.

Precedence (highest wins):
    CLI flags  >  env (GAR_*)  >  config/local.toml  >  config/default.toml
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT_TOML = Path(__file__).with_name("default.toml")
_LOCAL_TOML = Path(__file__).parent.parent.parent.parent / "config" / "local.toml"


@dataclass(slots=True)
class Settings:
    out_dir: Path = Path("out")
    driver: str = "fs"
    workers: int = 0  # 0 => auto
    kinds: set[str] | None = None
    max_blob_mb: int = 512
    hash_names: bool = True
    keep_original_bytes: bool = False
    processor_options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.workers <= 0:
            self.workers = max(1, (os.cpu_count() or 4))


def _merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_toml(p: Path) -> dict[str, Any]:
    if not p.is_file():
        return {}
    with p.open("rb") as fh:
        return tomllib.load(fh)


def load_settings() -> Settings:
    cfg = _read_toml(_DEFAULT_TOML)
    cfg = _merge(cfg, _read_toml(_LOCAL_TOML))

    for key, env in _ENV_MAP.items():
        if (val := os.environ.get(env)) is not None:
            cfg[key] = _coerce(key, val)

    return Settings(
        out_dir=Path(cfg.get("out_dir", "out")),
        driver=str(cfg.get("driver", "fs")),
        workers=int(cfg.get("workers", 0)),
        kinds=set(cfg["kinds"]) if cfg.get("kinds") else None,
        max_blob_mb=int(cfg.get("max_blob_mb", 512)),
        hash_names=bool(cfg.get("hash_names", True)),
        keep_original_bytes=bool(cfg.get("keep_original_bytes", False)),
        processor_options=dict(cfg.get("processor_options", {})),
    )


_ENV_MAP = {
    "out_dir": "GAR_OUT_DIR",
    "driver": "GAR_DRIVER",
    "workers": "GAR_WORKERS",
    "max_blob_mb": "GAR_MAX_BLOB_MB",
    "hash_names": "GAR_HASH_NAMES",
}


def _coerce(key: str, raw: str) -> Any:
    if key in {"workers", "max_blob_mb"}:
        return int(raw)
    if key in {"hash_names", "keep_original_bytes"}:
        return raw.lower() in {"1", "true", "yes", "on"}
    return raw