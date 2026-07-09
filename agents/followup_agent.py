import os
import csv
import requests
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(os.getenv("JOBS_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


TRACKER_FILE = str(DATA_DIR / "tracker.csv")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message}
    )

def check_followups():
    rows = []
    try:
        with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    except:
        print("No tracker file found")
        return

    today = datetime.now().date()
    flagged = 0

    for row in rows:
        if row['status'] == 'applied' and row['date_applied']:
            try:
                applied_date = datetime.strptime(row['date_applied'], '%Y-%m-%d').date()
                days_since = (today - applied_date).days
                if days_since >= 5:
                    msg = f"FOLLOW UP NEEDED\n\n"
                    msg += f"Role: {row['title']}\n"
                    msg += f"Company: {row['company']}\n"
                    msg += f"Platform: {row['platform']}\n"
                    msg += f"Applied: {row['date_applied']} ({days_since} days ago)\n\n"
                    msg += f"Suggested follow up:\n"
                    msg += f"Hi, I wanted to follow up on my application for the {row['title']} role. I remain very interested in joining {row['company']} and would love to discuss how my experience aligns with your needs. Please let me know if you need anything else from me."
                    send_telegram(msg)
                    flagged += 1
                    print(f"Follow up sent for: {row['company']}")
            except:
                pass

    if flagged == 0:
        print("No follow ups needed today")
    else:
        print(f"Sent {flagged} follow up reminders")

if __name__ == "__main__":
    check_followups()