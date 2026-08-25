"""Мозг Джарвиса: Google Gemini (бесплатный тариф) + характер из фильмов."""
from pathlib import Path

import google.generativeai as genai

SYSTEM_PROMPT = """Ты — ДЖАРВИС, персональный AI-ассистент пользователя {user}.
Ты вдохновлён Джарвисом Тони Старка из «Железного человека».

Твой стиль:
- Обращайся к пользователю «сэр» (иногда вариации: «босс», «господин»).
- Ироничный, остроумный, но всегда полезный и точный по делу.
- Уровень сарказма: {sarcasm}/10 (10 = максимум едкости, 0 = сухой официоз).
- Отвечай КРАТКО: 1–4 предложения, если не просят подробно. Это голосовой ассистент.
- Если тебя просят техническую помощь (код, ошибки) — будь точен, приводи конкретику.
- Любые шутки про дедлайны, вкладки браузера и сон уместны.
- Никогда не выходи из роли Джарвиса.

Примеры твоих ответов:
- «К сведению принято, сэр. Ваши вкладки снова победили порядок.»
- «Готово. Как всегда безупречно — это я, если что.»
- «Сэр, кофе я сварить не могу, но мир — могу перезапустить.»"""


class Brain:
    def __init__(self, brain_cfg: dict, user_name: str):
        self.model_name = brain_cfg.get("model", "gemini-1.5-flash")
        self.max_history = brain_cfg.get("max_history", 20)
        key = brain_cfg.get("api_key", "")
        self.enabled = bool(key) and "ВСТАВЬ" not in key
        if self.enabled:
            genai.configure(api_key=key)
            prompt = SYSTEM_PROMPT.format(
                user=user_name,
                sarcasm=brain_cfg.get("sarcasm_level", 7),
            )
            profile_path = Path(__file__).resolve().parent.parent / "profile.md"
            if profile_path.exists():
                prompt += (
                    "\n\n## Досье пользователя (всегда учитывай):\n"
                    + profile_path.read_text(encoding="utf-8")
                )
            self.model = genai.GenerativeModel(
                self.model_name,
                system_instruction=prompt,
            )
            self.chat = self.model.start_chat(history=[])
        else:
            self.model = None
            print("[Мозг: ключ Gemini не задан — работает режим команд без AI]")

    def ask(self, text: str) -> str:
        """Задаёт вопрос с памятью диалога. Возвращает ответ или заглушку."""
        if not self.enabled:
            return ""
        try:
            resp = self.chat.send_message(text)
            history = self.chat.history
            if len(history) > self.max_history * 2:
                trimmed = history[-self.max_history * 2:]
                self.chat = self.model.start_chat(history=trimmed)
            return resp.text.strip()
        except Exception as e:
            print(f"[Ошибка мозга: {e}]")
            return "Сэр, мой нейромодуль дал сбой. Проверьте интернет или ключ API."

    def reset_memory(self) -> None:
        if self.enabled:
            self.chat = self.model.start_chat(history=[])
