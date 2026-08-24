#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required (Ubuntu: sudo apt-get install -y python3)" >&2
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

# Create the single local configuration file before the core renderer so the
# interactive hostname step can run before OAuth/service URLs are generated.
if [[ ! -f "$ROOT/setup.env" ]]; then
  cp "$ROOT/setup.env.example" "$ROOT/setup.env"
  chmod 600 "$ROOT/setup.env"
  echo "created: setup.env (gitignored, mode 600)"
fi

if (( ! NON_INTERACTIVE )); then
  python3 "$ROOT/scripts/domain_setup.py"
fi

# Respect AUTO_CONFIGURE_NPM=false from the one source-of-truth file.
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
  echo "Nginx Proxy Manager automation skipped."
  echo "Use docs/NPM.md for the manual equivalent."
  exit 0
fi

# configure.py still prints its legacy NPM-manual next-step line. Replace only
# that line when this wrapper is going to apply the NPM desired state itself.
python3 "$ROOT/scripts/configure.py" "${CORE_ARGS[@]}" | sed \
  's#  1\. Configure Nginx Proxy Manager / certificates using docs/NPM.md\.#  1. Nginx Proxy Manager / certificates will be configured automatically next.#'

echo
echo "Applying Nginx Proxy Manager desired state..."
python3 "$ROOT/scripts/npm_apply.py"

echo
echo "One-shot configuration finished."
echo "You can now continue with AdGuard, Jackett indexers and the sanitized AIOStreams JSON import."
