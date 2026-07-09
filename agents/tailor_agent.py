import os
import pathlib
import csv
import anthropic
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.getenv("JOBS_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


CSV_FILE = str(DATA_DIR / "job_pipeline.csv")
RESEARCH_FILE = str(DATA_DIR / "research.csv")
LETTERS_FILE = str(DATA_DIR / "letters.csv")

def _load_profile() -> str:
    """Candidate profile is user data, not source.

    Set CANDIDATE_PROFILE to a path, or drop a file at ./profile.md
    (see profile.example.md for the expected shape). profile.md is gitignored.
    """
    path = pathlib.Path(os.getenv("CANDIDATE_PROFILE", "profile.md"))
    if not path.exists():
        raise FileNotFoundError(
            f"No candidate profile at {path}. Copy profile.example.md to "
            "profile.md and fill it in, or set CANDIDATE_PROFILE."
        )
    return path.read_text(encoding="utf-8")


RESUME = _load_profile()

def get_research(company):
    try:
        with open(RESEARCH_FILE, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row['company'] == company:
                    return row['research']
    except:
        pass
    return "No research available"

def write_cover_letter(job, research):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    prompt = f"""Write a tailored cover letter for:
Title: {job['title']}
Company: {job['company']}
Research: {research}
Background: {RESUME}
Instructions: Select 2 relevant stories, 300-400 words, professional tone, focus on results."""
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def init_letters_csv():
    if not os.path.exists(LETTERS_FILE):
        with open(LETTERS_FILE, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['company','title','cover_letter','date'])

def process_researched():
    rows = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    except:
        print("No CSV found")
        return

    init_letters_csv()
    if not rows:
        return
    updated = 0

    for row in rows:
        if row['status'] == 'researched':
            needs_letter = row.get('cover_letter_required','no').lower() == 'yes'
            if needs_letter:
                print(f"Writing cover letter for {row['company']}...")
                research = get_research(row['company'])
                letter = write_cover_letter(row, research)
                with open(LETTERS_FILE, 'a', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow([row['company'],row['title'],letter,datetime.now().strftime('%Y-%m-%d')])
                print(f"Done: {row['company']}")
            else:
                print(f"No cover letter needed for {row['company']}")
            row['status'] = 'tailored'
            updated += 1

    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"Processed {updated} jobs")

if __name__ == "__main__":
    process_researched()