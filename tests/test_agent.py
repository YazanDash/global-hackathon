from types import SimpleNamespace

from budgetdev.agent import CodingAgent
from budgetdev.llm import LLMResponse
from budgetdev.tools.base import Tool


def test_agent_executes_tools_and_finishes(registry, ledger, settings):
    registry.register(Tool("one", "one", {"type": "object"}, lambda: "result"))
    responses = iter([
        LLMResponse("", [{"id": "1", "name": "one", "arguments": {}}], total_tokens=2),
        LLMResponse("", [{"id": "2", "name": "finish", "arguments": {
            "explanation": "done", "patch": "diff"}}], total_tokens=3),
    ])
    client = SimpleNamespace(chat=lambda *args, **kwargs: next(responses))
    result = CodingAgent(client, registry, ledger, settings).run("fix it")
    assert result.success and result.patch == "diff"
    assert ledger.summary()["calls_by_tool"] == {"one": 1}


def test_agent_stops_at_limits(registry, ledger, settings):
    settings.max_steps = 1
    client = SimpleNamespace(chat=lambda *args, **kwargs:
        LLMResponse("", [{"name": "unknown", "arguments": {}}], total_tokens=1))
    result = CodingAgent(client, registry, ledger, settings).run("fix")
    assert result.stopped_reason == "max steps exceeded"

    settings.max_steps = 5
    result = CodingAgent(client, registry, ledger, settings).run("fix", max_tokens=0)
    assert result.stopped_reason == "token budget exceeded"
