"""Build jobs_filtered.csv: jobs_current.csv minus anything already applied per application_log.csv.

Runs inside run-skyvern.yml before the Skyvern trigger. Skyvern's cloud plan disables
code blocks, so dedupe happens here in Actions instead of inside the agent.
"""
import csv
import sys

APPLIED_STATUSES = {"applied", "submitted", "completed"}

applied = set()
try:
    with open("application_log.csv", newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            status = (row.get("status") or row.get("application_status") or "").strip().lower()
            if status in APPLIED_STATUSES:
                url = (row.get("apply_url") or row.get("url") or "").strip()
                if url:
                    applied.add(url)
except FileNotFoundError:
    print("WARN: application_log.csv not found; applied set empty")

with open("jobs_current.csv", newline="", encoding="utf-8", errors="replace") as f:
    rows = list(csv.DictReader(f))
    fields = list(rows[0].keys()) if rows else []

out = [r for r in rows if (r.get("apply_url") or "").strip() not in applied]

with open("jobs_filtered.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out)

print(f"{len(rows)} jobs, {len(rows) - len(out)} already applied, {len(out)} to apply")
if not out:
    print("NOTE: nothing left to apply to - refresh jobs_current.csv")
