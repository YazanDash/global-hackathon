import re
import subprocess


def run_tests(test_filter=None, cwd=".") -> str:
    command = ["pytest"]
    if test_filter:
        command.append(test_filter)
    command.append("-q")
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=120)
        output = result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        return "Tests: 0 passed, 1 failed.\nFailed tests:\n- pytest timeout"
    output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
    passed = re.search(r"(\d+) passed", output)
    failed = re.search(r"(\d+) failed", output)
    failed_names = re.findall(r"^FAILED\s+(\S+)", output, re.MULTILINE)[:10]
    errors = []
    for line in output.splitlines():
        if line.startswith(("E ", "ERROR")) and line.strip() not in errors:
            errors.append(line.strip())
    report = f"Tests: {int(passed.group(1)) if passed else 0} passed, {int(failed.group(1)) if failed else 0} failed."
    if failed_names:
        report += "\nFailed tests:\n" + "\n".join(f"- {name}" for name in failed_names)
    if errors:
        report += "\nFirst relevant errors:\n" + "\n".join(f"- {line}" for line in errors[:10])
    return report
