@echo off
chcp 65001 >nul
title JARVIS EXE BUILD
cd /d "%~dp0"
echo === Сборка JARVIS в EXE ===
python -m pip install -U pyinstaller
pyinstaller --clean --onefile --name Jarvis ^
  --add-data "profile.md;." ^
  --add-data "config.json;." ^
  --add-data "commands.json;." ^
  --hidden-import pyttsx3.drivers ^
  --hidden-import pyttsx3.drivers.sapi5 ^
  jarvis.py
if errorlevel 1 (
  echo.
  echo ОШИБКА СБОРКИ.
  pause
  exit /b 1
)
echo.
echo Готово: dist\Jarvis.exe
echo Данные EXE будут храниться в %%APPDATA%%\Jarvis\data
pause
