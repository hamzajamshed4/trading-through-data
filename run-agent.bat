@echo off
REM ============================================================
REM  Easiest way to start the AI MetaTrader 5 agent (Windows).
REM
REM  Prerequisites (one time):
REM    1) Install:   python -m venv .venv ^&^& .venv\Scripts\activate.bat ^&^& pip install -e ".[mt5]"
REM    2) Store credentials once (persist for all future windows):
REM         setx MT5_LOGIN 5055002917
REM         setx MT5_PASSWORD your-password
REM         setx MT5_SERVER MetaQuotes-Demo
REM
REM  Each run: open MetaTrader 5, log in, make sure "Algo Trading"
REM  is enabled (green), then double-click this file.
REM
REM  Optional args:  run-agent.bat SYMBOL TIMEFRAME LOTS
REM      e.g.  run-agent.bat XAUUSD H1 0.01
REM ============================================================

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo [error] .venv not found in "%~dp0".
  echo Create it first:  python -m venv .venv ^&^& .venv\Scripts\activate.bat ^&^& pip install -e ".[mt5]"
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"

if "%MT5_LOGIN%"=="" echo [warn] MT5_LOGIN is not set. Set it once with:  setx MT5_LOGIN your-login
if "%MT5_SERVER%"=="" echo [warn] MT5_SERVER is not set. Set it once with:  setx MT5_SERVER your-server

set "SYMBOL=%~1"
if "%SYMBOL%"=="" set "SYMBOL=XAUUSD"
set "TF=%~2"
if "%TF%"=="" set "TF=H1"
set "LOTS=%~3"
if "%LOTS%"=="" set "LOTS=0.01"

echo.
echo Starting AI MT5 agent:  symbol=%SYMBOL%  timeframe=%TF%  volume=%LOTS%
echo Decisions are appended to agent_log.txt. Close this window or press Ctrl+C to stop.
echo.

:loop
echo ---- %date% %time% ----
ttd-agent --mode live --symbol %SYMBOL% --timeframe %TF% --volume %LOTS% >> agent_log.txt 2>&1
powershell -NoProfile -Command "Get-Content agent_log.txt -Tail 8"
timeout /t 3600 /nobreak >nul
goto loop
