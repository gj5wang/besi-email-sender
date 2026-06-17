# BESI Email Sender

This is a tool I built for BESI Construction that automatically sends a daily email to the supervisor listing any construction workers who forgot to fill in their cost code for the day before.

## How it works

Every morning at 8 AM the script reads the timecard CSV that gets refreshed at midnight, finds anyone with a missing cost code from the previous day, and sends a summary email to Yan.Fikh@besi.ca. There is also a web dashboard you can open to browse through the data manually and change settings like who gets the email and when it sends.

## Files in this project

**send_email.py** is the main script that does all the work. It reads the CSV, filters for missing cost codes, and sends the email.

**dashboard.py** runs a local web server you can open at http://localhost:5050 to browse the data and manage settings.

**dashboard.html** is a standalone version of the dashboard that opens directly in your browser without needing to run anything in Terminal.

**Timecards.csv** is the sample CSV I used for testing. This needs to be swapped out for the real live file when the project goes to production.

**PROJECT_PLAN.md** has the full breakdown of every phase of the project and a checklist for whoever takes this over next.

## Setup

You will need Python 3.10 or higher. No extra packages are needed since everything uses Python's built in tools.

**Setting up the Gmail app password**

The script logs into Gmail using an app password instead of your regular Gmail password. Here is how to set that up.

Log into the sender Gmail account and go to Google Account then Security. Make sure 2 Step Verification is turned on. Then go to App passwords and create a new one called BESI Email Sender. Copy the 16 character password it gives you and run this in Terminal before running the script:

```bash
export GMAIL_APP_PASSWORD="your-app-password-here"
```

**Running the script manually**

```bash
python3 send_email.py
```

**Running the dashboard**

```bash
python3 dashboard.py
```

Then open http://localhost:5050 in your browser. Or just open dashboard.html directly if you do not want to run anything in Terminal.

## Things to update before going live

These are the main variables at the top of send_email.py that need to be swapped out for production:

CSV_PATH is currently set to the sample Timecards.csv file. This needs to point to wherever the real nightly export lands on the production machine.

SENDER_EMAIL is set to gloriatesting8@gmail.com which was just used for testing. This should be changed to the official BESI email address that will actually send the alerts.

COST_CODE_COL is set to 13 which is column 14 in the CSV. If the column order ever changes in the CSV export this number will need to be updated too.

## Handoff checklist for the next person

Set up the Gmail app password using the steps above. Confirm the scheduled task is running at 8 AM every day. Swap CSV_PATH to the real live file. Swap SENDER_EMAIL to the official BESI address. Check the first few emails that go out to make sure the worker names and projects look right.

## Dashboard features

You can browse missing cost codes by date using the date tabs at the top. You can search by worker name, employee ID, or project name. There is a Send Test Email button in the Email Settings tab that lets you trigger a test email right from the browser. You can also change the recipient, sender, and send time without touching any code.

Built by Gloria Wang, June 2026
