#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for the LangChain Python monorepo.
# Installs uv (if missing) and syncs the actively developed packages.
set -euo pipefail

# uv installs here; make sure it is discoverable before and after installation.
export PATH="$HOME/.local/bin:$PATH"

# Install uv if it is not already available.
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

uv --version

# Sync the packages that make up the core development experience.
# Each package is independently versioned with its own lockfile, so sync them
# individually. --all-groups pulls in test, lint, and typing dependencies.
# --frozen matches the repository convention (Makefiles set UV_FROZEN=true) and
# keeps committed lockfiles untouched during setup.
for pkg in core text-splitters langchain_v1; do
  echo "=== Syncing libs/${pkg} ==="
  (cd "libs/${pkg}" && uv sync --all-groups --frozen)
done

echo "LangChain (Python) Cloud Agent environment ready."
