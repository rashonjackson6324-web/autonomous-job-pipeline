import os
import csv
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.getenv("JOBS_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


CSV_FILE = str(DATA_DIR / "job_pipeline.csv")

# High-value roles (score +5)
TOP_ROLES = [
    "implementation manager", "implementation consultant", "implementation specialist",
    "implementation lead", "technical trainer", "software trainer", "corporate trainer",
    "project manager", "project coordinator", "onboarding manager", "onboarding specialist",
    "deployment manager", "solutions consultant", "engagement manager", "program manager",
]

# Mid-value roles (score +3)
MID_ROLES = [
    "onboarding", "deployment", "implementation", "trainer",
    "solutions engineer", "technical account", "client success",
]

# Downweighted roles — still tracked but scored lower
DOWNWEIGHT_ROLES = ["customer success manager", "account manager"]

def score_job(title, company, platform):
    score = 0
    title_lower = title.lower()
    company_lower = company.lower()

    # Role scoring
    matched_top = any(all(w in title_lower for w in role.split()) for role in TOP_ROLES)
    matched_mid = any(kw in title_lower for kw in MID_ROLES)
    is_downweighted = any(role in title_lower for role in DOWNWEIGHT_ROLES)

    if matched_top:
        score += 5
    elif matched_mid:
        score += 3

    if is_downweighted and not matched_top:
        score -= 1  # soft penalty for pure CSM / account mgr roles

    # Industry bonus
    preferred = [
        "saas", "healthcare", "payments", "health", "fintech",
        "tech", "software", "solutions", "platform", "cloud",
    ]
    if any(ind in company_lower for ind in preferred):
        score += 2

    # Remote bonus
    if "remote" in title_lower:
        score += 2

    # Seniority bonus
    if any(s in title_lower for s in ["senior", "lead", "sr.", "principal", "staff"]):
        score += 1

    return max(0, min(score, 10))

def process_jobs():
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
        if row['status'] == 'new':
            score = score_job(row['title'], row['company'], row['platform'])
            row['score'] = score
            row['status'] = 'qualified' if score >= 7 else 'rejected'
            updated += 1
            print(f"{row['title']} at {row['company']} - Score: {score} - {row['status']}")

    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"Qualified {updated} jobs")

if __name__ == "__main__":
    process_jobs()