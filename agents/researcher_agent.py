import os
import csv
import requests
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.getenv("JOBS_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


CSV_FILE = str(DATA_DIR / "job_pipeline.csv")
RESEARCH_FILE = str(DATA_DIR / "research.csv")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

def init_research_csv():
    if not os.path.exists(RESEARCH_FILE):
        with open(RESEARCH_FILE, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['company','research','date'])

def research_company(company):
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"Give me 5 bullet points about {company} covering: company size, core product, recent news, funding status, culture. Format each bullet starting with a dash."
                }]
            }]
        }
        r = requests.post(f"{url}?key={GOOGLE_KEY}", json=payload)
        result = r.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Research pending for {company}"

def process_qualified():
    rows = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    except:
        print("No CSV found")
        return

    init_research_csv()

    if not rows:
        return
    updated = 0
    for row in rows:
        if row['status'] == 'qualified':
            company = row['company']
            print(f"Researching {company}...")
            research = research_company(company)
            with open(RESEARCH_FILE, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow([company, research, datetime.now().strftime('%Y-%m-%d')])
            row['status'] = 'researched'
            updated += 1
            print(f"Done: {company}")

    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"Researched {updated} companies")

if __name__ == "__main__":
    process_qualified()