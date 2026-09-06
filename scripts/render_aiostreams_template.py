#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "setup.env"
SOURCE = ROOT / "data" / "aiostreams" / "runtime-template.json.gz.b64"
OUTPUT = ROOT / "data" / "aiostreams" / "runtime-template.json"


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        raise SystemExit("setup.env does not exist")
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


def b64url(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def streamvix_manifest(values: dict[str, str]) -> str:
    cfg = {
        "mediaflowMaster": True,
        "mediaFlowProxyUrl": f"https://{values['EASYPROXY_HOST']}/",
        "mediaFlowProxyPassword": values["EASYPROXY_PASSWORD"],
        "useMediaFlow": False,
        "dvrEnabled": False,
        "disableLiveTv": True,
        "vavooNoMfpEnabled": False,
        "trailerEnabled": False,
        "disableVixsrc": False,
        "vixDirect": False,
        "vixDirectFhd": False,
        "vixProxy": True,
        "cb01Enabled": True,
        "guardahdEnabled": True,
        "adnEnabled": True,
        "vidxgoEnabled": True,
        "cinemacityEnabled": True,
        "guardoserieEnabled": True,
        "guardaflixEnabled": True,
        "eurostreamingEnabled": False,
        "toonitaliaEnabled": True,
        "toonEnabled": True,
        "animesaturnEnabled": True,
        "animeworldEnabled": True,
        "animeunityEnabled": True,
        "animeunityDirect": False,
        "animeunityDirectFhd": False,
        "animeunityProxy": True,
        "fastMode": True,
    }
    encoded = b64url(json.dumps(cfg, separators=(",", ":"), ensure_ascii=False))
    return f"https://{values['STREAMVIX_HOST']}/{encoded}/manifest.json"


def tvvoo_manifest(values: dict[str, str]) -> str:
    proxy_url = b64url(f"https://{values['EASYPROXY_HOST']}")
    proxy_password = b64url(values["EASYPROXY_PASSWORD"])
    config = "cfg-it-uk-fr-de-pt-es-al-tr-ar-bk-ru-ro-pl-bg"
    return (
        f"https://{values['TVVOO_HOST']}/{config}"
        f"-mfu_{proxy_url}-mfp_{proxy_password}/manifest.json"
    )


def replace_strings(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {k: replace_strings(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_strings(v, replacements) for v in value]
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, new)
        return value
    return value


def main() -> int:
    values = parse_env(SETUP)
    required = (
        "AIO_USER",
        "AIO_PASSWORD",
        "TMDB_API_KEY",
        "TMDB_ACCESS_TOKEN",
        "EASYPROXY_HOST",
        "EASYPROXY_PASSWORD",
        "STREAMVIX_HOST",
        "TVVOO_HOST",
    )
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise SystemExit("cannot render AIOStreams template; missing setup values: " + ", ".join(missing))

    try:
        packed = base64.b64decode("".join(SOURCE.read_text(encoding="ascii").split()))
        template = json.loads(gzip.decompress(packed).decode("utf-8"))
    except Exception as exc:
        raise SystemExit(f"cannot decode sanitized AIOStreams template: {exc}") from exc

    replacements = {
        "CHANGE_ME_AIO_USER": values["AIO_USER"],
        "CHANGE_ME_AIO_PASSWORD": values["AIO_PASSWORD"],
        "CHANGE_ME_TMDB_API_KEY": values["TMDB_API_KEY"],
        "CHANGE_ME_TMDB_ACCESS_TOKEN": values["TMDB_ACCESS_TOKEN"],
        "CHANGE_ME_STREAMVIX_MANIFEST_URL": streamvix_manifest(values),
        "CHANGE_ME_TVVOO_MANIFEST_URL": tvvoo_manifest(values),
    }
    rendered = replace_strings(template, replacements)
    text = json.dumps(rendered, ensure_ascii=False, indent=2) + "\n"
    if "CHANGE_ME_" in text:
        raise SystemExit("rendered AIOStreams template still contains unresolved CHANGE_ME placeholders")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8")
    os.chmod(OUTPUT, 0o600)
    print(f"rendered: {OUTPUT.relative_to(ROOT)} (mode 600)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
