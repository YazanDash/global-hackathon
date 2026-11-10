from budgetdev.tools.files import grep, list_files, read_file, read_lines, write_patch
import pytest


def test_files_and_grep(workspace):
    (workspace / ".git").mkdir()
    (workspace / ".git" / "hidden").write_text("x")
    assert "app.py" in list_files(workspace)
    assert ".git" not in list_files(workspace)
    assert "app.py:1: def add" in grep("def add", workspace)


def test_reading_and_ranges(workspace):
    assert "[truncated" in read_file("app.py", workspace) or "return a - b" in read_file("app.py", workspace)
    assert "1: def add" in read_lines("app.py", 1, 1, workspace)
    with pytest.raises(ValueError):
        read_lines("app.py", 0, 1, workspace)
    with pytest.raises(ValueError):
        read_file("../outside", workspace)


def test_write_patch(workspace):
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a + b
"""
    assert write_patch(diff, workspace) == "Patch applied"
    assert "a + b" in (workspace / "app.py").read_text()
