@echo off
setlocal
chcp 65001 >nul
title JARVIS Setup
cd /d "%~dp0"

echo [1/4] Проверяю Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo Python не найден. Установите Python 3.10+ и включите Add Python to PATH.
  pause
  exit /b 1
)

if not exist .venv (
  echo [2/4] Создаю виртуальное окружение...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [3/4] Обновляю pip и устанавливаю зависимости...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if not exist .env (
  copy /Y .env.example .env >nul
  echo [4/4] Создан .env. Откройте его и вставьте OPENROUTER_API_KEY.
) else (
  echo [4/4] .env уже существует — не трогаю его.
)

echo.
echo Готово. Следующий шаг:
echo 1. Откройте .env
 echo 2. Вставьте OPENROUTER_API_KEY=...
echo 3. Запустите: start.bat
pause
