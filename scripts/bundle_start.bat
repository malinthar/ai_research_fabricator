@echo off
echo Starting bundled installer+launcher...

where python >nul 2>nul
if %errorlevel% neq 0 (
  echo Error: Python is not installed. Please install Python 3.10+ and try again.
  pause
  exit /b 1
)

rem Upgrade pip and install package to user site
python -m pip install --upgrade pip setuptools wheel --user
python -m pip install . --user

rem Try to run installed console script, otherwise run module directly
where false-research-agent >nul 2>nul
if %errorlevel%==0 (
  false-research-agent web %*
  exit /b %errorlevel%
)

python -m false_research_agent web %*
