#!/usr/bin/env python3
"""Adatta l'automazione NPM alla topologia corrente di streams-aio."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

import npm_apply as base

# setting, target Docker, porta, websocket
base.HOSTS = (
    ("AIOSTREAMS_HOST", "aiostreams", 4444, False),
    ("AIOMETADATA_HOST", "aiometadata", 1337, True),
    ("MEDIAFLOW_HOST", "mediaflow-proxy-light", 8888, False),
    ("EASYPROXY_HOST", "easyproxy", 8760, False),
    ("HEADSCALE_HOST", "headscale", 8080, True),
    ("PORTAINER_HOST", "portainer", 9000, False),
    ("STREMTHRU_HOST", "gluetun", 9090, False),
    ("SEANIME_HOST", "gluetun", 43211, True),
    ("SEANIME_SHARED_HOST", "gluetun", 43311, True),
    ("COMETNET_HOST", "gluetun", 8765, True),
    ("STREAMVIX_HOST", "streamvix", 7860, False),
    ("TVVOO_HOST", "tvvoo", 5000, False),
    ("AIOMANAGER_HOST", "aiomanager", 1610, True),
)

base.DEFAULT_PREFIX = {
    "AIOSTREAMS_HOST": "aiostreams",
    "AIOMETADATA_HOST": "aiometadata",
    "MEDIAFLOW_HOST": "mfp",
    "EASYPROXY_HOST": "easyproxy",
    "HEADSCALE_HOST": "headscale",
    "PORTAINER_HOST": "portainer",
    "STREMTHRU_HOST": "stremthru",
    "SEANIME_HOST": "seanime",
    "SEANIME_SHARED_HOST": "shared-seanime",
    "COMETNET_HOST": "cometnet",
    "STREAMVIX_HOST": "streamv",
    "TVVOO_HOST": "tvvoo",
    "AIOMANAGER_HOST": "aiomanager",
}

# Nel deployment di riferimento questi host sono pubblicati via HTTPS ma
# accettano richieste solo dalla LAN. EasyProxy resta pubblico perché viene
# usato direttamente dai client per il playback HLS.
LAN_ONLY = {
    "PORTAINER_HOST",
    "STREMTHRU_HOST",
    "STREAMVIX_HOST",
    "TVVOO_HOST",
    "AIOMANAGER_HOST",
}

_original_proxy_payload = base.proxy_payload
_original_find_or_create_certificate = base.find_or_create_certificate


def proxy_payload(item, cert_id):
    payload = _original_proxy_payload(item, cert_id)
    if item["setting"] in LAN_ONLY:
        values = base.parse_env(base.SETUP_FILE)
        subnet = values.get("LAN_SUBNET", "").strip()
        if not subnet:
            raise SystemExit("LAN_SUBNET mancante: impossibile applicare la policy LAN-only NPM")
        restriction = (
            "# LAN-only: gestito automaticamente da stream-stack\n"
            f"allow {subnet};\n"
            "deny all;\n"
        )
        current = payload.get("advanced_config", "")
        payload["advanced_config"] = (current + "\n" + restriction).strip() + "\n"
    return payload


def _doh_addresses(hostname: str) -> list[str]:
    addresses: list[str] = []
    for record_type in ("A", "AAAA"):
        query = urllib.parse.urlencode({"name": hostname, "type": record_type})
        req = urllib.request.Request(
            f"https://cloudflare-dns.com/dns-query?{query}",
            headers={"Accept": "application/dns-json", "User-Agent": "stream-stack-setup/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
        if data.get("Status") != 0:
            continue
        for answer in data.get("Answer") or []:
            value = str(answer.get("data") or "").strip()
            if value:
                addresses.append(value)
    return addresses


def wait_public_dns(hosts) -> None:
    """Wait for Cloudflare's public resolver to see every hostname before HTTP-01."""
    values = base.parse_env(base.SETUP_FILE)
    try:
        timeout = int(values.get("PUBLIC_READY_TIMEOUT", "600") or "600")
    except ValueError:
        timeout = 600
    timeout = max(30, min(timeout, 3600))
    deadline = time.time() + timeout
    pending = {item["hostname"] for item in hosts}
    last_log = 0.0

    base.log(f"waiting for public DNS propagation (up to {timeout}s)...")
    while pending and time.time() < deadline:
        resolved_now = {hostname for hostname in pending if _doh_addresses(hostname)}
        pending -= resolved_now
        now = time.time()
        if resolved_now:
            for hostname in sorted(resolved_now):
                base.log(f"public DNS ready: {hostname}")
        if pending and now - last_log >= 20:
            base.log("still waiting for public DNS: " + ", ".join(sorted(pending)))
            last_log = now
        if pending:
            time.sleep(5)

    if pending:
        raise RuntimeError(
            "Public DNS did not become ready before the timeout: " + ", ".join(sorted(pending))
        )


def find_or_create_certificate(token, hosts, email):
    wait_public_dns(hosts)
    try:
        return _original_find_or_create_certificate(token, hosts, email)
    except RuntimeError as exc:
        raise RuntimeError(
            f"{exc}\n"
            "Automatic HTTPS failed. For a fresh install, forward TCP 80 and TCP 443 on the router "
            "to SERVER_LAN_IP before running the wizard; HTTP-01 needs TCP 80 during certificate issuance."
        ) from exc


base.proxy_payload = proxy_payload
base.find_or_create_certificate = find_or_create_certificate

if __name__ == "__main__":
    raise SystemExit(base.main())
