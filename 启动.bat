@echo off
chcp 65001>nul
cd /d %~dp0
python scope.py
if errorlevel 1 pause
