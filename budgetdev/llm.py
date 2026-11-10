from dataclasses import dataclass, field
from typing import Any


class LLMError(RuntimeError):
    """Raised when the Bifrost request cannot be completed."""


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    raw_model: str = ""


class BifrostClient:
    def __init__(self, base_url: str, api_key: str):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("The openai package is required to use BifrostClient") from exc
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def chat(self, messages, model, tools=None) -> LLMResponse:
        try:
            response = self._client.chat.completions.create(
                model=model, messages=messages, tools=tools or None
            )
        except Exception as exc:
            raise LLMError(str(exc)) from exc
        choice = response.choices[0]
        message = choice.message
        usage = getattr(response, "usage", None)
        tool_calls = []
        for call in getattr(message, "tool_calls", None) or []:
            function = call.function
            arguments = function.arguments
            if isinstance(arguments, str):
                import json
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            tool_calls.append({"id": call.id, "name": function.name, "arguments": arguments})
        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        total = int(getattr(usage, "total_tokens", prompt + completion) or 0)
        return LLMResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
            raw_model=getattr(response, "model", model) or model,
        )
