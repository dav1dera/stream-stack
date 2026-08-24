#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SETUP_FILE = ROOT / "setup.env"
NPM_ENV = ROOT / "data" / "npm" / ".env"
CF_ENV = ROOT / "data" / "cloudflare-ddns" / ".env"
NPM_API = "http://127.0.0.1:81/api"

HOSTS = (
    ("AIOSTREAMS_HOST", "aiostreams", 4444, False),
    ("AIOMETADATA_HOST", "aiometadata", 1337, True),
    ("MEDIAFLOW_HOST", "mediaflow-proxy-light", 8888, False),
    ("HEADSCALE_HOST", "headscale", 8080, True),
    ("PORTAINER_HOST", "portainer", 9000, False),
    ("STREMTHRU_HOST", "gluetun", 9090, False),
    ("SEANIME_HOST", "gluetun", 43211, True),
    ("SEANIME_SHARED_HOST", "gluetun", 43311, True),
    ("COMETNET_HOST", "gluetun", 8765, True),
    ("STREAMVIX_HOST", "gluetun", 7860, False),
)

DEFAULT_PREFIX = {
    "AIOSTREAMS_HOST": "aiostreams",
    "AIOMETADATA_HOST": "aiometadata",
    "MEDIAFLOW_HOST": "mfp",
    "HEADSCALE_HOST": "headscale",
    "PORTAINER_HOST": "portainer",
    "STREMTHRU_HOST": "stremthru",
    "SEANIME_HOST": "seanime",
    "SEANIME_SHARED_HOST": "shared-seanime",
    "COMETNET_HOST": "cometnet",
    "STREAMVIX_HOST": "streamv",
}


def log(message: str) -> None:
    print(message, flush=True)


def parse_env(path: Path) -> dict[str, str]:
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


def quote_env(value: str) -> str:
    if value == "":
        return ""
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./:@%+,=*?-")
    if all(ch in safe for ch in value):
        return value
    return json.dumps(value)


def set_env_values(path: Path, updates: dict[str, str], mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(updates)
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in remaining:
                out.append(f"{key}={quote_env(remaining.pop(key))}")
                continue
        out.append(line)
    if remaining:
        if out and out[-1] != "":
            out.append("")
        for key, value in remaining.items():
            out.append(f"{key}={quote_env(value)}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    if mode is not None:
        os.chmod(path, mode)


def as_bool(value: str, default: bool = True) -> bool:
    if value == "":
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


def resolved_hosts(values: dict[str, str]) -> list[dict[str, Any]]:
    base = values.get("BASE_DOMAIN", "").strip().lower().rstrip(".")
    if not base:
        raise SystemExit("BASE_DOMAIN is missing from setup.env")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key, forward_host, port, websocket in HOSTS:
        hostname = values.get(key, "").strip().lower().rstrip(".")
        if not hostname:
            hostname = f"{DEFAULT_PREFIX[key]}.{base}"
        if hostname in seen:
            raise SystemExit(f"Duplicate public hostname in setup.env: {hostname}")
        seen.add(hostname)
        result.append({
            "setting": key,
            "hostname": hostname,
            "forward_host": forward_host,
            "forward_port": port,
            "websocket": websocket,
        })
    return result


def cloudflare_domains(values: dict[str, str], hosts: list[dict[str, Any]]) -> str:
    # Preserve the reference wildcard DDNS behavior, but also maintain explicit
    # records for every selected host. This makes arbitrary per-service FQDN
    # overrides deterministic even if an explicit DNS record shadows a wildcard.
    base = values["BASE_DOMAIN"].strip().lower().rstrip(".")
    domains = [f"*.{base}"] + [item["hostname"] for item in hosts]
    return ",".join(dict.fromkeys(domains))


def headscale_advanced(hostname: str) -> str:
    return f'''# Managed by stream-stack setup wizard.
# Headscale stays on /; Headplane is protected by OAuth2 Proxy on /admin.

location = /admin/logout.data {{
    add_header X-Remix-Redirect "https://{hostname}/oauth2/sign_in?rd=%2Fadmin" always;
    add_header X-Remix-Reload-Document "true" always;
    return 204;
}}

location = /oauth2/callback {{
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Scheme $scheme;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Real-IP $remote_addr;

    proxy_intercept_errors on;
    error_page 403 =302 /oauth2/sign_in?rd=%2Fadmin;

    proxy_pass http://oauth2-proxy:4180;
}}

location /oauth2/ {{
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Scheme $scheme;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_http_version 1.1;
    proxy_pass http://oauth2-proxy:4180;
}}

location /admin {{
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Scheme $scheme;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;
    proxy_http_version 1.1;
    proxy_pass http://oauth2-proxy:4180;
}}
'''


def api(method: str, path: str, token: str | None = None, payload: Any = None, timeout: int = 120) -> Any:
    url = NPM_API + path
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read()
            if not body:
                return None
            return json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"NPM API {method} {path} failed: HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"NPM API {method} {path} failed: {exc}") from exc


def wait_api(timeout: int = 180) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:81/api/", timeout=5) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Nginx Proxy Manager API did not become ready on http://127.0.0.1:81")


def npm_login(email: str, password: str) -> str:
    obj = api("POST", "/tokens", payload={"identity": email, "secret": password})
    token = obj.get("token") if isinstance(obj, dict) else None
    if not token:
        raise RuntimeError("NPM login succeeded without returning a bearer token")
    return str(token)


def find_or_create_certificate(token: str, hosts: list[dict[str, Any]], email: str) -> int:
    names = [item["hostname"] for item in hosts]
    wanted = set(names)
    certificates = api("GET", "/nginx/certificates", token=token) or []
    for cert in certificates:
        if cert.get("provider") == "letsencrypt" and wanted.issubset(set(cert.get("domain_names") or [])):
            log(f"using existing NPM certificate #{cert['id']}")
            return int(cert["id"])

    # Exact SAN names are intentional instead of hardcoding a wildcard cert:
    # this works even when the installer chooses different hostnames/zones.
    log("requesting one shared Let's Encrypt certificate for the configured public hostnames...")
    payload = {
        "provider": "letsencrypt",
        "nice_name": f"stream-stack ({names[0]})",
        "domain_names": names,
        "meta": {
            "letsencrypt_email": email,
            "letsencrypt_agree": True,
            "dns_challenge": False,
        },
    }
    cert = api("POST", "/nginx/certificates", token=token, payload=payload, timeout=240)
    if not isinstance(cert, dict) or not cert.get("id"):
        raise RuntimeError("NPM did not return a certificate id")
    log(f"created NPM certificate #{cert['id']}")
    return int(cert["id"])


def proxy_payload(item: dict[str, Any], cert_id: int) -> dict[str, Any]:
    advanced = headscale_advanced(item["hostname"]) if item["setting"] == "HEADSCALE_HOST" else ""
    return {
        "domain_names": [item["hostname"]],
        "forward_scheme": "http",
        "forward_host": item["forward_host"],
        "forward_port": item["forward_port"],
        "access_list_id": 0,
        "certificate_id": cert_id,
        "ssl_forced": True,
        "caching_enabled": False,
        "block_exploits": True,
        "advanced_config": advanced,
        "meta": {
            "letsencrypt_agree": False,
            "dns_challenge": False,
        },
        "allow_websocket_upgrade": bool(item["websocket"]),
        "http2_support": True,
        "hsts_enabled": True,
        "hsts_subdomains": True,
        "trust_forwarded_proto": False,
        "enabled": True,
        "locations": [],
    }


def upsert_hosts(token: str, hosts: list[dict[str, Any]], cert_id: int) -> None:
    current = api("GET", "/nginx/proxy-hosts", token=token) or []
    by_domain: dict[str, dict[str, Any]] = {}
    for host in current:
        for domain in host.get("domain_names") or []:
            by_domain.setdefault(str(domain).lower(), host)

    for item in hosts:
        hostname = item["hostname"]
        payload = proxy_payload(item, cert_id)
        existing = by_domain.get(hostname.lower())
        if existing:
            api("PUT", f"/nginx/proxy-hosts/{existing['id']}", token=token, payload=payload)
            log(f"updated NPM host: {hostname} -> {item['forward_host']}:{item['forward_port']}")
        else:
            created = api("POST", "/nginx/proxy-hosts", token=token, payload=payload)
            log(f"created NPM host: {hostname} -> {item['forward_host']}:{item['forward_port']}")
            if isinstance(created, dict):
                by_domain[hostname.lower()] = created


def docker_compose(*args: str) -> None:
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)


def write_desired_state(hosts: list[dict[str, Any]]) -> None:
    path = ROOT / "data" / "npm" / "stream-stack-hosts.json"
    obj = [
        {
            "hostname": item["hostname"],
            "forward_scheme": "http",
            "forward_host": item["forward_host"],
            "forward_port": item["forward_port"],
            "websocket": item["websocket"],
            "force_ssl": True,
            "hsts": True,
            "hsts_subdomains": True,
            "block_exploits": True,
            "http2": True,
            "special_routing": "headscale+headplane+oauth2" if item["setting"] == "HEADSCALE_HOST" else None,
        }
        for item in hosts
    ]
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not SETUP_FILE.exists():
        raise SystemExit("setup.env does not exist; run ./setup.sh first")
    values = parse_env(SETUP_FILE)
    if not as_bool(values.get("AUTO_CONFIGURE_NPM", "true")):
        log("NPM automatic configuration disabled by AUTO_CONFIGURE_NPM=false")
        return 0

    hosts = resolved_hosts(values)
    admin_email = values.get("NPM_ADMIN_EMAIL", "").strip().lower() or values.get("ALLOWED_EMAIL", "").strip().lower()
    if not admin_email:
        admin_email = f"admin@{values['BASE_DOMAIN']}"
    admin_password = values.get("NPM_ADMIN_PASSWORD", "") or secrets.token_urlsafe(24)
    letsencrypt_email = values.get("LETSENCRYPT_EMAIL", "").strip() or values.get("ALLOWED_EMAIL", "").strip()
    if not letsencrypt_email:
        raise SystemExit("LETSENCRYPT_EMAIL or ALLOWED_EMAIL is required for automatic SSL")

    set_env_values(
        SETUP_FILE,
        {
            "NPM_ADMIN_EMAIL": admin_email,
            "NPM_ADMIN_PASSWORD": admin_password,
            "LETSENCRYPT_EMAIL": letsencrypt_email,
            "AUTO_CONFIGURE_NPM": "true",
        },
        mode=0o600,
    )
    # NPM officially supports INITIAL_ADMIN_* on first startup. On an existing
    # NPM DB these do not overwrite the current account, so the API login below
    # remains safe/idempotent and reports a clear error if credentials differ.
    set_env_values(
        NPM_ENV,
        {
            "INITIAL_ADMIN_EMAIL": admin_email,
            "INITIAL_ADMIN_PASSWORD": admin_password,
        },
    )

    ddns = cloudflare_domains(values, hosts)
    set_env_values(CF_ENV, {"DOMAINS": ddns})
    write_desired_state(hosts)

    log(f"Cloudflare DDNS domains: {ddns}")
    log("starting Cloudflare DDNS and Nginx Proxy Manager...")
    docker_compose("up", "-d", "cloudflare-ddns", "npm")
    wait_api()

    try:
        token = npm_login(admin_email, admin_password)
    except RuntimeError as exc:
        raise SystemExit(
            f"{exc}\n"
            "If this NPM database already existed, INITIAL_ADMIN_* does not replace the existing login. "
            "Put the current NPM_ADMIN_EMAIL/NPM_ADMIN_PASSWORD in setup.env and rerun ./setup.sh."
        ) from exc

    cert_id = find_or_create_certificate(token, hosts, letsencrypt_email)
    upsert_hosts(token, hosts, cert_id)

    current = api("GET", "/nginx/proxy-hosts", token=token) or []
    existing_domains = {d for host in current for d in (host.get("domain_names") or [])}
    missing = [item["hostname"] for item in hosts if item["hostname"] not in existing_domains]
    if missing:
        raise SystemExit("NPM verification failed; missing proxy hosts: " + ", ".join(missing))

    log("NPM configuration complete: shared SSL + proxy routing matches the reference topology.")
    log("Unrelated/manual NPM proxy hosts are left untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
