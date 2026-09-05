import tempfile
import unittest
from pathlib import Path
from core.agent_tools import Tool, ToolRegistry
from core.memory import MemoryStore
from core.model_router import ModelRouter
from core.state import RuntimeState, RuntimeStateMachine, CancellationToken

class ArchitectureTests(unittest.TestCase):
    def test_confirmation_roundtrip(self):
        registry = ToolRegistry()
        registry.register(Tool("danger", "Опасное действие", {"type":"object","properties":{}}, lambda: "done", "confirm"))
        self.assertIn("CONFIRMATION", registry.execute("danger", {}).upper())
        self.assertEqual(registry.confirm_pending(True), "done")
        self.assertFalse(registry.has_pending())

    def test_confirmation_cancel(self):
        registry = ToolRegistry()
        registry.register(Tool("danger", "Опасное действие", {"type":"object","properties":{}}, lambda: "done", "confirm"))
        registry.execute("danger", {})
        self.assertEqual(registry.confirm_pending(False), "Действие отменено.")

    def test_memory_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            store = MemoryStore(Path(d) / "memory.db")
            store.add("Максим предпочитает русский язык", "preference")
            self.assertTrue(store.search("русский язык"))
            store.clear()
            self.assertEqual(store.search("русский"), [])

    def test_model_router(self):
        router = ModelRouter({"main":"main", "cheap":"cheap", "research":"research"})
        self.assertEqual(router.select("привет"), "cheap")
        self.assertEqual(router.select("найди актуальные новости AI"), "research")
        self.assertEqual(router.select("открой браузер и выполни задачу"), "main")

    def test_runtime_and_cancellation(self):
        state = RuntimeStateMachine()
        self.assertEqual(state.state, RuntimeState.IDLE)
        state.set(RuntimeState.SPEAKING)
        state.interrupt()
        self.assertEqual(state.state, RuntimeState.INTERRUPTED)
        token = CancellationToken()
        self.assertFalse(token.cancelled)
        token.cancel()
        self.assertTrue(token.cancelled)
        token.reset()
        self.assertFalse(token.cancelled)

if __name__ == "__main__":
    unittest.main()
