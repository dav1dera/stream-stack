#!/usr/bin/env python3
"""Adatta l'automazione NPM alla topologia corrente di streams-aio."""
from __future__ import annotations

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


base.proxy_payload = proxy_payload

if __name__ == "__main__":
    raise SystemExit(base.main())
