# Autonomous Job Application Pipeline

A fully autonomous job-application system I designed, built, and operate. Every morning at 8 AM ET, GitHub Actions dedupes a curated list of live job postings against my application history, then hands the remaining jobs to a [Skyvern](https://skyvern.com) browser agent that fills out and submits each application. Every result logs back automatically; every failure self-documents to a defect register.

> **Note:** this is a public showcase of the pipeline. The live deployment runs from a private repo (real profile data, application history, and secrets stay private). Workflow files are under `workflows/` here so they stay inert; in production they live in `.github/workflows/`.

## Architecture

```
cron 8AM ET ─→ run-skyvern.yml (GitHub Actions)
              ├─ scripts/filter_jobs.py   dedupe jobs vs application history
              ├─ publish jobs_filtered.csv → public assets repo
              └─ scripts/call_skyvern.py  POST /v1/run/workflows (Skyvern API)
                                            │
                        Skyvern agent ──────┘  parse CSV → loop jobs → apply + submit
                        (lag-skip rules, 25-step cap, continue-on-failure)
                                            │  repository_dispatch per job
              log-application.yml ←─────────┘  append → application_log.csv
              mirror-log.yml               publish log for dedupe reads
              defect-monitor.yml           on any failure → defect log
```

## Design decisions

- **Dedupe in CI, not in the agent** - the Skyvern plan disables code blocks, so filtering happens for free in GitHub Actions before the agent starts. Same outcome, zero platform dependency.
- **Skip-on-lag** - the agent prompt treats unresponsive/slow/looping pages as skips (`page_lag_or_timeout`) instead of burning steps; each application is hard-capped at 25 browser steps.
- **Hard safety rails** - CAPTCHAs and login walls are immediate skips; the agent never creates accounts or touches credentials.
- **Self-documenting failures** - every failed workflow run appends a structured row to a defect log with root cause, so defect classes get eliminated instead of retried. Real examples caught this way: a stale workflow ID after agent recreation (404), an expired PAT breaking the log mirror, request bodies corrupted by curl through a proxy (422, fixed with urllib).
- **Idempotent by design** - jobs already applied/submitted/completed are filtered every run; one bad job never kills a batch (`continue_on_failure`).

## Stack

GitHub Actions (cron, repository_dispatch, secrets) · Skyvern browser agent (task_v2 blocks, prompt engineering) · Python stdlib (csv, urllib) · direct ATS integrations (Greenhouse/Ashby/Lever boards)

## Files

| File | Purpose |
|---|---|
| `workflows/run-skyvern.yml` | Daily trigger: dedupe, publish filtered CSV, call Skyvern API |
| `workflows/log-application.yml` | Receives per-job `application_result` dispatches; appends to the CSV log |
| `workflows/mirror-log.yml` | Publishes the application log so the dedupe step can read it |
| `workflows/defect-monitor.yml` | Auto-appends every failed run to the defect log |
| `scripts/filter_jobs.py` | Dedupe: drops jobs already applied/submitted/completed |
| `scripts/call_skyvern.py` | Clean urllib POST to Skyvern |
| `profile.example.json` | Sanitized template of the agent's answer profile |
