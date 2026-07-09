import os
import csv
import requests
import anthropic
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.getenv("JOBS_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


CSV_FILE = str(DATA_DIR / "job_pipeline.csv")
TRACKER_FILE = str(DATA_DIR / "tracker.csv")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message}
    )

def get_pipeline_stats():
    stats = {
        'total': 0,
        'new': 0,
        'qualified': 0,
        'rejected': 0,
        'applied': 0,
        'pending_approval': 0
    }
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                stats['total'] += 1
                status = row['status']
                if status in stats:
                    stats[status] += 1
    except:
        pass
    return stats

def get_followup_count():
    count = 0
    try:
        with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row['status'] == 'applied':
                    count += 1
    except:
        pass
    return count

def generate_briefing(stats, followups):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""Generate a short motivating morning briefing for the operator about his job search pipeline.

Pipeline Stats:
- Total jobs tracked: {stats['total']}
- New jobs found: {stats['new']}
- Qualified: {stats['qualified']}
- Applied: {stats['applied']}
- Pending approval: {stats['pending_approval']}
- Rejected: {stats['rejected']}
- Applications awaiting response: {followups}

Keep it under 150 words. Professional, direct, motivating tone.
Start with the date and a quick status. End with one action item for today."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def run_briefing():
    print("Generating daily briefing...")
    stats = get_pipeline_stats()
    followups = get_followup_count()
    briefing = generate_briefing(stats, followups)
    send_telegram(briefing)
    print("Briefing sent to Telegram")
    print(briefing)

if __name__ == "__main__":
    run_briefing()