import os
import csv
import requests
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.getenv("JOBS_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


CSV_FILE = str(DATA_DIR / "job_pipeline.csv")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message}
    )

def process_formatted():
    rows = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    except:
        print("No CSV found")
        return

    if not rows:
        return
    updated = 0
    for row in rows:
        if row['status'] == 'formatted':
            msg = "NEW APPLICATION READY\n\n"
            msg += f"Role: {row['title']}\n"
            msg += f"Company: {row['company']}\n"
            msg += f"Platform: {row['platform']}\n"
            msg += f"URL: {row['url']}\n\n"
            msg += "Reply SUBMIT to approve"
            send_telegram(msg)
            row['status'] = 'pending_approval'
            updated += 1
            print(f"Sent to Telegram: {row['company']}")

    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"Sent {updated} applications for approval")

if __name__ == "__main__":
    process_formatted()