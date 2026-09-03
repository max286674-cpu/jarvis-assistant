@echo off
chcp 65001 >nul
title MAX JARVIS
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python jarvis.py
pause
