@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title MAX JARVIS Setup
cd /d "%~dp0"

echo ============================================
echo   MAX JARVIS - Установка
echo ============================================
echo.

REM ===== Шаг 1: Проверяем Python =====
echo [1/5] Проверяю установленные версии Python...
set "PY_CMD="
set "PY_VERSION="

REM Проверяем через py launcher (рекомендуется)
py -0p >nul 2>&1
if not errorlevel 1 (
    echo Найден Python Launcher. Доступные версии:
    py -0p
    echo.
    
    REM Ищем Python 3.12 (лучшая совместимость с PyAudio - есть готовые wheels)
    for /f "tokens=1 delims= " %%v in ('py -0p 2^>nul ^| findstr /C:"3.12"') do (
        set "PY_CMD=py -3.12"
        set "PY_VERSION=3.12"
    )
    if not defined PY_CMD (
        REM Ищем Python 3.11
        for /f "tokens=1 delims= " %%v in ('py -0p 2^>nul ^| findstr /C:"3.11"') do (
            set "PY_CMD=py -3.11"
            set "PY_VERSION=3.11"
        )
    )
    if not defined PY_CMD (
        REM Ищем Python 3.10
        for /f "tokens=1 delims= " %%v in ('py -0p 2^>nul ^| findstr /C:"3.10"') do (
            set "PY_CMD=py -3.10"
            set "PY_VERSION=3.10"
        )
    )
    if not defined PY_CMD (
        REM Ищем Python 3.13 (если нет 3.10-3.12)
        for /f "tokens=1 delims= " %%v in ('py -0p 2^>nul ^| findstr /C:"3.13"') do (
            set "PY_CMD=py -3.13"
            set "PY_VERSION=3.13"
        )
    )
)

REM Если py launcher не найден или нет подходящей версии - пробуем python
if not defined PY_CMD (
    python --version >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
        set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo [ОШИБКА] Python не найден.
    echo.
    echo Установите Python 3.12 x64 с сайта:
    echo   https://www.python.org/downloads/
    echo.
    echo ВАЖНО: при установке отметьте галочку "Add Python to PATH"
    echo и выберите "py launcher" (устанавливается по умолчанию).
    echo.
    echo После установки запустите setup.bat снова.
    pause
    exit /b 1
)

echo Использую: %PY_CMD% (Python %PY_VERSION%)
echo.

REM ===== Проверка на Python 3.14 =====
echo %PY_VERSION% | findstr /C:"3.14" >nul
if not errorlevel 1 (
    echo [ИНФО] Обнаружен Python 3.14.
    echo Используем sounddevice (вместо pyaudio) — готовые сборки доступны.
    echo.
)

REM ===== Шаг 2: Создаём venv =====
echo [2/5] Создаю виртуальное окружение...
if exist .venv (
    echo Удаляю старую .venv...
    rmdir /s /q .venv
)
%PY_CMD% -m venv .venv
if errorlevel 1 (
    echo [ОШИБКА] Не удалось создать виртуальное окружение.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ОШИБКА] Не удалось активировать виртуальное окружение.
    pause
    exit /b 1
)
echo Готово.
echo.

REM ===== Шаг 3: Обновляем pip и устанавливаем зависимости =====
echo [3/5] Обновляю pip и устанавливаю зависимости (быстро)...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ОШИБКА] Не удалось обновить pip.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости.
    echo.
    echo Попробуйте вручную:
    echo   .venv\Scripts\activate
    echo   python -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo Готово.
echo.

REM ===== Шаг 4: Проверяем sounddevice =====
echo [4/5] Проверяю голосовой стек (sounddevice)...
python -c "import sounddevice; print('sounddevice OK')" >nul 2>&1
if errorlevel 1 (
    echo [ВНИМАНИЕ] sounddevice не установился автоматически.
    echo Пробую установить sounddevice...
    python -m pip install sounddevice numpy
    if errorlevel 1 (
        echo.
        echo [ВНИМАНИЕ] sounddevice тоже не сработал.
        echo.
        echo РЕШЕНИЕ 1: Установите Python 3.12 x64 и запустите setup.bat снова.
        echo   https://www.python.org/downloads/
        echo.
        echo РЕШЕНИЕ 2: Установите PortAudio через vcpkg или MSYS2,
        echo   затем повторите: pip install sounddevice
        echo.
        echo Голосовой режим НЕ будет работать, пока sounddevice не установлен.
        echo Текстовый режим (python jarvis.py --text) будет работать.
        echo.
        set "SOUND_OK=0"
    ) else (
        echo sounddevice установлен.
        set "SOUND_OK=1"
    )
) else (
    echo sounddevice OK.
    set "SOUND_OK=1"
)
echo.

REM ===== Шаг 5: Создаём .env =====
echo [5/5] Настраиваю .env...
if not exist .env (
    copy /Y .env.example .env >nul
    echo Создан .env. Откройте его и вставьте OPENROUTER_API_KEY.
) else (
    echo .env уже существует — не трогаю его.
)
echo.

REM ===== Итоговый отчёт =====
echo ============================================
echo   ИТОГ УСТАНОВКИ
echo ============================================
echo   Python:        %PY_VERSION%
echo   sounddevice:   %SOUND_OK% (1=OK, 0=проблема)
echo   .env:          создан/существует
echo ============================================
echo.
if "%SOUND_OK%"=="0" (
    echo ⚠ ВНИМАНИЕ: sounddevice не установлен. Голосовой режим не будет работать.
    echo   Следуйте инструкциям выше для ручной установки sounddevice.
    echo.
    echo Текстовый режим доступен: python jarvis.py --text
) else (
    echo ✅ Всё готово! Следующие шаги:
    echo   1. Откройте .env и вставьте OPENROUTER_API_KEY
    echo   2. Запустите: start.bat
    echo   3. Проверка: python jarvis.py --check
)
echo.
pause
