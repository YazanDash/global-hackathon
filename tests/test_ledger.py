def test_ledger_records_calls(ledger):
    ledger.log_llm_call("coder", "step", 2, 3, 5)
    ledger.log_tool_call("grep", {"pattern": "x"}, True, "found", duration_ms=4)
    assert ledger.total_tokens() == 5
    summary = ledger.summary()
    assert summary["llm_calls"] == 1
    assert summary["tool_calls"] == 1
    assert summary["tokens_by_model"] == {"coder": 5}
    assert summary["calls_by_tool"] == {"grep": 1}
