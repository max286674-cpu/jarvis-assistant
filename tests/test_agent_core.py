import unittest
from unittest.mock import Mock
from core.agent_tools import Tool, ToolRegistry

class AgentCoreTests(unittest.TestCase):
    def test_registry_executes_registered_tool(self):
        r=ToolRegistry(); r.register(Tool("echo","echo",{"type":"object","properties":{"text":{"type":"string"}}},lambda text:f"ok:{text}"))
        self.assertEqual(r.execute("echo",{"text":"hello"}),"ok:hello")

    def test_unknown_tool_is_safe(self):
        r=ToolRegistry()
        self.assertIn("не найден",r.execute("shell",{}))

    def test_schema_is_openai_compatible(self):
        r=ToolRegistry(); r.register(Tool("x","test",{"type":"object","properties":{}},lambda:"x"))
        schema=r.schemas()[0]
        self.assertEqual(schema["type"],"function")
        self.assertEqual(schema["function"]["name"],"x")

if __name__ == "__main__": unittest.main()
