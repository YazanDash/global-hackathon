from dataclasses import dataclass
import json
import time
from typing import Any


SYSTEM_PROMPT = """You are BudgetDev, a token-efficient coding agent.

Your goal is to resolve the user's software issue with the fewest tokens possible while producing a correct, test-passing change.

Rules:
1. Think before acting, but keep your reasoning short.
2. Use list_files or grep only when necessary.
3. Prefer read_lines over read_file.
4. Read only the smallest relevant code range.
5. Make the smallest change that correctly resolves the issue.
6. Run only relevant tests when possible.
7. If tests fail, read the compressed failure output and make one focused correction.
8. Do not rewrite entire files.
9. Do not add unrelated features, comments, refactors, or documentation.
10. When the change is complete and tests pass, call finish."""


@dataclass
class AgentResult:
    success: bool
    final_message: str
    patch: str
    total_tokens: int
    steps_used: int
    stopped_reason: str


class CodingAgent:
    def __init__(self, client, registry, ledger, settings):
        self.client, self.registry, self.ledger, self.settings = client, registry, ledger, settings

    def run(self, issue, max_tokens=None) -> AgentResult:
        budget = self.settings.max_tokens if max_tokens is None else max_tokens
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": issue}]
        total = 0
        for step in range(1, self.settings.max_steps + 1):
            if total >= budget:
                return AgentResult(False, "", "", total, step - 1, "token budget exceeded")
            try:
                response = self.client.chat(
                    messages, self.settings.coder_model,
                    tools=self.registry.openai_definitions() + [self._finish_definition()],
                )
                self.ledger.log_llm_call(self.settings.coder_model, "agent_step",
                                         response.prompt_tokens, response.completion_tokens,
                                         response.total_tokens, True)
            except Exception as exc:
                self.ledger.log_llm_call(self.settings.coder_model, "agent_step", success=False, error=str(exc))
                return AgentResult(False, str(exc), "", total, step, "llm error")
            total += response.total_tokens
            if total > budget:
                return AgentResult(False, "", "", total, step, "token budget exceeded")
            if not response.tool_calls:
                return AgentResult(True, response.content, "", total, step, "model completed")
            for call in response.tool_calls:
                name, args = call.get("name"), call.get("arguments", {})
                if name == "finish":
                    return AgentResult(True, args.get("explanation", ""), args.get("patch", ""),
                                       total, step, "finish")
                started = time.monotonic()
                result = self.registry.execute(name, args)
                self.ledger.log_tool_call(name, args, result.success, result.output,
                                          result.error, (time.monotonic() - started) * 1000)
                messages.append({"role": "assistant", "content": None,
                                 "tool_calls": [_assistant_tool_call(call)]})
                messages.append({"role": "tool", "tool_call_id": call.get("id", name),
                                 "content": _compress(result.output if result.success else result.error or "")})
        return AgentResult(False, "", "", total, self.settings.max_steps, "max steps exceeded")

    @staticmethod
    def _finish_definition():
        return {"type": "function", "function": {
            "name": "finish", "description": "Submit the final explanation and unified diff.",
            "parameters": {"type": "object", "properties": {
                "explanation": {"type": "string"}, "patch": {"type": "string"}
            }, "required": ["explanation", "patch"]}
        }}


def _compress(value: str) -> str:
    return value if len(value) <= 12_000 else value[:12_000] + "\n[output compressed]"


def _assistant_tool_call(call: dict[str, Any]) -> dict[str, Any]:
    arguments = call.get("arguments", {})
    if not isinstance(arguments, str):
        arguments = json.dumps(arguments)
    return {
        "id": call.get("id", ""),
        "type": "function",
        "function": {
            "name": call.get("name", ""),
            "arguments": arguments,
        },
    }
