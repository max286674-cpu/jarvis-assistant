# Jarvis — персональный AI-ассистент для Windows 11

Jarvis — голосовой AI-ассистент с русским диалогом, OpenRouter, tool-calling, долговременной памятью, безопасным доступом к файлам, браузером, Windows-действиями, Telegram, погодой, новостями, криптой и тендерным радаром.

## Архитектура

```text
Микрофон
   ↓
RMS endpointing + optional Silero VAD
   ↓
faster-whisper (local) / Google fallback
   ↓
Brain + model routing
   ├── cheap model: простой диалог
   ├── main model: агент и действия
   └── research model: свежие данные / поиск
   ↓
OpenRouter tool-calling loop
   ├── Windows
   ├── разрешённые файлы
   ├── браузер Playwright
   ├── web search
   ├── память
   ├── задачи
   ├── Telegram
   ├── крипта
   └── тендеры
   ↓
Interruptible TTS
   ↓
Новый голос пользователя может перебить озвучку
```

## Что исправлено

- Свободная речь направляется в AI-агент, а не в большой набор regex-команд.
- OpenRouter работает через настоящий tool-calling цикл.
- Русский язык задан как основной язык ассистента.
- Динамические ответы по умолчанию не кэшируются.
- Долговременная память хранится в SQLite с FTS5, когда FTS5 доступен.
- Опасные действия требуют отдельного подтверждения и не могут самопроизвольно повториться в tool loop.
- Произвольный shell отключён: компьютер контролируется отдельными разрешёнными инструментами.
- Доступ к Desktop/Documents/Downloads защищён от path traversal.
- Добавлен Playwright browser agent как опциональный компонент.
- Локальный STT: faster-whisper; Silero VAD подключается при установке voice stack.
- TTS запускается отдельно и может быть остановлен во время речи.
- CI проверяет Python 3.11/3.12 на Ubuntu и Windows.

## Установка Windows 11

Рекомендуется Python 3.11 или 3.12.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

### Локальный голосовой стек

Для более быстрой и приватной расшифровки установи:

```powershell
pip install -r requirements-voice.txt
```

После установки Jarvis попробует использовать faster-whisper и Silero VAD автоматически. При проблеме с локальным STT остаётся Google fallback.

Первый запуск faster-whisper может скачать модель. Размер модели выбирается через `JARVIS_WHISPER_MODEL`; по умолчанию `small`.

### Браузерный агент

Для управления страницами через Playwright:

```powershell
pip install playwright
playwright install chromium
```

Если Playwright не установлен, остальные функции Jarvis продолжают работать.

### Telegram voice

Для обработки голосовых сообщений Telegram нужен FFmpeg:

```powershell
winget install Gyan.FFmpeg
ffmpeg -version
```

## Настройка OpenRouter

Скопируй `.env.example` в `.env` и укажи ключ:

```text
OPENROUTER_API_KEY=твой_ключ
JARVIS_MODEL=z-ai/glm-5.3-flash
JARVIS_FALLBACK_MODEL=deepseek/deepseek-v4-flash-0731
JARVIS_CHEAP_MODEL=deepseek/deepseek-v4-flash-0731
JARVIS_RESEARCH_MODEL=z-ai/glm-5.3-flash
```

Реальный ключ не должен находиться в `config.json`, исходниках, `profile.md` или GitHub.

## Проверка перед запуском

```powershell
python jarvis.py --check
```

Текстовый режим:

```powershell
python jarvis.py --text
```

Голосовой режим:

```powershell
python jarvis.py
```

## Что проверить

```text
Привет
Что ты умеешь?
Какая погода в Минске?
Открой Google
Создай задачу закончить лабораторную завтра вечером
Запомни, что я предпочитаю русский язык
Найди свежие новости по AI
```

## Диалог и перебивание

Jarvis работает в full-duplex режиме на уровне приложения: микрофон продолжает работать во время озвучки, а новый распознанный фрагмент может остановить текущий TTS и передать управление новому запросу.

Для реального использования лучше всего подходят наушники или гарнитура. С колонками микрофон может слышать собственный голос Jarvis; без полноценного аппаратного AEC это создаёт ложные перебивания.

## Доступ к компьютеру

Jarvis имеет расширяемый слой инструментов, но намеренно не выполняет произвольные shell-команды. Это важное ограничение: LLM может ошибиться, а содержимое сайта или файла может содержать prompt injection.

Сейчас доступны безопасные операции с разрешёнными корнями:

- открыть приложение;
- открыть папку;
- открыть URL;
- посмотреть файлы;
- прочитать текстовый файл;
- записать файл — с подтверждением;
- удалить файл — с подтверждением/опасным уровнем;
- открыть страницу через Playwright;
- прочитать видимый текст страницы;
- закрыть браузер.

Разрешённые файловые корни по умолчанию: Desktop, Documents и Downloads. Их можно изменить в `config.json`.

## Подтверждения

Необратимые операции не исполняются сразу. Например, при удалении файла Jarvis сначала создаёт pending action и ждёт отдельное «да» или «подтверждаю». Любая другая реплика не считается подтверждением.

Это распространяется и на отправку Telegram-сообщений и очистку долговременной памяти.

## Telegram

В `.env`:

```text
TELEGRAM_BOT_TOKEN=токен_бота
TELEGRAM_CHAT_ID=твой_chat_id
```

Переменные окружения имеют приоритет над `config.json`.

## Тесты

Локально:

```powershell
python -m compileall -q .
pytest -q
```

GitHub Actions запускает компиляцию и тесты на Python 3.11/3.12 под Windows и Ubuntu.

CI не может физически проверить твой микрофон, динамики, Windows GUI и качество barge-in. Это единственная часть, которую необходимо проверить на реальном компьютере.

## Структура

```text
core/
  actions.py          безопасные Windows-действия
  agent_tools.py      registry + schemas + confirmations
  brain.py            LLM + tool loop + memory/context
  browser.py          optional Playwright agent
  config.py           конфигурация
  duplex_speaker.py   interruptible TTS
  listener.py         microphone + VAD + STT
  local_stt.py        faster-whisper adapter
  memory.py           SQLite/FTS5 memory
  model_router.py     cheap/main/research routing
  router.py           legacy deterministic commands
  state.py            runtime state + cancellation
  web_search.py       web search adapter
  workspace.py        permissioned filesystem

features/
  briefing.py
  code_helper.py
  crypto_watch.py
  news.py
  reminders.py
  sessions.py
  telegram_bot.py
  tenders.py

tests/
  unit and architecture tests
```

## Важное ограничение текущей версии

Это уже не простой голосовой скрипт, а агентная архитектура с инструментами, памятью, подтверждениями и управлением браузером/файлами. При этом полноценный аппаратный acoustic echo cancellation и настоящая генерация TTS по мере прихода токенов LLM зависят от отдельного аудиостека и ещё не являются гарантированными функциями каждого Windows-компьютера. Поэтому текущая версия делает упор на надёжность: interruptible TTS, локальный STT, VAD и безопасные tool boundaries.
