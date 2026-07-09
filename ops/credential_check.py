# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_anthropic():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if key.startswith('"') or key.endswith('"'):
        return False, "ANTHROPIC_API_KEY has quotes — remove them from .env"
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 10, "messages": [{"role": "user", "content": "ping"}]},
            timeout=10
        )
        if r.status_code == 200:
            return True, "Anthropic OK"
        return False, f"Anthropic 401 — key invalid or expired (status {r.status_code})"
    except Exception as e:
        return False, f"Anthropic error: {e}"

def check_telegram():
    token = os.getenv("TELEGRAM_TOKEN", "")
    if token.startswith('"') or token.endswith('"'):
        return False, "TELEGRAM_TOKEN has quotes — remove them from .env"
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if r.status_code == 200:
            return True, f"Telegram OK — bot: {r.json()['result']['username']}"
        return False, f"Telegram 401 — token invalid or revoked (status {r.status_code})"
    except Exception as e:
        return False, f"Telegram error: {e}"

def run_checks():
    print("=== Credential Health Check ===")
    all_good = True
    for name, fn in [("Anthropic", check_anthropic), ("Telegram", check_telegram)]:
        ok, msg = fn()
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {status} {msg}")
        if not ok:
            all_good = False
    print()
    if not all_good:
        print("PIPELINE HALTED — fix credentials before running.")
        exit(1)
    print("All credentials valid. Pipeline continuing.")

if __name__ == "__main__":
    run_checks()
