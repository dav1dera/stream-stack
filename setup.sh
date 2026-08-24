#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required (Ubuntu: sudo apt-get install -y python3)" >&2
  exit 1
fi

NO_NPM=0
CORE_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --no-npm)
      NO_NPM=1
      ;;
    *)
      CORE_ARGS+=("$arg")
      ;;
  esac
done

if (( NO_NPM )); then
  python3 "$ROOT/scripts/configure.py" "${CORE_ARGS[@]}"
  echo
  echo "Nginx Proxy Manager automation skipped (--no-npm)."
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
