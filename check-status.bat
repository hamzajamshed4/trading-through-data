@echo off
REM ============================================================
REM  Show the live MetaTrader 5 account status: balance/equity,
REM  open positions, and recent closed trades. Double-click it.
REM
REM  Requires the same one-time setup as run-agent.bat
REM  (venv installed + MT5_LOGIN/MT5_PASSWORD/MT5_SERVER via setx),
REM  and MetaTrader 5 open and logged in.
REM
REM  Optional arg: number of days of history (default 7).
REM      e.g.  check-status.bat 30
REM ============================================================

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo [error] .venv not found in "%~dp0".
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"

set "DAYS=%~1"
if "%DAYS%"=="" set "DAYS=7"

ttd-agent --status --history-days %DAYS%

echo.
pause
