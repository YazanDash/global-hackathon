from budgetdev.tools.tests import run_tests


def test_compressed_test_output(workspace):
    result = run_tests(cwd=workspace)
    assert "Tests: 0 passed, 1 failed." in result
    assert "FAILED" not in result


def test_ansi_is_stripped(monkeypatch, tmp_path):
    import subprocess
    class Result:
        stdout = "\x1b[31m1 failed\x1b[0m"
        stderr = ""
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Result())
    assert "\x1b[" not in run_tests(cwd=tmp_path)
