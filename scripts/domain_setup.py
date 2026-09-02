#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "setup.env"

HOSTS = [
    ("AIOSTREAMS_HOST", "AIOStreams", "aiostreams"),
    ("AIOMETADATA_HOST", "AIOMetadata", "aiometadata"),
    ("MEDIAFLOW_HOST", "MediaFlow", "mfp"),
    ("EASYPROXY_HOST", "EasyProxy", "easyproxy"),
    ("HEADSCALE_HOST", "Headscale + Headplane", "headscale"),
    ("STREAMVIX_HOST", "StreamViX", "streamv"),
    ("TVVOO_HOST", "TvVoo", "tvvoo"),
    ("AIOMANAGER_HOST", "AIOManager", "aiomanager"),
    ("SEANIME_HOST", "Seanime main", "seanime"),
    ("SEANIME_SHARED_HOST", "Seanime shared", "shared-seanime"),
    ("COMETNET_HOST", "CometNet", "cometnet"),
    ("STREMTHRU_HOST", "StremThru", "stremthru"),
    ("PORTAINER_HOST", "Portainer", "portainer"),
]


def parse(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
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
        out[key.strip()] = value
    return out


def quote(value: str) -> str:
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./:@%+,=*?-")
    if value and all(ch in safe for ch in value):
        return value
    return json.dumps(value) if value else ""


def update(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    left = dict(values)
    out: list[str] = []
    for line in lines:
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in left:
                out.append(f"{key}={quote(left.pop(key))}")
                continue
        out.append(line)
    if left:
        out.append("")
        out.extend(f"{k}={quote(v)}" for k, v in left.items())
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def clean_domain(value: str) -> str:
    value = value.strip().lower().rstrip(".")
    if "://" in value or "/" in value or " " in value or "." not in value:
        raise ValueError("usa un nome DNS senza protocollo, ad esempio example.com")
    return value


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = " [S/n]: " if default else " [s/N]: "
    while True:
        ans = input(prompt + suffix).strip().lower()
        if not ans:
            return default
        if ans in {"y", "yes", "s", "si", "sì"}:
            return True
        if ans in {"n", "no"}:
            return False
        print("Rispondi sì/no.")


def main() -> int:
    if not SETUP.exists():
        raise SystemExit("setup.env non esiste")

    values = parse(SETUP)
    base = values.get("BASE_DOMAIN", "")
    while not base:
        candidate = input("Dominio pubblico base (es. example.com): ").strip()
        try:
            base = clean_domain(candidate)
        except ValueError as exc:
            print(f"Dominio non valido: {exc}")
    base = clean_domain(base)

    missing = [key for key, _, _ in HOSTS if not values.get(key)]
    updates: dict[str, str] = {"BASE_DOMAIN": base}
    if not missing:
        update(SETUP, updates)
        return 0

    print()
    print("Hostname pubblici dei servizi")
    print("La logica interna dello stack resta fissa; i nomi DNS sono personalizzabili.")
    use_defaults = ask_yes_no(f"Usare i nomi standard sotto {base}?", default=True)

    for key, label, prefix in HOSTS:
        current = values.get(key, "").strip().lower().rstrip(".")
        if current:
            updates[key] = current
            continue
        default = f"{prefix}.{base}"
        if use_defaults:
            updates[key] = default
            continue
        while True:
            entered = input(f"Hostname {label} [{default}]: ").strip() or default
            try:
                updates[key] = clean_domain(entered)
                break
            except ValueError as exc:
                print(f"Hostname non valido: {exc}")

    update(SETUP, updates)
    print("Hostname pubblici salvati in setup.env.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
