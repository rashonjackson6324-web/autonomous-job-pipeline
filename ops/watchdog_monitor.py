"""
Watchdog Monitor
Monitors pipeline processes and escalates when a stage stalls.
auto-restarts on failure, sends Telegram alerts on state changes.
"""

import os
from collections import Counter
import csv
import pathlib
import sys
import time
import subprocess
import threading
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

JOBS_DIR         = Path(os.getenv("JOBS_DIR", "./data"))
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CHECK_INTERVAL   = 60    # seconds between health checks
STALL_THRESHOLD  = 50    # rows in one status before we call it a stall
MAX_RESTARTS     = 3     # max auto-restarts before alerting
RESTART_COOLDOWN = 120   # seconds before restarting again

# Long-running processes to keep alive.
# Set WATCHED_PROCESSES to a comma-separated list of script paths relative to
# JOBS_DIR, e.g. "servers/api.py,workers/consumer.py". Empty by default: this
# repo ships no long-running service, only scheduled stages.
MONITORED = {
    pathlib.Path(spec).stem: {
        "cmd": [sys.executable, str(JOBS_DIR / spec)],
        "critical": True,
    }
    for spec in filter(None, (x.strip() for x in os.getenv("WATCHED_PROCESSES", "").split(",")))
}

state = {name: {"proc": None, "restarts": 0, "last_restart": 0, "status": "stopped"}
         for name in MONITORED}


def telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[TELEGRAM] {msg}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": f"🐕 [Watchdog]\n{msg}"},
            timeout=5
        )
    except Exception:
        pass


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        log_path = JOBS_DIR / "logs" / "watchdog.log"
        log_path.parent.mkdir(exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def start_process(name: str):
    cfg = MONITORED[name]
    proc = subprocess.Popen(cfg["cmd"], cwd=str(JOBS_DIR))
    state[name]["proc"] = proc
    state[name]["status"] = "running"
    log(f"Started: {name} (PID {proc.pid})")
    return proc



def check_pipeline_health():
    """Escalate if rows pile up in an early status, i.e. a stage has stalled.

    Reads the pipeline CSV directly. There is no health endpoint to depend on:
    the state machine's own durable state is the health signal.
    """
    csv_path = JOBS_DIR / "job_pipeline.csv"
    if not csv_path.exists():
        return
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        log(f"Could not read {csv_path}: {e}")
        return

    counts = Counter(r.get("status", "unknown") for r in rows)
    backlog = counts.get("new", 0)
    if backlog > STALL_THRESHOLD:
        telegram(f"⚠️ {backlog} jobs sitting in 'new' — the pipeline may be stalled.")

    for status in ("qualified", "researched", "tailored"):
        if counts.get(status, 0) > STALL_THRESHOLD:
            telegram(f"⚠️ {counts[status]} jobs stuck at '{status}' — that stage is not draining.")

def watchdog_loop():
    log("Watchdog started.")
    telegram("Watchdog online — monitoring pipeline.")

    # Initial start of all monitored processes
    for name in MONITORED:
        start_process(name)

    time.sleep(5)

    while True:
        for name, cfg in MONITORED.items():
            s = state[name]
            proc = s["proc"]

            if proc is None or proc.poll() is not None:
                # Process is dead
                exit_code = proc.returncode if proc else "unknown"
                s["status"] = "stopped"
                log(f"Process dead: {name} (exit {exit_code})")

                now = time.time()
                cooldown_ok = (now - s["last_restart"]) > RESTART_COOLDOWN

                if s["restarts"] < MAX_RESTARTS and cooldown_ok:
                    s["restarts"] += 1
                    s["last_restart"] = now
                    telegram(f"♻️ {name} crashed (exit {exit_code}). Restarting... ({s['restarts']}/{MAX_RESTARTS})")
                    start_process(name)
                elif s["restarts"] >= MAX_RESTARTS:
                    if cfg["critical"]:
                        telegram(f"🚨 CRITICAL: {name} has crashed {s['restarts']} times. Manual intervention needed.")
                    log(f"Max restarts reached for {name}. Not restarting.")
                else:
                    # In cooldown
                    remaining = int(RESTART_COOLDOWN - (now - s["last_restart"]))
                    log(f"{name} in cooldown. Retry in {remaining}s")
            else:
                # Process alive
                s["status"] = "running"
                s["restarts"] = 0  # reset counter on sustained health

        # Periodic pipeline health check
        check_pipeline_health()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    watchdog_loop()
