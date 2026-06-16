# BESI Email Sender

An automated tool that emails a daily summary of construction workers who did not submit a cost code in their timecard. Built for BESI Construction.

---

## What it does

Every morning at **8 AM**, the script reads the previous day's timecard data, finds workers with a missing cost code, and sends a formatted email to the supervisor. A web dashboard is also included for manually browsing the data and adjusting settings.

```
[Procore / source system]
        ↓  exports nightly at 12 AM
  Timecards.csv
        ↓  runs at 8 AM
  send_email.py
        ↓
  Email → Yan.Fikh@besi.ca
```

---

## Project Structure

```
BESI email sender/
├── send_email.py      # Main script — reads CSV, sends email
├── dashboard.py       # Web dashboard — browse missing codes, adjust settings
├── Timecards.csv      # Sample CSV (replace with live feed in production)
├── settings.json      # Auto-generated when you save settings in the dashboard
├── email_log.txt      # Auto-generated run log
└── PROJECT_PLAN.md    # Full project plan and handoff checklist
```

---

## Setup

### Requirements
- Python 3.10+
- No external packages needed — uses only the standard library

### 1. Gmail App Password
The script sends email via Gmail SMTP using an app password (not your regular Gmail password).

1. Log into the sender Gmail account → Google Account → Security
2. Enable 2-Step Verification if not already on
3. Go to **App passwords** → create one named "BESI Email Sender"
4. Copy the 16-character password
5. Set it as an environment variable before running:

```bash
export GMAIL_APP_PASSWORD="your-app-password-here"
```

### 2. Run the email script manually

```bash
python3 send_email.py
```

### 3. Run the dashboard

```bash
python3 dashboard.py
```

Then open **http://localhost:5050** in your browser.

---

## Configuration

All key settings are at the top of `send_email.py`:

| Variable | Default | Notes |
|----------|---------|-------|
| `CSV_PATH` | `Timecards.csv` | Update to live CSV path in production |
| `SENDER_EMAIL` | `gloriatesting8@gmail.com` | Swap to official BESI email in production |
| `RECIPIENT` | `Yan.Fikh@besi.ca` | Who receives the daily alert |
| `COST_CODE_COL` | `13` | 0-based column index of cost code in CSV |
| `DATE_COL` | `9` | 0-based column index of clock-in time |

---

## Handoff Checklist

- [ ] Set `GMAIL_APP_PASSWORD` environment variable
- [ ] Swap `CSV_PATH` to the live nightly export path
- [ ] Swap `SENDER_EMAIL` to the official BESI sender address
- [ ] Confirm scheduled task is firing at 8 AM daily
- [ ] Monitor first few mornings and verify email content is accurate
- [ ] Update `COST_CODE_COL` if the CSV column order ever changes

---

## Dashboard Features

- Browse missing cost codes by date
- Search by worker name, ID, or project
- Send a test email directly from the UI
- Adjust recipient, sender, and send time without touching code

---

Built by Gloria Wang — June 2026
