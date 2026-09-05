#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"

EXPECTED_SERVICES = {
    "tailscale", "portainer", "dnscrypt-proxy", "headscale",
    "headplane", "npm", "cloudflare-ddns", "aiometadata", "mediaflow-proxy-light",
    "aiostreams", "pgbouncer", "postgres", "redis", "watchtower", "honey",
    "teamspeak", "microwarp", "gost", "oauth2-proxy", "easyproxy", "streamvix",
    "tvvoo", "aiomanager", "deunhealth", "gluetun", "comet", "cometnet",
    "stremthru", "jackett", "seanime", "seanime-shared",
}

REQUIRED_FILES = {
    "setup.sh", "setup.env.example", "docker-compose.override.yml",
    "scripts/bootstrap.sh", "scripts/configure.py", "scripts/current_defaults.py",
    "scripts/npm_apply.py", "scripts/npm_current.py", "scripts/acceptance.py",
    "data/easyproxy/.env.example", "data/easyproxy/data/config.json.example",
    "data/tvvoo/.env.example", "data/aiomanager/.env.example",
    "data/aiostreams/.env.example", "data/comet/.env.example",
    "data/pgbouncer/data/pgbouncer.ini", "data/pgbouncer/data/userlist.txt.example",
    "data/postgres/postgresql.conf", "data/postgres/init/01-databases.sql",
    "windows-wizard/Start-Wizard.cmd", "windows-wizard/run.ps1",
    "windows-wizard/launcher.py", "windows-wizard/local_ready.py",
}

REQUIRED_SNIPPETS = {
    "docker-compose.yml": ["ALLOW_NO_AUTH=1"],
    "setup.env.example": ["PUBLIC_READY_TIMEOUT=600", "STRICT_ACCEPTANCE=true"],
    "data/aiostreams/.env.example": [
        "REQUEST_URL_MAPPINGS=", "http://streamvix:7860", "http://tvvoo:5000",
        "http://aiomanager:1610", "MAX_VARIANTS=30", "MAX_ADDONS=20",
    ],
    "data/tvvoo/.env.example": [
        "PROXY_BASE_URL=https://CHANGE_ME_EASYPROXY_HOST",
        "CHANGE_ME_EASYPROXY_PASSWORD",
    ],
    "data/streamvix/.env.example": [
        "MFP_URL=https://CHANGE_ME_EASYPROXY_HOST/",
        "PROXY=socks5h://gluetun:1081",
    ],
    "data/aiomanager/.env.example": [
        "DB_TYPE=postgres", "pgbouncer:6432/aiomanager",
        "CHANGE_ME_AIOMANAGER_ENCRYPTION_KEY",
    ],
    "data/comet/.env.example": [
        "BACKGROUND_SCRAPER_CONCURRENT_WORKERS=8",
        "BACKGROUND_SCRAPER_MAX_MOVIES_PER_RUN=700",
        "BACKGROUND_SCRAPER_MAX_SERIES_PER_RUN=500",
        "BACKGROUND_SCRAPER_MAX_EPISODES_PER_SERIES_PER_RUN=25",
    ],
    "data/pgbouncer/data/pgbouncer.ini": [
        "comet = host=postgres port=5432 dbname=comet pool_size=32 max_db_connections=40",
        "stremthru = host=postgres port=5432 dbname=stremthru pool_size=16 max_db_connections=24",
        "aiomanager = host=postgres port=5432 dbname=aiomanager pool_size=8 max_db_connections=12",
        "default_pool_size = 16", "reserve_pool_size = 4",
    ],
    "data/postgres/postgresql.conf": [
        "max_connections = 120", "synchronous_commit = on",
        "checkpoint_timeout = 15min", "checkpoint_completion_target = 0.95",
    ],
    "data/postgres/init/01-databases.sql": [
        "ALTER ROLE comet SET synchronous_commit = off;",
        "ALTER ROLE comet SET work_mem = '16MB';",
        "ALTER ROLE stremthru SET synchronous_commit = off;",
    ],
    "scripts/npm_current.py": [
        "wait_public_dns", "cloudflare-dns.com/dns-query", "PUBLIC_READY_TIMEOUT",
        "TCP 80", "TCP 443",
    ],
    "scripts/acceptance.py": [
        "ACCEPTANCE OK", "docker compose", "https_check", "HEADSCALE_HOST",
        "PUBLIC_READY_TIMEOUT",
    ],
    "windows-wizard/launcher.py": [
        "STRICT_ACCEPTANCE", "ROUTER_PORTS_READY", "scripts/acceptance.py",
        "Acceptance test end-to-end",
    ],
    "docker-compose.override.yml": ["43211:43211", "43311:43311"],
}

# Constructed in pieces so the validator does not flag its own test literals.
FORBIDDEN = (
    "self-" + "stremiopi.org",
    "192.168." + "178.11",
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
        if len(actual) != 31:
            problems.append(f"numero servizi: attesi 31, trovati {len(actual)}")

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

    scan_paths = [ROOT / "README.md", ROOT / "setup.env.example", ROOT / "scripts", ROOT / "windows-wizard"]
    for base in scan_paths:
        paths = [base] if base.is_file() else list(base.rglob("*")) if base.exists() else []
        for path in paths:
            if not path.is_file() or path.resolve() == Path(__file__).resolve():
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
    print("- 31 servizi attesi presenti")
    print("- template strutturali presenti")
    print("- tuning Comet/PostgreSQL/PgBouncer allineato")
    print("- MicroWARP configurato per SOCKS interno senza auth")
    print("- readiness one-click: wait DNS + strict acceptance presenti")
    print("- mapping EasyProxy/TvVoo/AIOManager presenti")
    print("- override fresh-install Seanime presente")
    print("- nessun riferimento privato noto nei file di setup")
    return 0


if __name__ == "__main__":
    sys.exit(main())
