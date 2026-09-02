#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"
OVERRIDE = ROOT / "docker-compose.override.yml"

EXPECTED_SERVICES = {
    "tailscale", "portainer", "adguardhome", "dnscrypt-proxy", "headscale",
    "headplane", "npm", "cloudflare-ddns", "aiometadata", "mediaflow-proxy-light",
    "aiostreams", "pgbouncer", "postgres", "redis", "watchtower", "honey",
    "teamspeak", "microwarp", "gost", "oauth2-proxy", "easyproxy", "streamvix",
    "tvvoo", "aiomanager", "deunhealth", "gluetun", "comet", "cometnet",
    "stremthru", "jackett", "seanime", "seanime-shared",
}

REQUIRED_FILES = {
    "setup.sh",
    "setup.env.example",
    "scripts/bootstrap.sh",
    "scripts/configure.py",
    "scripts/current_defaults.py",
    "scripts/npm_apply.py",
    "scripts/npm_current.py",
    "data/easyproxy/.env.example",
    "data/easyproxy/data/config.json.example",
    "data/tvvoo/.env.example",
    "data/aiomanager/.env.example",
    "data/aiostreams/.env.example",
    "data/pgbouncer/data/pgbouncer.ini",
    "data/pgbouncer/data/userlist.txt.example",
    "data/postgres/init/01-databases.sql",
    "windows-wizard/Start-Wizard.cmd",
    "windows-wizard/run.ps1",
    "windows-wizard/local_ready.py",
}

REQUIRED_SNIPPETS = {
    "data/aiostreams/.env.example": [
        "REQUEST_URL_MAPPINGS=",
        "http://streamvix:7860",
        "http://tvvoo:5000",
        "http://aiomanager:1610",
        "MAX_VARIANTS=30",
        "MAX_ADDONS=20",
    ],
    "data/tvvoo/.env.example": ["PROXY_BASE_URL=https://easyproxy.example.com", "CHANGE_ME_EASYPROXY_PASSWORD"],
    "data/streamvix/.env.example": ["MFP_URL=https://easyproxy.example.com/", "PROXY=socks5h://gluetun:1081"],
    "data/aiomanager/.env.example": ["DB_TYPE=postgres", "pgbouncer:6432/aiomanager", "CHANGE_ME_AIOMANAGER_ENCRYPTION_KEY"],
    "data/pgbouncer/data/pgbouncer.ini": ["aiomanager = host=postgres", "comet = host=postgres", "stremthru = host=postgres"],
    "docker-compose.override.yml": ["3010:3000", "43211:43211", "43311:43311"],
}

FORBIDDEN = (
    "self-stremiopi.org",
    "192.168.178.11",
)


def service_names(text: str) -> set[str]:
    names: set[str] = set()
    in_services = False
    for line in text.splitlines():
        if line == "services:":
            in_services = True
            continue
        if in_services and line and not line.startswith(" ") and line.endswith(":"):
            break
        if in_services:
            match = re.match(r"^  ([A-Za-z0-9_.-]+):\s*$", line)
            if match:
                names.add(match.group(1))
    return names


def main() -> int:
    problems: list[str] = []
    if not COMPOSE.exists():
        problems.append("docker-compose.yml mancante")
    else:
        actual = service_names(COMPOSE.read_text(encoding="utf-8"))
        missing = sorted(EXPECTED_SERVICES - actual)
        extra = sorted(actual - EXPECTED_SERVICES)
        if missing:
            problems.append("servizi mancanti: " + ", ".join(missing))
        if extra:
            problems.append("servizi inattesi: " + ", ".join(extra))
        if len(actual) != 32:
            problems.append(f"numero servizi: attesi 32, trovati {len(actual)}")

    for rel in sorted(REQUIRED_FILES):
        if not (ROOT / rel).exists():
            problems.append(f"file richiesto mancante: {rel}")

    for rel, snippets in REQUIRED_SNIPPETS.items():
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                problems.append(f"{rel}: manca `{snippet}`")

    # Scan only public templates/scripts/docs, never generated runtime state.
    scan_paths = [ROOT / "README.md", ROOT / "setup.env.example", ROOT / "scripts", ROOT / "windows-wizard"]
    for base in scan_paths:
        paths = [base] if base.is_file() else list(base.rglob("*")) if base.exists() else []
        for path in paths:
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for forbidden in FORBIDDEN:
                if forbidden in text:
                    problems.append(f"dato privato/riferimento hardcoded in {path.relative_to(ROOT)}: {forbidden}")

    if problems:
        print("VALIDAZIONE FALLITA")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("VALIDAZIONE OK")
    print("- 32 servizi attesi presenti")
    print("- template strutturali presenti")
    print("- mapping EasyProxy/TvVoo/AIOManager presenti")
    print("- override fresh-install AdGuard/Seanime presente")
    print("- nessun riferimento privato noto nei file di setup")
    return 0


if __name__ == "__main__":
    sys.exit(main())
