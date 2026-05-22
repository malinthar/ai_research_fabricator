#!/usr/bin/env bash
set -euo pipefail

# If package not importable, install it into the current Python environment
if ! python3 -c "import false_research_agent" >/dev/null 2>&1; then
  echo "Package not found — installing with pip..."
  python3 -m pip install .
fi

if command -v false-research-agent >/dev/null 2>&1; then
  exec false-research-agent web "$@"
fi

exec python3 -m false_research_agent web "$@"
