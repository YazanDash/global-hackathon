from pathlib import Path
import os
import subprocess
import tempfile


IGNORED = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}


def _root(root):
    return Path(root).expanduser().resolve()


def _safe_path(path, root="."):
    workspace = _root(root)
    candidate = (workspace / path).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("Path is outside the target workspace") from exc
    return candidate


def list_files(root="."):
    workspace = _root(root)
    result = []
    for current, dirs, files in os.walk(workspace, followlinks=False):
        dirs[:] = [d for d in dirs if d not in IGNORED]
        for name in sorted(files):
            if name.endswith((".pyc", ".pyo")):
                continue
            result.append(str((Path(current) / name).relative_to(workspace)))
            if len(result) >= 200:
                return "\n".join(result)
    return "\n".join(result)


def grep(pattern, root="."):
    import re
    workspace = _root(root)
    regex = re.compile(pattern)
    matches = []
    for current, dirs, files in os.walk(workspace, followlinks=False):
        dirs[:] = [d for d in dirs if d not in IGNORED]
        for name in files:
            if name.endswith((".pyc", ".pyo")):
                continue
            path = Path(current) / name
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(lines, 1):
                if regex.search(line):
                    matches.append(f"{path.relative_to(workspace)}:{number}: {line}")
                    if len(matches) >= 50:
                        return "\n".join(matches)
    return "\n".join(matches)


def read_file(path, root="."):
    target = _safe_path(path, root)
    lines = target.read_text(encoding="utf-8").splitlines()
    if len(lines) > 400:
        return f"{path}:1-400\n" + "\n".join(f"{i}: {line}" for i, line in enumerate(lines[:400], 1)) + \
            "\n[truncated; use read_lines]"
    return f"{path}:1-{len(lines)}\n" + "\n".join(f"{i}: {line}" for i, line in enumerate(lines, 1))


def read_lines(path, start, end, root="."):
    target = _safe_path(path, root)
    lines = target.read_text(encoding="utf-8").splitlines()
    if start < 1 or end < start or start > len(lines):
        raise ValueError("Invalid line range")
    actual_start = max(1, start - 10)
    actual_end = min(len(lines), end + 10)
    return f"{path}:{start}-{end}\n" + "\n".join(
        f"{i}: {lines[i - 1]}" for i in range(actual_start, actual_end + 1)
    )


def write_patch(diff, root="."):
    workspace = _root(root)
    if not workspace.is_dir():
        raise ValueError("Invalid target workspace")
    for line in diff.splitlines():
        if line.startswith(("--- ", "+++ ")):
            path = line[4:].split("\t", 1)[0].strip()
            if path not in ("/dev/null",) and not path.startswith(("a/", "b/")):
                raise ValueError("Invalid patch path")
            relative = path[2:] if path.startswith(("a/", "b/")) else path
            if relative != "/dev/null":
                _safe_path(relative, workspace)
    if (workspace / ".git").exists():
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".diff", delete=False) as handle:
            handle.write(diff)
            patch_path = handle.name
        try:
            result = subprocess.run(
                ["git", "-C", str(workspace), "apply", "--whitespace=nowarn", patch_path],
                text=True, capture_output=True, timeout=30,
            )
        finally:
            os.unlink(patch_path)
        if result.returncode:
            raise ValueError(result.stderr.strip() or "Patch could not be applied")
        return "Patch applied"
    raise ValueError("write_patch requires a Git workspace")
