#!/usr/bin/env bash
set -euo pipefail

echo "Starting bundled installer+launcher..."

# Choose python executable
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Error: Python is not installed. Please install Python 3.10+ and try again." >&2
  exit 1
fi

echo "Using $PY"

echo "Upgrading pip/setuptools/wheel (user install)..."
$PY -m pip install --upgrade pip setuptools wheel --user

echo "Installing package into the current user environment..."
$PY -m pip install . --user

echo "Launching the web app..."

if command -v false-research-agent >/dev/null 2>&1; then
  exec false-research-agent web
else
  exec $PY -m false_research_agent web
fi
