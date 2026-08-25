@echo off
chcp 65001 >nul
title JARVIS
cd /d "%~dp0"
python jarvis.py
pause
