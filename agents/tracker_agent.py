import os
import csv
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.getenv("JOBS_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


CSV_FILE = str(DATA_DIR / "job_pipeline.csv")
TRACKER_FILE = str(DATA_DIR / "tracker.csv")

def init_tracker():
    if not os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['company','title','platform','date_applied','status','follow_up_date','notes'])

def process_approved():
    rows = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    except:
        print("No CSV found")
        return

    init_tracker()
    if not rows:
        return
    updated = 0

    for row in rows:
        if row['status'] == 'pending_approval':
            with open(TRACKER_FILE, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow([
                    row['company'],
                    row['title'],
                    row['platform'],
                    datetime.now().strftime('%Y-%m-%d'),
                    'applied',
                    '',
                    ''
                ])
            row['status'] = 'applied'
            updated += 1
            print(f"Tracked: {row['title']} at {row['company']}")

    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"Tracked {updated} applications")

if __name__ == "__main__":
    process_approved()