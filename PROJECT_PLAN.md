# BESI Email Sender — Project Plan

**Goal:** Every morning at 8 AM, automatically email Yan.Fikh@besi.ca a list of construction workers who clocked in the previous day but left their cost code blank (NULL) in the timecard system.

---

## System Overview

```
[Procore / source system]
        ↓  (exports nightly at 12 AM)
  Timecards.csv
        ↓  (runs at 8 AM)
  send_email.py
        ↓
  Email → Yan.Fikh@besi.ca
```

The CSV is refreshed at 12 AM each night before the 8 AM email runs, so the script always operates on fresh data.

---

## CSV Structure

The file has no header row. Column indices (0-based):

| Index | Field |
|-------|-------|
| 0 | Worker name |
| 1 | Employee ID |
| 2 | Status |
| 3 | Department |
| 4 | Role |
| 5 | Project name |
| 6 | Project detail |
| 7 | Union type |
| 8 | Timecard status |
| 9 | Clock-in time |
| 10 | Clock-out time |
| 11 | Duration |
| 12 | Shift |
| **13** | **Cost Code ← the field we check** |
| 14 | (reserved) |
| 15 | (reserved) |
| 16 | Regular hours |
| 17–19 | Other hour types |
| 20–23 | Internal IDs |
| 24 | Record timestamp |

A row is flagged if column 13 is `NULL` (string) or empty.

The script should filter to rows where the **clock-in date (col 9) matches yesterday's date**, so repeat/historical nulls don't re-trigger every day.

---

## Project Phases

### ✅ Phase 1 — Data Source (COMPLETE)
- Timecards.csv is exported nightly at 12 AM to the project folder.
- No action needed — this pipeline is already in place.

### ✅ Phase 2 — Email Script (COMPLETE — built this session)
- `send_email.py` reads the CSV, filters yesterday's rows with null cost codes, and sends a formatted email via Gmail SMTP.
- Uses app password authentication (not raw Gmail password).
- See **Setup steps** below before running in production.

### 🔲 Phase 3 — Scheduling (IN PROGRESS)
- A scheduled task needs to run `send_email.py` daily at 8 AM.
- The schedule skill / cron entry is set up in this session.
- **Verify**: confirm the task fires correctly by checking logs the first morning.

### 🔲 Phase 4 — Production CSV Swap (HANDOFF TASK)
- Currently the script runs against `Timecards.csv` (static sample).
- When the live CSV feed is available, update the `CSV_PATH` variable in `send_email.py` to point to the real file location.
- No other code changes needed.

### 🔲 Phase 5 — Gmail App Password (HANDOFF TASK)
- The script authenticates to Gmail via an **App Password** (not the account password).
- Steps for whoever sets this up:
  1. Log into `gloriatesting8@gmail.com` → Google Account → Security.
  2. Enable 2-Step Verification if not already on.
  3. Go to **App passwords** → create one named "BESI Email Sender".
  4. Copy the 16-character password.
  5. Open `send_email.py` and replace `YOUR_APP_PASSWORD_HERE` with it (or set the env var `GMAIL_APP_PASSWORD`).

### 🔲 Phase 6 — Production Sender Email (HANDOFF TASK)
- `gloriatesting8@gmail.com` is used for testing. In production, swap to the official BESI sender address.
- Update `SENDER_EMAIL` in `send_email.py`.
- May require IT to provision a Google Workspace app password or switch to an SMTP relay.

### 🔲 Phase 7 — Validation & Monitoring (HANDOFF TASK)
- First week: manually verify the email arrives and the names match what supervisors expect.
- Add a simple log file (`email_log.txt`) write on each run — already included in the script.
- If the CSV schema changes (new columns inserted), update the `COST_CODE_COL` index in `send_email.py`.

---

## Key Files

| File | Purpose |
|------|---------|
| `Timecards.csv` | Source data, refreshed nightly at 12 AM |
| `send_email.py` | Main script — reads CSV, sends email |
| `email_log.txt` | Auto-generated run log (created on first run) |
| `PROJECT_PLAN.md` | This document |

---

## Configuration Variables (top of `send_email.py`)

```python
CSV_PATH       = "Timecards.csv"          # ← swap to live path in Phase 4
SENDER_EMAIL   = "gloriatesting8@gmail.com" # ← swap in Phase 6
RECIPIENT      = "Yan.Fikh@besi.ca"
COST_CODE_COL  = 13                        # ← update if CSV schema changes
DATE_COL       = 9                         # clock-in timestamp column
```

---

## Handoff Checklist for Next Team Member

- [ ] Set up Gmail App Password (Phase 5)
- [ ] Confirm scheduled task is firing daily at 8 AM
- [ ] Swap `CSV_PATH` to live file once the real feed is ready (Phase 4)
- [ ] Swap sender email to production address (Phase 6)
- [ ] Monitor first 3–5 mornings and verify email content is accurate
- [ ] Update `COST_CODE_COL` if the CSV column order ever changes
