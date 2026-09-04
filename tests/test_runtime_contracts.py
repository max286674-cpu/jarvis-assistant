import tempfile
import unittest
from pathlib import Path

from core.agent_tools import Tool, ToolRegistry
from core.memory import MemoryStore
from core.actions import ActionExecutor


class RuntimeContractsTests(unittest.TestCase):
    def test_tool_schema_is_openai_compatible(self):
        registry = ToolRegistry()
        registry.register(Tool("ping", "Проверка", {"type": "object", "properties": {}}, lambda: "pong"))
        schema = registry.schemas()[0]
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "ping")
        self.assertEqual(registry.execute("ping", {}), "pong")

    def test_unknown_tool_does_not_crash(self):
        registry = ToolRegistry()
        self.assertIn("не найден", registry.execute("missing", {}).lower())

    def test_memory_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            store = MemoryStore(Path(td) / "memory.db")
            store.add("Максим предпочитает русский язык")
            self.assertTrue(store.search("русский язык"))
            store.clear()
            self.assertEqual(store.search("русский"), [])

    def test_arbitrary_shell_is_not_available(self):
        executor = ActionExecutor(None)
        result = executor.run({"type": "run_cmd", "command": "whoami"})
        self.assertIn("отключено", result.lower())


if __name__ == "__main__":
    unittest.main()
