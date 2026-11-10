from dataclasses import dataclass, field
from typing import Any, Callable
import json


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def tools(self):
        return list(self._tools.values())

    def openai_definitions(self):
        return [
            {"type": "function", "function": {
                "name": tool.name, "description": tool.description, "parameters": tool.parameters
            }}
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict[str, Any] | str | None = None) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(False, error=f"Unknown tool: {name}")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                return ToolResult(False, error=f"Invalid tool arguments: {exc}")
        try:
            output = tool.handler(**(arguments or {}))
            return output if isinstance(output, ToolResult) else ToolResult(True, str(output))
        except Exception as exc:
            return ToolResult(False, error=str(exc))
