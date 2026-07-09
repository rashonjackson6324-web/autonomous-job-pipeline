"""
Pipeline Master
Single entry point. Runs all checks, then launches pipeline.
Add this to Task Scheduler instead of running pipeline directly.
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent
JOBS_DIR  = Path(os.getenv("JOBS_DIR", REPO_ROOT / "data"))

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    try:
        with open(JOBS_DIR / "logs" / "pipeline_master.log", "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def run_check(module_path: str, label: str) -> bool:
    """Run a check script. Returns True if passed."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / module_path)],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        log(f"✗ {label} FAILED:\n{output[-500:]}")
        return False
    log(f"✓ {label} passed")
    return True

def run_pipeline(script: str) -> bool:
    """Run one stage. Scripts live in the repo; data lives in JOBS_DIR."""
    target = REPO_ROOT / script
    if not target.exists():
        log(f"[FAIL] {script} not found at {target}")
        return False
    log(f"Launching: {script}")
    result = subprocess.run([sys.executable, str(target)], cwd=str(REPO_ROOT))
    if result.returncode != 0:
        log(f"[FAIL] {script} exited {result.returncode}")
        return False
    return True

if __name__ == "__main__":
    log("=== Pipeline master starting ===")
    (JOBS_DIR / "logs").mkdir(parents=True, exist_ok=True)

    checks = [
        ("ops/credential_check.py", "Credentials"),
        ("ops/skyvern_check.py", "Skyvern Limits"),
    ]

    all_passed = True
    for module, label in checks:
        if not run_check(module, label):
            all_passed = False
            break

    if not all_passed:
        log("Pipeline halted — fix issues above before continuing.")
        sys.exit(1)

    log("All checks passed. Launching pipeline...")
    run_pipeline("main_pipeline.py")   # ← your actual pipeline entry point
    log("=== Pipeline run complete ===")
