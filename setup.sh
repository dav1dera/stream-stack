#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Serve Python 3 (Ubuntu: sudo apt-get install -y python3)" >&2
  exit 1
fi

NO_NPM=0
NON_INTERACTIVE=0
CORE_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --no-npm)
      NO_NPM=1
      ;;
    --non-interactive)
      NON_INTERACTIVE=1
      CORE_ARGS+=("$arg")
      ;;
    *)
      CORE_ARGS+=("$arg")
      ;;
  esac
done

if [[ ! -f "$ROOT/setup.env" ]]; then
  cp "$ROOT/setup.env.example" "$ROOT/setup.env"
  chmod 600 "$ROOT/setup.env"
  echo "creato: setup.env (ignorato da Git, mode 600)"
fi

if (( ! NON_INTERACTIVE )); then
  python3 "$ROOT/scripts/domain_setup.py"
fi

# Completa hostname/segreti introdotti dalla topologia corrente
# (EasyProxy, TvVoo e AIOManager) prima del renderer generale.
python3 "$ROOT/scripts/current_defaults.py"

if [[ -f "$ROOT/setup.env" ]]; then
  npm_flag="$(awk -F= '/^[[:space:]]*AUTO_CONFIGURE_NPM=/{v=$2} END{gsub(/[[:space:]\"'"'"']/,"",v); print tolower(v)}' "$ROOT/setup.env")"
  case "$npm_flag" in
    false|0|no|off)
      NO_NPM=1
      ;;
  esac
fi

if (( NO_NPM )); then
  python3 "$ROOT/scripts/configure.py" "${CORE_ARGS[@]}"
  echo
  echo "Automazione Nginx Proxy Manager saltata."
  echo "Consulta docs/NPM.md per l'equivalente manuale."
  exit 0
fi

python3 "$ROOT/scripts/configure.py" "${CORE_ARGS[@]}" | sed \
  's#  1\. Configure Nginx Proxy Manager / certificates using docs/NPM.md\.#  1. Nginx Proxy Manager / certificates will be configured automatically next.#'

echo
echo "Applicazione configurazione Nginx Proxy Manager..."
python3 "$ROOT/scripts/npm_current.py"

echo
echo "Configurazione one-shot completata."
echo "Restano gli stati applicativi: AdGuard, indexer Jackett e import JSON sanitizzato AIOStreams."
