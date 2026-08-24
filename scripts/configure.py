#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import ipaddress
import json
import os
import re
import secrets
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SETUP_FILE = ROOT / "setup.env"
SETUP_EXAMPLE = ROOT / "setup.env.example"
BOOTSTRAP = ROOT / "scripts" / "bootstrap.sh"

PLACEHOLDER_RE = re.compile(r"CHANGE_ME_[A-Z0-9_]+")

TOKEN_TO_SETTING = {
    "CHANGE_ME_POSTGRES_PASSWORD": "POSTGRES_PASSWORD",
    "CHANGE_ME_AIOMETADATA_ADMIN_KEY": "AIOMETADATA_ADMIN_KEY",
    "CHANGE_ME_AIOMETADATA_ADDON_PASSWORD": "AIOMETADATA_ADDON_PASSWORD",
    "CHANGE_ME_TMDB_API_KEY": "TMDB_API_KEY",
    "CHANGE_ME_TMDB_ACCESS_TOKEN": "TMDB_ACCESS_TOKEN",
    "CHANGE_ME_TVDB_API_KEY": "TVDB_API_KEY",
    "CHANGE_ME_MDBLIST_API_KEY": "MDBLIST_API_KEY",
    "CHANGE_ME_GEMINI_API_KEY": "GEMINI_API_KEY",
    "CHANGE_ME_ANILIST_CLIENT_ID": "ANILIST_CLIENT_ID",
    "CHANGE_ME_ANILIST_CLIENT_SECRET": "ANILIST_CLIENT_SECRET",
    "CHANGE_ME_TRAKT_CLIENT_ID": "TRAKT_CLIENT_ID",
    "CHANGE_ME_TRAKT_CLIENT_SECRET": "TRAKT_CLIENT_SECRET",
    "CHANGE_ME_AIOMETADATA_CONFIG_UUID": "AIOMETADATA_CONFIG_UUID",
    "CHANGE_ME_64_HEX_SECRET": "AIO_SECRET_KEY",
    "CHANGE_ME_AIO_USER": "AIO_USER",
    "CHANGE_ME_AIO_PASSWORD": "AIO_PASSWORD",
    "CHANGE_ME_AIO_CONFIG_ACCESS_KEY": "AIO_CONFIG_ACCESS_KEY",
    "CHANGE_ME_JACKETT_API_KEY": "JACKETT_API_KEY",
    "CHANGE_ME_AIO_TRUSTED_UUID": "AIO_TRUSTED_UUID",
    "CHANGE_ME_COMET_PUBLIC_API_TOKEN": "COMET_PUBLIC_API_TOKEN",
    "CHANGE_ME_COMETNET_API_KEY": "COMETNET_API_KEY",
    "CHANGE_ME_TORBOX_API_KEY": "TORBOX_API_KEY",
    "CHANGE_ME_CLOUDFLARE_API_TOKEN": "CLOUDFLARE_API_TOKEN",
    "CHANGE_ME_COMET_ADMIN_PASSWORD": "COMET_ADMIN_PASSWORD",
    "CHANGE_ME_COMET_CONFIG_PASSWORD": "COMET_CONFIG_PASSWORD",
    "CHANGE_ME_COMET_STREAM_PROXY_PASSWORD": "COMET_STREAM_PROXY_PASSWORD",
    "CHANGE_ME_WIREGUARD_PRIVATE_KEY": "WIREGUARD_PRIVATE_KEY",
    "CHANGE_ME_WIREGUARD_ADDRESS_CIDR": "WIREGUARD_ADDRESS_CIDR",
    "CHANGE_ME_HEADPLANE_32_CHAR_SECRET": "HEADPLANE_COOKIE_SECRET",
    "CHANGE_ME_HEADSCALE_API_KEY": "HEADSCALE_API_KEY",
    "CHANGE_ME_GOOGLE_OAUTH_CLIENT_ID": "GOOGLE_OAUTH_CLIENT_ID",
    "CHANGE_ME_GOOGLE_OAUTH_CLIENT_SECRET": "GOOGLE_OAUTH_CLIENT_SECRET",
    "CHANGE_ME_MEDIAFLOW_PASSWORD": "MEDIAFLOW_PASSWORD",
    "CHANGE_ME_32_BYTE_COOKIE_SECRET": "OAUTH2_COOKIE_SECRET",
    "CHANGE_ME_STREMTHRU_USER": "STREMTHRU_USER",
    "CHANGE_ME_STREMTHRU_PASSWORD": "STREMTHRU_PASSWORD",
    "CHANGE_ME_64_HEX_VAULT_SECRET": "STREMTHRU_VAULT_SECRET",
    "CHANGE_ME_GITHUB_USERNAME": "GITHUB_USERNAME",
    "CHANGE_ME_GITHBB_USER": "GITHUB_USERNAME",
    "CHANGE_ME_GITHUB_TOKEN": "GITHUB_TOKEN",
    "CHANGE_ME_GITHBB_TOKEN": "GITHUB_TOKEN",
    "CHANGE_ME_HEADSCALE_AUTHKEY": "HEADSCALE_AUTHKEY",
    "CHANGE_ME_PROXMOX_IP": "PROXMOX_IP",
    "CHANGE_ME_SERVER_LAN_IP": "SERVER_LAN_IP",
    "CHANGE_ME_AMP_IP": "AMP_IP",
}

REQUIRED_FIELDS = {
    "BASE_DOMAIN": "Public base domain (example: example.com)",
    "SERVER_LAN_IP": "Docker host LAN IP",
    "LAN_SUBNET": "LAN subnet in CIDR form",
    "ALLOWED_EMAIL": "Google account allowed through OAuth2 Proxy",
    "CLOUDFLARE_API_TOKEN": "Cloudflare DNS API token",
    "WIREGUARD_PRIVATE_KEY": "Mullvad/WireGuard private key",
    "WIREGUARD_ADDRESS_CIDR": "Mullvad/WireGuard tunnel address, including CIDR",
    "TMDB_API_KEY": "TMDB API key",
    "TMDB_ACCESS_TOKEN": "TMDB read access token",
    "TVDB_API_KEY": "TVDB API key",
    "TORBOX_API_KEY": "TorBox API key",
    "GOOGLE_OAUTH_CLIENT_ID": "Google OAuth client ID",
    "GOOGLE_OAUTH_CLIENT_SECRET": "Google OAuth client secret",
}

SECRET_FIELDS = {
    "CLOUDFLARE_API_TOKEN", "WIREGUARD_PRIVATE_KEY", "TMDB_API_KEY",
    "TMDB_ACCESS_TOKEN", "TVDB_API_KEY", "MDBLIST_API_KEY", "GEMINI_API_KEY",
    "ANILIST_CLIENT_SECRET", "TRAKT_CLIENT_SECRET", "TORBOX_API_KEY",
    "GOOGLE_OAUTH_CLIENT_SECRET", "GITHUB_TOKEN", "POSTGRES_PASSWORD",
    "AIOMETADATA_ADMIN_KEY", "AIOMETADATA_ADDON_PASSWORD", "AIO_SECRET_KEY",
    "AIO_PASSWORD", "AIO_CONFIG_ACCESS_KEY", "COMET_ADMIN_PASSWORD",
    "COMET_CONFIG_PASSWORD", "COMET_PUBLIC_API_TOKEN", "COMETNET_API_KEY",
    "COMET_STREAM_PROXY_PASSWORD", "MEDIAFLOW_PASSWORD", "HEADPLANE_COOKIE_SECRET",
    "OAUTH2_COOKIE_SECRET", "STREMTHRU_PASSWORD", "STREMTHRU_VAULT_SECRET",
    "SEANIME_MAIN_PASSWORD", "SEANIME_SHARED_PASSWORD", "HEADSCALE_API_KEY",
    "HEADSCALE_AUTHKEY", "JACKETT_API_KEY",
}

OPTIONAL_FIELDS = {
    "PROXMOX_IP": "Proxmox LAN IP used only by Honey",
    "AMP_IP": "AMP LAN IP used only by Honey",
    "MDBLIST_API_KEY": "MDBList API key",
    "GEMINI_API_KEY": "Gemini API key",
    "ANILIST_CLIENT_ID": "AniList OAuth client ID",
    "ANILIST_CLIENT_SECRET": "AniList OAuth client secret",
    "TRAKT_CLIENT_ID": "Trakt client ID",
    "TRAKT_CLIENT_SECRET": "Trakt client secret",
    "AIOMETADATA_CONFIG_UUID": "AIOMetadata config UUID used for cache warming",
    "AIO_TRUSTED_UUID": "AIOStreams trusted configuration UUID",
    "GITHUB_USERNAME": "GitHub username for StremThru integration",
    "GITHUB_TOKEN": "Fine-grained GitHub token for StremThru integration",
}

AUTO_GENERATORS: dict[str, Callable[[], str]] = {
    "POSTGRES_PASSWORD": lambda: secrets.token_urlsafe(32),
    "AIOMETADATA_ADMIN_KEY": lambda: secrets.token_urlsafe(18),
    "AIOMETADATA_ADDON_PASSWORD": lambda: secrets.token_urlsafe(18),
    "AIO_SECRET_KEY": lambda: secrets.token_hex(32),
    "AIO_PASSWORD": lambda: secrets.token_urlsafe(18),
    "AIO_CONFIG_ACCESS_KEY": lambda: secrets.token_urlsafe(12),
    "COMET_ADMIN_PASSWORD": lambda: secrets.token_urlsafe(20),
    "COMET_PUBLIC_API_TOKEN": lambda: secrets.token_urlsafe(32),
    "COMET_STREAM_PROXY_PASSWORD": lambda: secrets.token_urlsafe(20),
    "MEDIAFLOW_PASSWORD": lambda: secrets.token_urlsafe(20),
    "HEADPLANE_COOKIE_SECRET": lambda: secrets.token_hex(16),
    "OAUTH2_COOKIE_SECRET": lambda: secrets.token_hex(16),
    "STREMTHRU_PASSWORD": lambda: secrets.token_urlsafe(18),
    "STREMTHRU_VAULT_SECRET": lambda: secrets.token_hex(32),
    "SEANIME_MAIN_PASSWORD": lambda: secrets.token_urlsafe(18),
    "SEANIME_SHARED_PASSWORD": lambda: secrets.token_urlsafe(18),
}

DEFAULTS = {
    "TIMEZONE": "Europe/Rome",
    "AIO_USER": "admin",
    "STREMTHRU_USER": "admin",
    "HEADSCALE_USER": "admin",
    "AUTO_RUNTIME_KEYS": "true",
}

HOST_SETTING_PREFIXES = {
    "AIOSTREAMS_HOST": "aiostreams",
    "AIOMETADATA_HOST": "aiometadata",
    "MEDIAFLOW_HOST": "mfp",
    "HEADSCALE_HOST": "headscale",
    "STREAMVIX_HOST": "streamv",
    "SEANIME_HOST": "seanime",
    "SEANIME_SHARED_HOST": "shared-seanime",
    "COMETNET_HOST": "cometnet",
    "STREMTHRU_HOST": "stremthru",
    "PORTAINER_HOST": "portainer",
    "JACKETTIO_HOST": "jackettio",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SystemExit(f"{path}:{lineno}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{lineno}: invalid quoted value: {exc}") from exc
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        values[key] = value
    return values


def quote_env(value: str) -> str:
    if value == "":
        return ""
    if re.fullmatch(r"[A-Za-z0-9_./:@%+,=*?\-]+", value):
        return value
    return json.dumps(value)


def write_setup_env(values: dict[str, str]) -> None:
    order = [
        "BASE_DOMAIN", "SERVER_LAN_IP", "LAN_SUBNET", "TAILNET_DOMAIN",
        *HOST_SETTING_PREFIXES.keys(),
        "PROXMOX_IP", "AMP_IP", "ALLOWED_EMAIL", "TIMEZONE",
        "AIO_USER", "AIO_PASSWORD", "AIO_CONFIG_ACCESS_KEY",
        "STREMTHRU_USER", "STREMTHRU_PASSWORD",
        "SEANIME_MAIN_PASSWORD", "SEANIME_SHARED_PASSWORD",
        "CLOUDFLARE_API_TOKEN", "WIREGUARD_PRIVATE_KEY", "WIREGUARD_ADDRESS_CIDR",
        "TMDB_API_KEY", "TMDB_ACCESS_TOKEN", "TVDB_API_KEY",
        "MDBLIST_API_KEY", "GEMINI_API_KEY", "ANILIST_CLIENT_ID", "ANILIST_CLIENT_SECRET",
        "TRAKT_CLIENT_ID", "TRAKT_CLIENT_SECRET", "TORBOX_API_KEY",
        "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET",
        "GITHUB_USERNAME", "GITHUB_TOKEN", "AIOMETADATA_CONFIG_UUID", "AIO_TRUSTED_UUID",
        "POSTGRES_PASSWORD", "AIOMETADATA_ADMIN_KEY", "AIOMETADATA_ADDON_PASSWORD",
        "AIO_SECRET_KEY", "COMET_ADMIN_PASSWORD", "COMET_CONFIG_PASSWORD",
        "COMET_PUBLIC_API_TOKEN", "COMETNET_API_KEY", "COMET_STREAM_PROXY_PASSWORD",
        "MEDIAFLOW_PASSWORD", "HEADPLANE_COOKIE_SECRET", "OAUTH2_COOKIE_SECRET",
        "STREMTHRU_VAULT_SECRET", "HEADSCALE_USER", "HEADSCALE_API_KEY",
        "HEADSCALE_AUTHKEY", "JACKETT_API_KEY", "AUTO_RUNTIME_KEYS",
    ]
    seen = set(order)
    order.extend(sorted(k for k in values if k not in seen))
    lines = [
        "# LOCAL SECRET CONFIGURATION FOR stream-stack",
        "# Generated/updated by ./setup.sh. This file is gitignored and chmod 600.",
        "# Do not commit or share it.", "",
    ]
    for key in order:
        if key in values:
            lines.append(f"{key}={quote_env(values[key])}")
    SETUP_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(SETUP_FILE, 0o600)


def prompt_value(key: str, prompt: str, *, secret: bool, required: bool) -> str:
    suffix = "" if required else " (optional, Enter to skip)"
    while True:
        value = (getpass.getpass if secret else input)(f"{prompt}{suffix}: ").strip()
        if value or not required:
            return value
        print("A value is required.")


def bool_value(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def discover_unknown_template_settings() -> dict[str, str]:
    found: dict[str, str] = {}
    if not DATA.exists():
        return found
    for src in DATA.rglob("*.example"):
        try:
            text = src.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token in set(PLACEHOLDER_RE.findall(text)):
            if token == "CHANGE_ME_SEANIME_PASSWORD" or token in TOKEN_TO_SETTING:
                continue
            found[token] = token.removeprefix("CHANGE_ME_")
    return found


def looks_secret(name: str) -> bool:
    upper = name.upper()
    return any(part in upper for part in ("PASSWORD", "TOKEN", "SECRET", "PRIVATE_KEY", "API_KEY", "AUTHKEY"))


def validate_core(values: dict[str, str]) -> None:
    domain = values["BASE_DOMAIN"].strip().lower().rstrip(".")
    if "://" in domain or "/" in domain or " " in domain or "." not in domain:
        raise SystemExit("BASE_DOMAIN must be a bare DNS domain, for example example.com")
    values["BASE_DOMAIN"] = domain
    try:
        ipaddress.ip_address(values["SERVER_LAN_IP"])
    except ValueError as exc:
        raise SystemExit(f"Invalid SERVER_LAN_IP: {exc}") from exc
    try:
        ipaddress.ip_network(values["LAN_SUBNET"], strict=False)
    except ValueError as exc:
        raise SystemExit(f"Invalid LAN_SUBNET: {exc}") from exc
    if "@" not in values["ALLOWED_EMAIL"]:
        raise SystemExit("ALLOWED_EMAIL must look like an email address")


def derive_values(values: dict[str, str]) -> None:
    for key, default in DEFAULTS.items():
        if not values.get(key):
            values[key] = default
    base = values.get("BASE_DOMAIN", "").strip().lower().rstrip(".")
    if base:
        if not values.get("TAILNET_DOMAIN"):
            values["TAILNET_DOMAIN"] = f"wg.{base}"
        for key, prefix in HOST_SETTING_PREFIXES.items():
            if not values.get(key):
                values[key] = f"{prefix}.{base}"
    if values.get("SERVER_LAN_IP"):
        if not values.get("PROXMOX_IP"):
            values["PROXMOX_IP"] = values["SERVER_LAN_IP"]
        if not values.get("AMP_IP"):
            values["AMP_IP"] = values["SERVER_LAN_IP"]
    if values.get("COMET_ADMIN_PASSWORD") and not values.get("COMET_CONFIG_PASSWORD"):
        values["COMET_CONFIG_PASSWORD"] = values["COMET_ADMIN_PASSWORD"]
    if values.get("COMET_PUBLIC_API_TOKEN") and not values.get("COMETNET_API_KEY"):
        values["COMETNET_API_KEY"] = values["COMET_PUBLIC_API_TOKEN"]


def collect_values(non_interactive: bool) -> dict[str, str]:
    values = parse_env(SETUP_FILE)
    for key, default in DEFAULTS.items():
        if not values.get(key):
            values[key] = default

    for key, prompt in REQUIRED_FIELDS.items():
        if values.get(key):
            continue
        if non_interactive:
            raise SystemExit(f"Missing required value in setup.env: {key}")
        values[key] = prompt_value(key, prompt, secret=key in SECRET_FIELDS, required=True)

    derive_values(values)
    validate_core(values)

    for key, prompt in OPTIONAL_FIELDS.items():
        if key in values and values[key] != "":
            continue
        if non_interactive:
            values.setdefault(key, "")
        elif key not in values or values[key] == "":
            values[key] = prompt_value(key, prompt, secret=key in SECRET_FIELDS, required=False)

    for token, key in sorted(discover_unknown_template_settings().items()):
        TOKEN_TO_SETTING[token] = key
        if values.get(key):
            continue
        if non_interactive:
            raise SystemExit(f"New template placeholder {token} requires setup.env value {key}")
        values[key] = prompt_value(
            key, f"Value for new template placeholder {token}",
            secret=looks_secret(key), required=True,
        )

    for key, generator in AUTO_GENERATORS.items():
        if not values.get(key):
            values[key] = generator()
            log(f"generated: {key}")

    if not values.get("COMET_CONFIG_PASSWORD"):
        values["COMET_CONFIG_PASSWORD"] = values["COMET_ADMIN_PASSWORD"]
    if not values.get("COMETNET_API_KEY"):
        values["COMETNET_API_KEY"] = values["COMET_PUBLIC_API_TOKEN"]
    if not values.get("AIOMETADATA_ADDON_PASSWORD"):
        values["AIOMETADATA_ADDON_PASSWORD"] = values["AIOMETADATA_ADMIN_KEY"]

    derive_values(values)
    return values


def run_bootstrap() -> None:
    if not BOOTSTRAP.exists():
        raise SystemExit(f"Missing {BOOTSTRAP}")
    subprocess.run(["bash", str(BOOTSTRAP)], cwd=ROOT, check=True)


def generated_targets() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for src in sorted(DATA.rglob("*.example")):
        pairs.append((src, Path(str(src)[:-len(".example")])))
    return pairs


def path_specific_token(path: Path, token: str, values: dict[str, str]) -> str | None:
    rel = path.relative_to(ROOT).as_posix()
    if token == "CHANGE_ME_SEANIME_PASSWORD":
        if "/main/" in rel:
            return values["SEANIME_MAIN_PASSWORD"]
        if "/shared/" in rel:
            return values["SEANIME_SHARED_PASSWORD"]
    return None


def text_replacements(values: dict[str, str]) -> dict[str, str]:
    return {
        "you@example.com": values["ALLOWED_EMAIL"],
        "shared-seanime.example.com": values["SEANIME_SHARED_HOST"],
        "aiometadata.example.com": values["AIOMETADATA_HOST"],
        "aiostreams.example.com": values["AIOSTREAMS_HOST"],
        "cometnet.example.com": values["COMETNET_HOST"],
        "headscale.example.com": values["HEADSCALE_HOST"],
        "portainer.example.com": values["PORTAINER_HOST"],
        "stremthru.example.com": values["STREMTHRU_HOST"],
        "seanime.example.com": values["SEANIME_HOST"],
        "streamv.example.com": values["STREAMVIX_HOST"],
        "mfp.example.com": values["MEDIAFLOW_HOST"],
        "tailnet.example.com": values["TAILNET_DOMAIN"],
        "aio.example.com": values["AIOSTREAMS_HOST"],
        "jackettio.example.com": values["JACKETTIO_HOST"],
        "*.example.com": f"*.{values['BASE_DOMAIN']}",
        "192.168.1.0/24": values["LAN_SUBNET"],
        "192.168.1.10": values["SERVER_LAN_IP"],
        "wg.net": values["TAILNET_DOMAIN"],
        "Europe/Rome": values["TIMEZONE"],
        "example.com": values["BASE_DOMAIN"],
    }


def render_templates(values: dict[str, str], *, allow_runtime_blanks: bool) -> set[str]:
    unknown: set[str] = set()
    replacements = text_replacements(values)

    for src, dst in generated_targets():
        text = src.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)

        for token in sorted(set(PLACEHOLDER_RE.findall(text))):
            specific = path_specific_token(dst, token, values)
            if specific is not None:
                text = text.replace(token, specific)
                continue
            setting = TOKEN_TO_SETTING.get(token)
            if setting is None:
                unknown.add(token)
                continue
            value = values.get(setting, "")
            if value:
                text = text.replace(token, value)
            elif allow_runtime_blanks and setting in {"JACKETT_API_KEY", "HEADSCALE_API_KEY", "HEADSCALE_AUTHKEY"}:
                text = text.replace(token, "")
            elif setting in OPTIONAL_FIELDS:
                text = text.replace(token, "")
            else:
                unknown.add(token)

        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")

    return unknown


def docker_available() -> bool:
    return shutil.which("docker") is not None and subprocess.run(
        ["docker", "compose", "version"], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0


def docker(*args: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args], cwd=ROOT, check=check, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def wait_for_headscale(timeout: int = 120) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = docker("exec", "headscale", "headscale", "health", check=False, capture=True)
        if result.returncode == 0:
            return True
        time.sleep(2)
    return False


def discover_jackett_api_key(values: dict[str, str]) -> None:
    if values.get("JACKETT_API_KEY"):
        return
    candidates = [
        DATA / "jackett" / "data" / "Jackett" / "ServerConfig.json",
        DATA / "jackett" / "data" / "ServerConfig.json",
    ]
    deadline = time.time() + 120
    cfg = candidates[0]
    while time.time() < deadline:
        found = next((p for p in candidates if p.exists() and p.stat().st_size), None)
        if found is not None:
            cfg = found
            break
        time.sleep(2)
    if not cfg.exists() or not cfg.stat().st_size:
        log("warning: Jackett did not create ServerConfig.json; API key still needs to be supplied.")
        return
    try:
        obj = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"warning: cannot parse {cfg}: {exc}")
        return
    key = obj.get("APIKey") or obj.get("ApiKey") or obj.get("api_key")
    if key:
        values["JACKETT_API_KEY"] = str(key)
        log("detected: JACKETT_API_KEY")
    else:
        log("warning: Jackett API key was not found in ServerConfig.json")


def ensure_headscale_user(username: str) -> None:
    result = docker("exec", "headscale", "headscale", "users", "list", check=False, capture=True)
    if result.returncode == 0 and username in result.stdout:
        return
    created = docker("exec", "headscale", "headscale", "users", "create", username, check=False, capture=True)
    if created.returncode != 0:
        again = docker("exec", "headscale", "headscale", "users", "list", check=False, capture=True)
        if again.returncode != 0 or username not in again.stdout:
            raise RuntimeError(created.stderr.strip() or "could not create Headscale user")


def generate_headscale_keys(values: dict[str, str]) -> None:
    if values.get("HEADSCALE_API_KEY") and values.get("HEADSCALE_AUTHKEY"):
        return
    if not wait_for_headscale():
        log("warning: Headscale did not become ready; API/pre-auth keys still need to be supplied.")
        return
    username = values.get("HEADSCALE_USER", "admin")
    try:
        ensure_headscale_user(username)
    except RuntimeError as exc:
        log(f"warning: {exc}")
        return

    if not values.get("HEADSCALE_API_KEY"):
        result = docker("exec", "headscale", "headscale", "apikeys", "create", "--expiration", "999d", check=False, capture=True)
        if result.returncode == 0 and result.stdout.strip():
            values["HEADSCALE_API_KEY"] = result.stdout.strip().splitlines()[-1].strip()
            log("generated: HEADSCALE_API_KEY")
        else:
            log("warning: could not auto-generate Headscale API key")

    if not values.get("HEADSCALE_AUTHKEY"):
        result = docker(
            "exec", "headscale", "headscale", "preauthkeys", "create",
            "--user", username, "--expiration", "24h", check=False, capture=True,
        )
        if result.returncode != 0:
            user_id = None
            listing = docker("exec", "headscale", "headscale", "users", "list", "-o", "json", check=False, capture=True)
            if listing.returncode == 0:
                try:
                    users = json.loads(listing.stdout)
                    if isinstance(users, dict):
                        users = users.get("users", [])
                    for item in users:
                        if str(item.get("name", "")) == username:
                            user_id = item.get("id")
                            break
                except Exception:
                    pass
            if user_id is not None:
                result = docker(
                    "exec", "headscale", "headscale", "preauthkeys", "create",
                    "--user", str(user_id), "--expiration", "24h", check=False, capture=True,
                )
        if result.returncode == 0 and result.stdout.strip():
            values["HEADSCALE_AUTHKEY"] = result.stdout.strip().splitlines()[-1].strip()
            log("generated: HEADSCALE_AUTHKEY")
        else:
            log("warning: could not auto-generate Headscale pre-auth key")


def bootstrap_runtime_keys(values: dict[str, str]) -> None:
    needs = not values.get("JACKETT_API_KEY") or not values.get("HEADSCALE_API_KEY") or not values.get("HEADSCALE_AUTHKEY")
    if not needs or not bool_value(values.get("AUTO_RUNTIME_KEYS", "true")):
        return
    if not docker_available():
        log("warning: Docker Compose is not available; runtime-generated Jackett/Headscale keys were not created.")
        return

    log("Starting only Gluetun, Headscale and Jackett to obtain runtime-generated keys...")
    result = subprocess.run(["docker", "compose", "up", "-d", "gluetun", "headscale", "jackett"], cwd=ROOT, text=True)
    if result.returncode != 0:
        log("warning: bootstrap services could not be started. Runtime keys remain pending.")
        return
    discover_jackett_api_key(values)
    generate_headscale_keys(values)


def find_unresolved() -> list[tuple[Path, str]]:
    problems: list[tuple[Path, str]] = []
    for _, dst in generated_targets():
        if not dst.exists():
            continue
        try:
            text = dst.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token in sorted(set(PLACEHOLDER_RE.findall(text))):
            problems.append((dst, token))
        if "example.com" in text:
            problems.append((dst, "example.com"))
        if "192.168.1.0/24" in text or "192.168.1.10" in text:
            problems.append((dst, "example LAN value"))
    return problems


def compose_validate() -> bool:
    if not docker_available():
        log("warning: Docker Compose not installed; skipped `docker compose config --quiet`.")
        return True
    return subprocess.run(["docker", "compose", "config", "--quiet"], cwd=ROOT).returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure the entire stream-stack from one local setup.env file.")
    parser.add_argument("--non-interactive", action="store_true", help="Do not prompt; fail if a required setup.env value is missing.")
    parser.add_argument("--no-runtime-keys", action="store_true", help="Do not start Headscale/Jackett to auto-create runtime keys.")
    args = parser.parse_args()

    if not SETUP_FILE.exists() and SETUP_EXAMPLE.exists():
        shutil.copy2(SETUP_EXAMPLE, SETUP_FILE)
        os.chmod(SETUP_FILE, 0o600)
        log("created: setup.env (gitignored, mode 600)")

    values = collect_values(args.non_interactive)
    if args.no_runtime_keys:
        values["AUTO_RUNTIME_KEYS"] = "false"

    run_bootstrap()
    unknown = render_templates(values, allow_runtime_blanks=True)
    if unknown:
        log("warning: template placeholders without a known mapping:")
        for token in sorted(unknown):
            log(f"  - {token}")

    bootstrap_runtime_keys(values)

    unknown = render_templates(values, allow_runtime_blanks=False)
    write_setup_env(values)

    problems = find_unresolved()
    for token in sorted(unknown):
        problems.append((ROOT, token))

    if problems:
        print("\nConfiguration is not complete:")
        for path, problem in problems:
            rel = path.relative_to(ROOT) if path != ROOT else Path(".")
            print(f"  - {rel}: {problem}")
        print("\nFill the missing value(s) in setup.env and run ./setup.sh again.")
        return 2

    if not compose_validate():
        print("\nDocker Compose validation failed. No full-stack start was attempted.")
        return 3

    print("\nConfiguration complete.")
    print("All generated runtime files are populated from setup.env and contain no CHANGE_ME_* values.")
    print("setup.env is local-only, gitignored and mode 600.")
    print("\nNext:")
    print("  1. Configure Nginx Proxy Manager / certificates using docs/NPM.md.")
    print("  2. Complete the AdGuard first-run wizard.")
    print("  3. Add your Jackett indexers.")
    print("  4. Import your sanitized AIOStreams JSON configuration.")
    print("  5. Run: docker compose --profile all up -d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
