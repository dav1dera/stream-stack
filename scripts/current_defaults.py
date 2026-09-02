#!/usr/bin/env python3
"""Completa i valori introdotti dalla topologia corrente prima del renderer principale."""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "setup.env"

HOST_DEFAULTS = {
    "EASYPROXY_HOST": "easyproxy",
    "TVVOO_HOST": "tvvoo",
    "AIOMANAGER_HOST": "aiomanager",
}


def parse(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = value[1:-1]
        elif len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def quote(value: str) -> str:
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./:@%+,=*?-")
    if value and all(ch in safe for ch in value):
        return value
    return json.dumps(value) if value else ""


def write_updates(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    left = dict(updates)
    output: list[str] = []
    for line in lines:
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in left:
                output.append(f"{key}={quote(left.pop(key))}")
                continue
        output.append(line)
    if left:
        if output and output[-1] != "":
            output.append("")
        output.extend(f"{key}={quote(value)}" for key, value in left.items())
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def main() -> int:
    if not SETUP.exists():
        raise SystemExit("setup.env non esiste")
    values = parse(SETUP)
    base = values.get("BASE_DOMAIN", "").strip().lower().rstrip(".")
    updates: dict[str, str] = {}

    if base:
        for key, prefix in HOST_DEFAULTS.items():
            if not values.get(key):
                updates[key] = f"{prefix}.{base}"

    if not values.get("EASYPROXY_PASSWORD"):
        updates["EASYPROXY_PASSWORD"] = secrets.token_urlsafe(20)
    if not values.get("AIOMANAGER_ENCRYPTION_KEY"):
        updates["AIOMANAGER_ENCRYPTION_KEY"] = secrets.token_hex(32)

    if updates:
        write_updates(SETUP, updates)
        for key in updates:
            if key.endswith("_HOST"):
                print(f"derived: {key}")
            else:
                print(f"generated: {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
