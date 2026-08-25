@echo off
chcp 65001 >nul
echo === Сборка JARVIS в один EXE ===
pip install pyinstaller -q
pyinstaller --onefile --name Jarvis ^
  --add-data "profile.md;." ^
  --add-data "config.json;." ^
  --add-data "commands.json;." ^
  --hidden-import pyaudio ^
  --hidden-import pyttsx3.drivers ^
  --hidden-import pyttsx3.drivers.sapi5 ^
  jarvis.py
echo.
echo Готово! EXE лежит в папке dist\Jarvis.exe
pause
