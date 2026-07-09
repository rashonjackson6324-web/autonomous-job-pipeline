#!/usr/bin/env python3
"""Register the pipeline runs with the OS scheduler (Windows Task Scheduler).

Each entry runs the full stage chain. Stages are idempotent, so a run that
overlaps a previous one is harmless.

Uses the argument-list form of subprocess rather than a shell string: both the
interpreter path and the runner path routinely contain spaces, and shell
quoting for schtasks is a reliable source of silently-broken tasks.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "main_pipeline.py"
PYTHON = sys.executable

RUN_TIMES = os.getenv("RUN_TIMES", "07:00,12:00,17:00").split(",")


def register(run_time: str) -> bool:
    task_name = f"JobPipeline_{run_time.replace(':', '')}"
    action = f'"{PYTHON}" "{RUNNER}"'
    result = subprocess.run(
        [
            "schtasks", "/create",
            "/tn", task_name,
            "/tr", action,
            "/sc", "daily",
            "/st", run_time,
            "/f",
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Failed to schedule {task_name}: {result.stderr.strip()}")
        return False
    print(f"Scheduled {task_name} at {run_time}")
    return True


if __name__ == "__main__":
    if not RUNNER.exists():
        sys.exit(f"Runner not found: {RUNNER}")

    times = [t.strip() for t in RUN_TIMES if t.strip()]
    ok = sum(register(t) for t in times)
    print(f"{ok}/{len(times)} schedules created")
    sys.exit(0 if ok == len(times) else 1)
