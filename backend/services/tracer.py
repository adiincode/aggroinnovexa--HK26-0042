import json
import os
import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).with_name("_tracer_runner.py")
MAX_CODE_CHARS = 5000


def trace_code(code: str, timeout: int = 6) -> dict:
    if len(code) > MAX_CODE_CHARS:
        return {"steps": [], "output": "", "error": "Code too long (max 5000 characters)", "truncated": False}
    try:
        proc = subprocess.run(
            [sys.executable, str(RUNNER)],
            input=code,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired:
        return {"steps": [], "output": "", "error": "Time limit exceeded (possible infinite loop)", "truncated": False}

    lines = proc.stdout.strip().splitlines()
    if proc.returncode != 0 or not lines:
        return {"steps": [], "output": "", "error": (proc.stderr or "Execution failed")[-300:], "truncated": False}
    return json.loads(lines[-1])