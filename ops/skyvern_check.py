# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import requests
from datetime import datetime

# Add to your .env: SKYVERN_API_KEY=your_key

SKYVERN_API_KEY = os.getenv("SKYVERN_API_KEY", "")
SKYVERN_BASE_URL = os.getenv("SKYVERN_BASE_URL", "https://api.skyvern.com/api/v1")

# Thresholds
WARN_THRESHOLD = 0.80   # warn at 80% used
HALT_THRESHOLD = 0.95   # halt pipeline at 95% used

def check_skyvern_limit():
    if not SKYVERN_API_KEY:
        return "warn", "SKYVERN_API_KEY not set in .env — skipping limit check"

    try:
        r = requests.get(
            f"{SKYVERN_BASE_URL}/usage",
            headers={"x-api-key": SKYVERN_API_KEY},
            timeout=10
        )

        if r.status_code == 404:
            # Try alternate endpoint
            r = requests.get(
                f"{SKYVERN_BASE_URL}/account",
                headers={"x-api-key": SKYVERN_API_KEY},
                timeout=10
            )

        if r.status_code != 200:
            return "warn", f"Skyvern usage check failed (status {r.status_code}) — proceeding with caution"

        data = r.json()

        # Parse usage — adjust keys based on actual Skyvern response shape
        used = data.get("tasks_used") or data.get("used") or data.get("current_usage", 0)
        limit = data.get("tasks_limit") or data.get("limit") or data.get("max_usage", 0)

        if not limit:
            return "warn", "Could not parse Skyvern usage limits from response"

        ratio = used / limit
        pct = round(ratio * 100, 1)

        if ratio >= HALT_THRESHOLD:
            return "halt", f"Skyvern at {pct}% ({used}/{limit}) — PIPELINE HALTED. Switch to fallback browser automation."
        elif ratio >= WARN_THRESHOLD:
            return "warn", f"Skyvern at {pct}% ({used}/{limit}) — approaching limit. Consider fallback soon."
        else:
            return "ok", f"Skyvern OK — {pct}% used ({used}/{limit})"

    except Exception as e:
        return "warn", f"Skyvern check error: {e} — proceeding with caution"


def run_skyvern_check(halt_on_limit=True):
    print("=== Skyvern Limit Check ===")
    status, msg = check_skyvern_limit()
    icon = {"ok": "[OK]", "warn": "[WARN]", "halt": "[HALT]"}.get(status, "?")
    print(f"  {icon} {msg}")
    print()

    if status == "halt" and halt_on_limit:
        print("ACTION REQUIRED: Skyvern limit critical.")
        print("Fallback options:")
        print("  1. browser-use (pip install browser-use)")
        print("  2. Playwright (pip install playwright)")
        print("  3. Manual apply queue — export new jobs to CSV for manual review")
        print()
        exit(1)

    return status


if __name__ == "__main__":
    run_skyvern_check()
