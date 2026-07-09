import os
import csv
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.getenv("JOBS_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


LETTERS_FILE = str(DATA_DIR / "letters.csv")
FORMATTED_FILE = str(DATA_DIR / "formatted.csv")
CSV_FILE = str(DATA_DIR / "job_pipeline.csv")

def format_for_platform(letter, platform):
    if platform == "LinkedIn":
        formatted = letter[:1300]
        return formatted
    elif platform == "email":
        return f"Subject: Application for Role\n\n{letter}"
    else:
        return letter[:2000]

def init_formatted_csv():
    if not os.path.exists(FORMATTED_FILE):
        with open(FORMATTED_FILE, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['company','title','platform','formatted_letter','date'])

def process_tailored():
    rows = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    except:
        print("No CSV found")
        return

    letters = []
    try:
        with open(LETTERS_FILE, 'r', encoding='utf-8') as f:
            letters = list(csv.DictReader(f))
    except:
        print("No letters found")
        return

    init_formatted_csv()
    if not rows:
        return
    updated = 0

    for row in rows:
        if row['status'] == 'tailored':
            letter = next((l['cover_letter'] for l in letters if l['company']==row['company']), None)
            if letter:
                formatted = format_for_platform(letter, row['platform'])
                with open(FORMATTED_FILE, 'a', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow([row['company'],row['title'],row['platform'],formatted,datetime.now().strftime('%Y-%m-%d')])
                row['status'] = 'formatted'
                updated += 1
                print(f"Formatted: {row['company']} for {row['platform']}")

    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"Formatted {updated} applications")

if __name__ == "__main__":
    process_tailored()