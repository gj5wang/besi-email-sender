"""
BESI Email Sender
-----------------
Reads Timecards.csv, finds workers with a NULL cost code for yesterday,
and emails a summary to Yan.Fikh@besi.ca.

Run daily at 8 AM (after the 12 AM CSV refresh).
"""

import csv
import os
import smtplib
import logging
from datetime import date, timedelta, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────
CSV_PATH      = Path(__file__).parent / "Timecards.csv"
SENDER_EMAIL  = "gloriatesting8@gmail.com" #the testing email
# Set GMAIL_APP_PASSWORD as an environment variable, or paste it below.
APP_PASSWORD  = os.environ.get("GMAIL_APP_PASSWORD", "YOUR_APP_PASSWORD_HERE")
RECIPIENT     = "Yan.Fikh@besi.ca"

COST_CODE_COL = 13   # 0-based index of the Cost Code column
DATE_COL      = 9    # 0-based index of the clock-in timestamp column
NAME_COL      = 0    # 0-based index of the worker name column
ID_COL        = 1    # 0-based index of the employee ID column
PROJECT_COL   = 5    # 0-based index of the project name column

LOG_FILE      = Path(__file__).parent / "email_log.txt"
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)


def is_null(value: str) -> bool:
    """Return True if the cost code field is missing or NULL."""
    return value.strip().upper() in ("", "NULL", "N/A", "NONE")


def get_yesterday() -> date:
    return date.today() - timedelta(days=1)


def parse_date(value: str) -> date | None:
    """Parse a datetime string like '2026-06-01 06:30:00' into a date."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def load_missing_cost_codes(target_date: date) -> list[dict]:
    """Return a list of worker records missing a cost code on target_date."""
    missing = []
    seen = set()  # deduplicate by (name, date, project)

    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) <= max(COST_CODE_COL, DATE_COL, NAME_COL):
                continue  # skip malformed rows

            clock_in_date = parse_date(row[DATE_COL])
            if clock_in_date != target_date:
                continue

            cost_code = row[COST_CODE_COL]
            if not is_null(cost_code):
                continue

            name    = row[NAME_COL].strip()
            emp_id  = row[ID_COL].strip()
            project = row[PROJECT_COL].strip()
            key     = (name, str(clock_in_date), project)

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
    """Compose the email message."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[BESI] Missing Cost Codes — {target_date.strftime('%B %d, %Y')}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT

    count = len(missing)

    # ── Plain-text body ──────────────────────────────────────────────────────
    lines = [
        f"Hi Yan,",
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

    # ── HTML body ────────────────────────────────────────────────────────────
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
    """Send via Gmail SMTP (TLS)."""
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT, msg.as_string())


def main():
    yesterday = get_yesterday()
    logging.info(f"Starting run for date: {yesterday}")

    if APP_PASSWORD == "YOUR_APP_PASSWORD_HERE":
        logging.error("App password not configured. Set GMAIL_APP_PASSWORD env var.")
        print("ERROR: Gmail app password not set. See PROJECT_PLAN.md — Phase 5.")
        return

    missing = load_missing_cost_codes(yesterday)
    logging.info(f"Found {len(missing)} worker(s) with missing cost codes.")

    if not missing:
        logging.info("No missing cost codes — no email sent.")
        print(f"No missing cost codes for {yesterday}. No email sent.")
        return

    msg = build_email(missing, yesterday)
    send_email(msg)
    logging.info(f"Email sent to {RECIPIENT} listing {len(missing)} worker(s).")
    print(f"Email sent to {RECIPIENT} with {len(missing)} worker(s) flagged.")


if __name__ == "__main__":
    main()
