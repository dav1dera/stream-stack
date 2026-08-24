#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [[ ! -e "$dst" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo "created: ${dst#$ROOT/}"
  fi
}

while IFS= read -r -d '' src; do
  dst="${src%.example}"
  copy_if_missing "$src" "$dst"
done < <(find "$ROOT/data" -type f -name '.env.example' -print0)

copy_if_missing "$ROOT/data/pgbouncer/data/userlist.txt.example" "$ROOT/data/pgbouncer/data/userlist.txt"
copy_if_missing "$ROOT/data/oauth2-proxy/allowed-emails.txt.example" "$ROOT/data/oauth2-proxy/allowed-emails.txt"
copy_if_missing "$ROOT/data/headplane/data/config.yaml.example" "$ROOT/data/headplane/data/config.yaml"
copy_if_missing "$ROOT/data/headscale/data/config/config.yaml.example" "$ROOT/data/headscale/data/config/config.yaml"
copy_if_missing "$ROOT/data/honey/data/config/config.json.example" "$ROOT/data/honey/data/config/config.json"
copy_if_missing "$ROOT/data/seanime/data/main/config/config.toml.example" "$ROOT/data/seanime/data/main/config/config.toml"
copy_if_missing "$ROOT/data/seanime/data/shared/config/config.toml.example" "$ROOT/data/seanime/data/shared/config/config.toml"

mkdir -p \
  "$ROOT/data/adguardhome/data/workdir" \
  "$ROOT/data/adguardhome/data/confdir" \
  "$ROOT/data/aiometadata/data" \
  "$ROOT/data/aiostreams/data" \
  "$ROOT/data/comet/data" \
  "$ROOT/data/headplane/data" \
  "$ROOT/data/headscale/data/lib" \
  "$ROOT/data/headscale/data/run" \
  "$ROOT/data/honey/data/config" \
  "$ROOT/data/jackett/data" \
  "$ROOT/data/npm/data" \
  "$ROOT/data/npm/data/letsencrypt" \
  "$ROOT/data/seanime/data/main/anime" \
  "$ROOT/data/seanime/data/main/downloads" \
  "$ROOT/data/seanime/data/main/config" \
  "$ROOT/data/seanime/data/shared/anime" \
  "$ROOT/data/seanime/data/shared/downloads" \
  "$ROOT/data/seanime/data/shared/config" \
  "$ROOT/data/tailscale/data/state"

echo
echo "Templates copied. Recommended: run ./setup.sh to configure the entire stack from one setup.env file."
echo "Manual check: grep -RIn --exclude='*.example' 'CHANGE_ME_' \"$ROOT/data\""
