@echo off
setlocal

rem If package not found, install it
python - <<'PY' >nul 2>&1
import importlib,sys
spec = importlib.util.find_spec('false_research_agent')
sys.exit(0 if spec is not None else 1)
PY
if %errorlevel% neq 0 (
  echo Package not found - installing with pip...
  python -m pip install .
)

where false-research-agent >nul 2>nul
if %errorlevel%==0 (
  false-research-agent web %*
  exit /b %errorlevel%
)

python -m false_research_agent web %*
