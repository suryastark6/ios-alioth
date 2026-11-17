@echo off
rem Double-click: opens the alioth session menu (logs go to the logs folder).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0alioth-session.ps1"
pause
