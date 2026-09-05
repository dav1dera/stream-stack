#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.client
import json
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SETUP_FILE = ROOT / "setup.env"

# Porte LAN che devono risultare aperte quando lo stack completo e' avviato.
LOCAL_PORTS = {
    "Nginx Proxy Manager": 81,
    "Portainer": 9443,
    "Headplane": 3000,
    "AIOStreams": 4444,
    "AIOMetadata": 1337,
    "MediaFlow Proxy": 8888,
    "Honey": 4173,
    "EasyProxy": 8760,
    "TvVoo": 5000,
    "AIOManager": 1610,
    "Comet": 2020,
    "StremThru": 9090,
    "Jackett": 9117,
    "StreamViX": 7860,
    "Seanime": 43211,
    "Seanime Shared": 43311,
}


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = value[1:-1]
        elif len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1]
        values[key] = value
    return values


def as_bool(value: str, default: bool = True) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _run_compose(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "--profile", "all", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def compose_ps() -> tuple[bool, list[str]]:
    """Require every service in the all profile to exist, run, and be healthy when applicable."""
    expected_proc = _run_compose("config", "--services")
    if expected_proc.returncode != 0:
        return False, [
            f"docker compose config --services failed: {expected_proc.stderr.strip() or expected_proc.stdout.strip()}"
        ]
    expected = {line.strip() for line in expected_proc.stdout.splitlines() if line.strip()}

    proc = _run_compose("ps", "-a", "--format", "json")
    if proc.returncode != 0:
        return False, [f"docker compose ps failed: {proc.stderr.strip() or proc.stdout.strip()}"]

    raw = proc.stdout.strip()
    if not raw:
        return False, ["docker compose ps returned no services"]

    try:
        parsed = json.loads(raw)
        rows = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        rows = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                return False, ["unable to parse docker compose ps --format json output"]

    actual = {str(row.get("Service") or "").strip() for row in rows if row.get("Service")}
    problems: list[str] = []
    for service in sorted(expected - actual):
        problems.append(f"{service}: container missing")

    for row in rows:
        service = str(row.get("Service") or row.get("Name") or "unknown")
        state = str(row.get("State") or "").lower()
        health = str(row.get("Health") or "").lower()
        if state != "running":
            problems.append(f"{service}: state={state or 'unknown'}")
        elif health and health != "healthy":
            problems.append(f"{service}: health={health}")

    return not problems, problems


def tcp_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def local_ports(server_ip: str) -> tuple[bool, list[str]]:
    problems = [
        f"{name}: {server_ip}:{port} closed"
        for name, port in LOCAL_PORTS.items()
        if not tcp_open(server_ip, port)
    ]
    return not problems, problems


def load_current_npm_topology(values: dict[str, str]) -> tuple[list[dict[str, Any]], set[str]]:
    # npm_current mutates npm_apply.HOSTS/DEFAULT_PREFIX to the exact current topology.
    sys.path.insert(0, str(ROOT / "scripts"))
    import npm_current as current  # type: ignore

    hosts = current.base.resolved_hosts(values)
    return hosts, set(current.LAN_ONLY)


def dns_addresses(hostname: str) -> list[str]:
    addresses: set[str] = set()
    try:
        for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM):
            addresses.add(item[4][0])
    except socket.gaierror:
        return []
    return sorted(addresses)


def https_check(hostname: str, path: str = "/", timeout: float = 8.0) -> tuple[bool, str]:
    """Validate DNS, TLS hostname/certificate, NPM routing and a non-5xx HTTP response."""
    addresses = dns_addresses(hostname)
    if not addresses:
        return False, "DNS unresolved"

    context = ssl.create_default_context()
    try:
        conn = http.client.HTTPSConnection(hostname, 443, timeout=timeout, context=context)
        conn.request("GET", path, headers={"User-Agent": "stream-stack-acceptance/1.0"})
        response = conn.getresponse()
        status = response.status
        response.read(1024)
        conn.close()
    except Exception as exc:
        return False, f"HTTPS/TLS failed: {exc}"

    if status >= 500:
        return False, f"HTTP {status}"

    return True, f"HTTP {status} via {', '.join(addresses)}"


def public_https(values: dict[str, str]) -> tuple[bool, list[str], list[str]]:
    hosts, lan_only = load_current_npm_topology(values)
    problems: list[str] = []
    details: list[str] = []

    for item in hosts:
        if item["setting"] in lan_only:
            continue
        hostname = item["hostname"]
        paths = ["/"]
        if item["setting"] == "HEADSCALE_HOST":
            paths = ["/admin", "/oauth2/sign_in"]
        for path in paths:
            ok, detail = https_check(hostname, path)
            details.append(f"{hostname}{path}: {detail}")
            if not ok:
                problems.append(f"{hostname}{path}: {detail}")

    return not problems, problems, details


def run_once(values: dict[str, str]) -> tuple[bool, list[str], list[str]]:
    failures: list[str] = []
    details: list[str] = []

    ok, problems = compose_ps()
    if ok:
        details.append("Docker Compose: every expected service is present and running/healthy")
    else:
        failures.extend(problems)

    server_ip = values.get("SERVER_LAN_IP", "").strip()
    if not server_ip:
        failures.append("SERVER_LAN_IP missing from setup.env")
    else:
        ok, problems = local_ports(server_ip)
        if ok:
            details.append("LAN ports: all expected service ports reachable")
        else:
            failures.extend(problems)

    if as_bool(values.get("AUTO_CONFIGURE_NPM", "true")):
        ok, problems, public_details = public_https(values)
        details.extend(public_details)
        if not ok:
            failures.extend(problems)

    return not failures, failures, details


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Strict post-deploy acceptance test for stream-stack."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Seconds to wait for all checks to pass. 0 = PUBLIC_READY_TIMEOUT from setup.env (default 600).",
    )
    parser.add_argument("--interval", type=int, default=5, help="Retry interval in seconds.")
    args = parser.parse_args()

    values = parse_env(SETUP_FILE)
    if not values:
        print("ACCEPTANCE FAILED: setup.env missing or empty", flush=True)
        return 2

    try:
        configured_timeout = int(values.get("PUBLIC_READY_TIMEOUT", "600") or "600")
    except ValueError:
        configured_timeout = 600
    timeout = args.timeout or configured_timeout
    timeout = max(30, min(timeout, 3600))
    interval = max(2, min(args.interval, 60))
    deadline = time.time() + timeout
    attempt = 0
    last_failures: list[str] = []

    print(f"Strict acceptance started (timeout={timeout}s)", flush=True)
    while True:
        attempt += 1
        ok, failures, details = run_once(values)
        if ok:
            print("ACCEPTANCE OK", flush=True)
            print("- every expected Compose service is present and running/healthy", flush=True)
            print("- expected LAN ports are reachable", flush=True)
            if as_bool(values.get("AUTO_CONFIGURE_NPM", "true")):
                print("- public non-LAN-only hostnames resolve", flush=True)
                print("- TLS hostname/certificate validation succeeds", flush=True)
                print("- NPM routes return non-5xx responses", flush=True)
                print("- Headscale /admin and /oauth2/sign_in routes are reachable", flush=True)
            for detail in details:
                print(f"  {detail}", flush=True)
            return 0

        last_failures = failures
        remaining = int(max(0, deadline - time.time()))
        print(
            f"Acceptance attempt {attempt}: not ready yet ({remaining}s remaining)",
            flush=True,
        )
        for failure in failures[:20]:
            print(f"  - {failure}", flush=True)

        if time.time() >= deadline:
            break
        time.sleep(min(interval, max(0.5, deadline - time.time())))

    print("ACCEPTANCE FAILED", flush=True)
    for failure in last_failures:
        print(f"- {failure}", flush=True)
    print(
        "The wizard must not report the deployment as ready until these checks pass.",
        flush=True,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
