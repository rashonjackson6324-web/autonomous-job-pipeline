import os
import csv
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

DATA_DIR = Path(os.getenv("JOBS_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

CSV_FILE = str(DATA_DIR / "job_pipeline.csv")
HEADERS = ['title','company','url','date_posted','platform','status','score','date_added','cover_letter_required']

# ── Target roles (weighted toward what the operator wants) ──────────────────────────
TARGET_KEYWORDS = [
    "implementation manager",
    "implementation consultant",
    "implementation specialist",
    "implementation lead",
    "technical trainer",
    "software trainer",
    "corporate trainer",
    "project manager",
    "project coordinator",
    "onboarding manager",
    "onboarding specialist",
    "onboarding consultant",
    "solutions consultant",
    "solutions engineer",
    "engagement manager",
    "program manager",
    "deployment manager",
    "deployment specialist",
]

# Roles to deprioritise (won't be excluded, just scored lower by qualifier)
DOWNWEIGHT_TITLES = ["customer success manager", "account manager", "sales manager"]


def is_relevant(title: str) -> bool:
    t = title.lower()
    for kw in TARGET_KEYWORDS:
        if all(w in t for w in kw.split()):
            return True
    # Broad fallback: catch anything with these single words
    broad = ["implementation", "onboarding", "trainer", "deployment"]
    return any(w in t for w in broad)


def ensure_csv_headers():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(HEADERS)
        return
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        first = f.readline().strip().split(',')
    if first[0].lower() != 'title':
        # Prepend header row
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            body = f.read()
        with open(CSV_FILE, 'w', encoding='utf-8') as f:
            f.write(','.join(HEADERS) + '\n' + body)


def get_existing_urls() -> set:
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            return {row['url'] for row in csv.DictReader(f) if row.get('url')}
    except Exception:
        return set()


def save_jobs(jobs: list, existing_urls: set) -> int:
    added = 0
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        for j in jobs:
            url = j.get('url', '').strip()
            if url and url not in existing_urls:
                w.writerow([
                    j.get('title', ''),
                    j.get('company', ''),
                    url,
                    j.get('date_posted', datetime.now().strftime('%Y-%m-%d'))[:10],
                    j.get('platform', ''),
                    'new', '',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    j.get('cover_letter_required', 'no'),
                ])
                existing_urls.add(url)
                added += 1
    return added


# ── Job Sources ────────────────────────────────────────────────────────────────

def fetch_remoteok() -> list:
    """RemoteOK free JSON API — remote-only jobs."""
    jobs = []
    try:
        r = requests.get(
            'https://remoteok.com/api',
            headers={'User-Agent': 'JobScout/1.0'},
            timeout=20,
        )
        data = r.json()
        for item in data[1:]:  # index 0 is metadata
            title = item.get('position', '')
            if is_relevant(title):
                jobs.append({
                    'title': title,
                    'company': item.get('company', 'Unknown'),
                    'url': item.get('url') or f"https://remoteok.com/remote-jobs/{item.get('id','')}",
                    'date_posted': (item.get('date') or '')[:10] or datetime.now().strftime('%Y-%m-%d'),
                    'platform': 'RemoteOK',
                })
    except Exception as e:
        print(f"  [RemoteOK] error: {e}")
    return jobs


def fetch_arbeitnow() -> list:
    """Arbeitnow free API — worldwide, remote-friendly."""
    jobs = []
    terms = ['implementation', 'project-manager', 'trainer', 'onboarding', 'project-coordinator', 'deployment']
    seen = set()
    for term in terms:
        try:
            r = requests.get(
                f'https://www.arbeitnow.com/api/job-board-api?search={term}&remote=true',
                timeout=20,
            )
            for item in r.json().get('data', []):
                title = item.get('title', '')
                url = item.get('url', '')
                if url in seen or not is_relevant(title):
                    continue
                seen.add(url)
                jobs.append({
                    'title': title,
                    'company': item.get('company_name', 'Unknown'),
                    'url': url,
                    'date_posted': str(item.get('created_at', ''))[:10] or datetime.now().strftime('%Y-%m-%d'),
                    'platform': 'Arbeitnow',
                })
        except Exception as e:
            print(f"  [Arbeitnow:{term}] error: {e}")
    return jobs


def fetch_themuse() -> list:
    """The Muse public API — US-focused, many tech companies."""
    jobs = []
    categories = ['Project+Management', 'IT', 'Operations+%26+Logistics', 'Data+%26+Analytics']
    seen = set()
    for cat in categories:
        for page in range(1, 3):  # pages 1-2
            try:
                r = requests.get(
                    f'https://www.themuse.com/api/public/jobs?category={cat}'
                    f'&level=Mid+Level&level=Senior+Level&page={page}&api_key=public',
                    timeout=20,
                )
                for item in r.json().get('results', []):
                    title = item.get('name', '')
                    url = item.get('refs', {}).get('landing_page', '')
                    if url in seen or not is_relevant(title):
                        continue
                    seen.add(url)
                    jobs.append({
                        'title': title,
                        'company': item.get('company', {}).get('name', 'Unknown'),
                        'url': url,
                        'date_posted': (item.get('publication_date') or '')[:10] or datetime.now().strftime('%Y-%m-%d'),
                        'platform': 'TheMuse',
                    })
            except Exception as e:
                print(f"  [TheMuse:{cat}] error: {e}")
    return jobs


def fetch_weworkremotely() -> list:
    """We Work Remotely RSS feeds."""
    jobs = []
    feeds = [
        'https://weworkremotely.com/categories/remote-management-finance-jobs.rss',
        'https://weworkremotely.com/categories/remote-all-other-jobs.rss',
        'https://weworkremotely.com/categories/remote-customer-support-jobs.rss',
    ]
    seen = set()
    for feed_url in feeds:
        try:
            r = requests.get(feed_url, headers={'User-Agent': 'JobScout/1.0'}, timeout=20)
            root = ET.fromstring(r.content)
            for item in root.findall('.//item'):
                raw_title = item.findtext('title', '')
                url = item.findtext('link', '')
                # WWR format: "Company: Job Title"
                if ':' in raw_title:
                    company, title = raw_title.split(':', 1)
                    company = company.strip()
                    title = title.strip()
                else:
                    title, company = raw_title, 'Unknown'
                if url in seen or not is_relevant(title):
                    continue
                seen.add(url)
                pub = item.findtext('pubDate', '')[:16]
                jobs.append({
                    'title': title,
                    'company': company,
                    'url': url,
                    'date_posted': pub or datetime.now().strftime('%Y-%m-%d'),
                    'platform': 'WeWorkRemotely',
                })
        except Exception as e:
            print(f"  [WWR] error: {e}")
    return jobs


def fetch_jobicy() -> list:
    """Jobicy free API — remote jobs."""
    jobs = []
    try:
        r = requests.get(
            'https://jobicy.com/api/v2/remote-jobs?count=50&industry=management',
            timeout=20,
        )
        for item in r.json().get('jobs', []):
            title = item.get('jobTitle', '')
            url = item.get('url', '')
            if not is_relevant(title):
                continue
            jobs.append({
                'title': title,
                'company': item.get('companyName', 'Unknown'),
                'url': url,
                'date_posted': (item.get('pubDate') or '')[:10] or datetime.now().strftime('%Y-%m-%d'),
                'platform': 'Jobicy',
            })
    except Exception as e:
        print(f"  [Jobicy] error: {e}")
    return jobs


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"=== Job Scout starting at {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    ensure_csv_headers()
    existing_urls = get_existing_urls()
    print(f"Pipeline already has {len(existing_urls)} jobs.\n")

    sources = [
        ("RemoteOK",        fetch_remoteok),
        ("Arbeitnow",       fetch_arbeitnow),
        ("The Muse",        fetch_themuse),
        ("We Work Remotely",fetch_weworkremotely),
        ("Jobicy",          fetch_jobicy),
    ]

    total_new = 0
    for name, fn in sources:
        print(f"Fetching from {name}...")
        try:
            found = fn()
            added = save_jobs(found, existing_urls)
            print(f"  {len(found)} relevant found, {added} new added.")
            total_new += added
        except Exception as e:
            print(f"  Failed: {e}")

    print(f"\n=== Done. {total_new} new jobs added to pipeline. ===")


if __name__ == "__main__":
    main()
