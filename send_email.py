"""
BESI Email Sender
-----------------
This script reads the daily timecard CSV, finds workers who did not fill in
their cost code for yesterday, and sends a summary email to the supervisor.

It is meant to run automatically every morning at 8 AM after the CSV refreshes
at midnight. You can also run it manually from Terminal anytime.

To run it:
    export GMAIL_APP_PASSWORD="your-app-password-here"
    python3 send_email.py
"""

import csv
import os
import smtplib
import logging
from datetime import date, timedelta, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path


# ── Configuration ─────────────────────────────────────────────────────────────
# These are the main settings you might need to change when handing this off.

# Path to the CSV file. Right now this points to the static sample file.
# When the live nightly export is ready, update this to the real file path.
CSV_PATH = Path(__file__).parent / "Timecards.csv"

# The Gmail account that sends the alert emails. This is a test account.
# Swap this out for the official BESI sender email when going to production.
SENDER_EMAIL = "gloriatesting8@gmail.com"

# The Gmail app password. Never hardcode this here. Set it as an environment
# variable in Terminal before running: export GMAIL_APP_PASSWORD="your-password"
APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "YOUR_APP_PASSWORD_HERE")

# Who receives the daily alert email.
RECIPIENT = "Yan.Fikh@besi.ca"

# Which column in the CSV holds the cost code (0-based index).
# Currently column 14 in the file, which is index 13.
# If the CSV format ever changes and columns shift, update this number.
COST_CODE_COL = 13

# Which column holds the clock-in timestamp (0-based index).
DATE_COL = 9

# Which column holds the worker name.
NAME_COL = 0

# Which column holds the employee ID.
ID_COL = 1

# Which column holds the project name.
PROJECT_COL = 5

# Where to write the run log. This file is created automatically on first run.
LOG_FILE = Path(__file__).parent / "email_log.txt"
# ─────────────────────────────────────────────────────────────────────────────


# Set up logging so every run gets recorded in email_log.txt with a timestamp.
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)


def is_null(value: str) -> bool:
    """
    Check if a cost code value is missing.
    Returns True if the value is empty, NULL, N/A, or NONE.
    """
    return value.strip().upper() in ("", "NULL", "N/A", "NONE")


def get_yesterday() -> date:
    """Return yesterday's date. The script always checks the previous day."""
    return date.today() - timedelta(days=1)


def parse_date(value: str) -> date | None:
    """
    Convert a timestamp string like '2026-06-01 06:30:00' into a date object.
    Returns None if the format doesn't match so the row gets skipped safely.
    """
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def load_missing_cost_codes(target_date: date) -> list[dict]:
    """
    Read the CSV and return a list of workers who have a missing cost code
    on the given date. Each worker and project combination is a separate entry,
    so if someone worked on two projects both show up in the email.
    """
    missing = []

    # We use a set to avoid duplicate rows for the same person, date, and project.
    seen = set()

    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:

            # Skip rows that are too short to have all the columns we need.
            if len(row) <= max(COST_CODE_COL, DATE_COL, NAME_COL):
                continue

            # Only look at rows from the target date.
            clock_in_date = parse_date(row[DATE_COL])
            if clock_in_date != target_date:
                continue

            # Skip this row if the cost code is actually filled in.
            cost_code = row[COST_CODE_COL]
            if not is_null(cost_code):
                continue

            name    = row[NAME_COL].strip()
            emp_id  = row[ID_COL].strip()
            project = row[PROJECT_COL].strip()

            # Use name + date + project as a unique key to avoid duplicates.
            key = (name, str(clock_in_date), project)

            if key not in seen:
                seen.add(key)
                missing.append({
                    "name":    name,
                    "id":      emp_id,
                    "project": project,
                    "date":    str(clock_in_date),
                })

    return missing


def build_email(missing: list[dict], target_date: date) -> MIMEMultipart:
    """
    Build the email message with both a plain text and HTML version.
    The HTML version includes a formatted table so it looks clean in Gmail.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[BESI] Missing Cost Codes — {target_date.strftime('%B %d, %Y')}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT

    count = len(missing)

    # Plain text version for email clients that don't support HTML.
    lines = [
        "Hi Yan,",
        "",
        f"The following {count} worker(s) did not submit a cost code for {target_date.strftime('%A, %B %d, %Y')}:",
        "",
    ]
    for i, w in enumerate(missing, 1):
        lines.append(f"  {i}. {w['name']} (ID: {w['id']}) — {w['project']}")
    lines += [
        "",
        "Please follow up with them to ensure their timecards are complete.",
        "",
        "This is an automated message from the BESI Timecard System.",
    ]
    text_body = "\n".join(lines)

    # HTML version with a styled table.
    rows_html = "".join(
        f"<tr><td>{i}</td><td>{w['name']}</td><td>{w['id']}</td><td>{w['project']}</td></tr>"
        for i, w in enumerate(missing, 1)
    )
    html_body = f"""
    <html><body>
    <p>Hi Yan,</p>
    <p>The following <strong>{count} worker(s)</strong> did not submit a cost code
       for <strong>{target_date.strftime('%A, %B %d, %Y')}</strong>:</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px;">
      <thead style="background:#f2f2f2;">
        <tr><th>#</th><th>Name</th><th>Employee ID</th><th>Project</th></tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    <p>Please follow up with them to ensure their timecards are complete.</p>
    <p style="color:#888;font-size:12px;">This is an automated message from the BESI Timecard System.</p>
    </body></html>
    """

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return msg


def send_email(msg: MIMEMultipart) -> None:
    """
    Connect to Gmail's SMTP server and send the email.
    Uses TLS encryption on port 587.
    """
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT, msg.as_string())


def main():
    yesterday = get_yesterday()
    logging.info(f"Starting run for date: {yesterday}")

    # Stop early if the app password hasn't been set up yet.
    if APP_PASSWORD == "YOUR_APP_PASSWORD_HERE":
        logging.error("App password not configured. Set GMAIL_APP_PASSWORD env var.")
        print("ERROR: Gmail app password not set. See PROJECT_PLAN.md — Phase 5.")
        return

    # Load workers with missing cost codes for yesterday.
    missing = load_missing_cost_codes(yesterday)
    logging.info(f"Found {len(missing)} worker(s) with missing cost codes.")

    # If nobody is missing a cost code, skip sending the email.
    if not missing:
        logging.info("No missing cost codes — no email sent.")
        print(f"No missing cost codes for {yesterday}. No email sent.")
        return

    # Build and send the email.
    msg = build_email(missing, yesterday)
    send_email(msg)
    logging.info(f"Email sent to {RECIPIENT} listing {len(missing)} worker(s).")
    print(f"Email sent to {RECIPIENT} with {len(missing)} worker(s) flagged.")


if __name__ == "__main__":
    main()
