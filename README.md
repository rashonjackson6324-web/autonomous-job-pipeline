# autonomous-job-pipeline

A staged pipeline that finds job listings, qualifies them against a rubric, researches the company, tailors a cover letter, formats it for the target platform, and routes it to a human for one-tap approval before anything is submitted.

Runs on a scheduler. The only human action in the loop is the approval tap.

---

## Pipeline

Each agent reads a shared CSV, acts only on rows in its input status, and writes the next status. The status field *is* the state machine.

```
  scout_agent          scrape + aggregate listings              → status: new
       │
       ▼
  qualifier_agent      score 0-10 against a rubric              → qualified (≥7) | rejected
       │
       ▼
  researcher_agent     enrich: company, team, stack, news       → researched
       │
       ▼
  tailor_agent         write a cover letter for this posting    → tailored
       │
       ▼
  formatter_agent      fit the letter to the platform's limits  → formatted
       │
       ▼
  submitter_agent      push to chat for approval                → pending_approval
       │                 ("Reply SUBMIT to approve")
       ▼
  tracker_agent        record the outcome                       → applied
       │
       ▼
  followup_agent       time-delayed follow-up on silence
```

Supporting modules:

| Module | Role |
|---|---|
| `agents/qa_agent.py` | Answers a specific application or interview question using the candidate profile, structured with the STAR method. Invoked on demand, not part of the status chain. |
| `agents/briefing_agent.py` | Compiles a digest of what ran and what it produced. |
| `ops/watchdog_monitor.py` | Escalates when a stage stalls. |
| `ops/scheduler.py` | Registers the scheduled runs. |
| `ops/credential_check.py` | Preflight: are the required credentials present? |
| `ops/skyvern_check.py` | Preflight: browser-automation quota check. |

---

## Why it's built this way

**A CSV status column instead of a queue.** Every stage is idempotent and independently re-runnable. If `researcher_agent` dies halfway, rerunning it picks up exactly the rows still marked `qualified`. There is no in-memory state to lose and no broker to operate. For a pipeline that runs three times a day, a durable file beats a message queue.

**`qualifier_agent` runs before `researcher_agent`.** Research is the expensive stage — LLM calls, web fetches. Filtering first means you never pay to enrich a listing you were never going to apply to.

**The submit step is a human gate, on purpose.** `submitter_agent` does not fill out the form. It assembles the application, posts it to a chat client, and waits for approval. An autonomous applicant that fires blind into a real employer's ATS is a liability — one malformed cover letter addressed to the wrong company, repeated forty times, is worse than applying to nothing. The pipeline automates everything up to the decision, and stops.

**Preflight checks fail the run early.** `credential_check` and `skyvern_check` run before any stage does work, so a missing API key surfaces as a clean failure rather than a half-processed CSV.

---

## A bug this design surfaced

`tailor_agent` used to write status `formatted` — the status `submitter_agent` consumes. That silently skipped `formatter_agent` entirely, so cover letters went out without ever being fitted to the platform's character limits.

The state machine made it obvious once written down: a stage that no status ever routes to is dead code. It now writes `tailored`, and the formatter runs.

---

## Layout

```
main_pipeline.py           preflight checks, then the stage chain; halts on failure
pipeline_master.py         thin wrapper that runs main_pipeline.py
agents/                    the pipeline stages
ops/                       preflight, scheduling, monitoring
profile.example.md         template — copy to profile.md (gitignored)
```

Stage scripts resolve against the repository root; CSVs and logs resolve against `JOBS_DIR`. Conflating the two means the runner shells out to `./data/agents/scout_agent.py`, which does not exist — and because a non-zero exit was never checked, the run logged "complete" having done nothing.

The candidate profile is user data, not source. `tailor_agent` and `qa_agent` load it at runtime from `profile.md`, which is gitignored. Copy `profile.example.md` and fill it in.

---

## Running

```bash
cp .env.example .env
cp profile.example.md profile.md      # then fill it in
pip install -r requirements.txt
python main_pipeline.py
```

## License

MIT
