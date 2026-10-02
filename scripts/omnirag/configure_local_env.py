#!/usr/bin/env python3
"""Prepare or apply an OmniRAG overlay to docker/.env.

Default behavior is preview-only. `--apply` is intentionally explicit and backs
up the original docker/.env. This script does not start Docker or any model.
"""

from __future__ import annotations

import argparse
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKER_ENV = ROOT / "docker" / ".env"
OVERLAYS = {
    "baseline": ROOT / "docker" / "omnirag" / ".env.baseline.example",
    "research": ROOT / "docker" / "omnirag" / ".env.research.example",
}
OUT = ROOT / "artifacts" / "omnirag" / "prelocal"
ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
SECRET_KEYS = {"ELASTIC_PASSWORD", "MYSQL_PASSWORD", "MINIO_PASSWORD", "REDIS_PASSWORD"}


def parse_assignments(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        m = ASSIGN_RE.match(line.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def merge_env(base: str, values: dict[str, str]) -> str:
    seen = set()
    lines = []
    for line in base.splitlines():
        m = ASSIGN_RE.match(line)
        if m and m.group(1) in values:
            key = m.group(1)
            lines.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            lines.append(line)
    missing = [k for k in values if k not in seen]
    if missing:
        lines += ["", "# ---- OmniRAG overlay ----"]
        lines += [f"{k}={values[k]}" for k in missing]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--profile", choices=sorted(OVERLAYS), default="baseline")
    p.add_argument("--generate-secrets", action="store_true")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    overlay = parse_assignments(OVERLAYS[args.profile].read_text(encoding="utf-8"))
    if args.generate_secrets:
        for key in SECRET_KEYS:
            overlay[key] = secrets.token_urlsafe(32)

    base = DOCKER_ENV.read_text(encoding="utf-8")
    merged = merge_env(base, overlay)
    OUT.mkdir(parents=True, exist_ok=True)
    preview = OUT / f"docker.env.{args.profile}.preview"
    # Mask secrets in the preview artifact, even when generated.
    masked = merged
    for key in SECRET_KEYS:
        value = overlay.get(key)
        if value:
            masked = masked.replace(f"{key}={value}", f"{key}=<SET_LOCALLY>")
    preview.write_text(masked, encoding="utf-8")

    if not args.apply:
        print(f"Preview written to {preview}")
        print("No docker/.env file was modified. Use --apply locally when ready.")
        return 0

    backup = DOCKER_ENV.with_name(f".env.pre-omnirag.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
    shutil.copy2(DOCKER_ENV, backup)
    DOCKER_ENV.write_text(merged, encoding="utf-8")
    print(f"Applied {args.profile} overlay to {DOCKER_ENV}")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
