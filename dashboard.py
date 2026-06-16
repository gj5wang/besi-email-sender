"""
BESI Email Sender — Web Dashboard
Run:  python3 dashboard.py
Then open:  http://localhost:5050
"""

import csv
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "Timecards.csv"
LOG_PATH = BASE_DIR / "email_log.txt"

COST_CODE_COL = 13
DATE_COL      = 9
NAME_COL      = 0
ID_COL        = 1
PROJECT_COL   = 5

# ── Data helpers ──────────────────────────────────────────────────────────────

def load_data():
    """Return all null-cost-code rows grouped by date."""
    by_date = defaultdict(list)
    seen = set()
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) <= COST_CODE_COL:
                continue
            cost = row[COST_CODE_COL].strip().upper()
            if cost not in ("", "NULL", "N/A", "NONE"):
                continue
            try:
                d = datetime.strptime(row[DATE_COL].strip(), "%Y-%m-%d %H:%M:%S").date()
            except ValueError:
                continue
            key = (row[NAME_COL].strip(), str(d))
            if key in seen:
                continue
            seen.add(key)
            by_date[str(d)].append({
                "name":    row[NAME_COL].strip(),
                "id":      row[ID_COL].strip(),
                "project": row[PROJECT_COL].strip(),
                "date":    str(d),
            })
    return by_date


def read_log():
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text().strip().splitlines()
    return lines[-10:]  # last 10 entries


# ── HTML template ─────────────────────────────────────────────────────────────

def render(by_date):
    dates_sorted = sorted(by_date.keys(), reverse=True)
    latest_date  = dates_sorted[0] if dates_sorted else "N/A"
    latest_count = len(by_date.get(latest_date, []))
    total_flagged = sum(len(v) for v in by_date.values())
    log_lines = read_log()

    phases = [
        ("Data Source (CSV nightly export)", True),
        ("Email Script (send_email.py)", True),
        ("Scheduler (8 AM daily)", True),
        ("Production CSV Swap", False),
        ("Gmail App Password", False),
        ("Production Sender Email", False),
        ("Validation & Monitoring", False),
    ]

    phase_rows = ""
    for i, (label, done) in enumerate(phases, 1):
        icon  = "✅" if done else "🔲"
        badge = ('<span class="badge done">Complete</span>' if done
                 else '<span class="badge pending">Pending</span>')
        phase_rows += f"<tr><td>{icon} Phase {i}</td><td>{label}</td><td>{badge}</td></tr>"

    date_options = "".join(f'<option value="{d}">{d} ({len(by_date[d])} workers)</option>'
                           for d in dates_sorted)

    worker_rows_by_date = {}
    for d, workers in by_date.items():
        rows = ""
        for i, w in enumerate(workers, 1):
            rows += (f'<tr><td>{i}</td><td>{w["name"]}</td>'
                     f'<td>{w["id"]}</td><td>{w["project"]}</td></tr>')
        worker_rows_by_date[d] = rows

    worker_data_json = json.dumps({d: by_date[d] for d in dates_sorted})

    log_html = ("".join(f"<div class='log-line'>{l}</div>" for l in log_lines)
                if log_lines else "<div class='log-line muted'>No log entries yet.</div>")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BESI Email Sender Dashboard</title>
<style>
  :root {{
    --orange: #E8611A;
    --dark:   #1a1a2e;
    --card:   #ffffff;
    --bg:     #f4f6f9;
    --text:   #2d2d2d;
    --muted:  #888;
    --border: #e0e0e0;
    --green:  #2e7d32;
    --radius: 10px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); color: var(--text); }}

  header {{
    background: var(--dark);
    color: white;
    padding: 18px 32px;
    display: flex;
    align-items: center;
    gap: 14px;
  }}
  header .logo {{ font-size: 22px; font-weight: 700; letter-spacing: 1px; }}
  header .logo span {{ color: var(--orange); }}
  header .subtitle {{ font-size: 13px; color: #aaa; margin-top: 2px; }}

  .container {{ max-width: 1100px; margin: 0 auto; padding: 28px 20px; }}

  .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 28px; }}
  .stat-card {{
    background: var(--card); border-radius: var(--radius);
    padding: 20px 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08);
  }}
  .stat-card .label {{ font-size: 12px; text-transform: uppercase; color: var(--muted); letter-spacing: .5px; }}
  .stat-card .value {{ font-size: 32px; font-weight: 700; margin-top: 4px; color: var(--dark); }}
  .stat-card .sub   {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
  .stat-card.accent .value {{ color: var(--orange); }}

  .section {{
    background: var(--card); border-radius: var(--radius);
    box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 24px; overflow: hidden;
  }}
  .section-header {{
    padding: 16px 24px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
  }}
  .section-header h2 {{ font-size: 15px; font-weight: 600; }}
  .section-body {{ padding: 20px 24px; }}

  select {{
    padding: 7px 12px; border-radius: 6px; border: 1px solid var(--border);
    font-size: 13px; background: white; cursor: pointer;
  }}

  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{ text-align: left; padding: 10px 14px; background: #f9f9f9;
        font-size: 12px; text-transform: uppercase; color: var(--muted);
        border-bottom: 1px solid var(--border); }}
  td {{ padding: 11px 14px; border-bottom: 1px solid #f0f0f0; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #fafafa; }}

  .badge {{
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600;
  }}
  .badge.done    {{ background: #e8f5e9; color: var(--green); }}
  .badge.pending {{ background: #fff3e0; color: #e65100; }}

  .log-line {{ font-family: monospace; font-size: 12px; padding: 4px 0;
               border-bottom: 1px solid #f0f0f0; color: #444; }}
  .log-line.muted {{ color: var(--muted); }}

  .config-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  .config-item .key   {{ font-size: 11px; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; }}
  .config-item .val   {{ font-size: 13px; font-family: monospace; background: #f4f6f9;
                         padding: 7px 10px; border-radius: 6px; }}

  footer {{ text-align: center; color: var(--muted); font-size: 12px; padding: 20px 0 40px; }}
</style>
</head>
<body>

<header>
  <div>
    <div class="logo"><span>BESI</span> Email Sender</div>
    <div class="subtitle">Automated Cost Code Alert System — Dashboard</div>
  </div>
</header>

<div class="container">

  <!-- Stats -->
  <div class="stats">
    <div class="stat-card accent">
      <div class="label">Flagged — Latest Date</div>
      <div class="value">{latest_count}</div>
      <div class="sub">workers missing cost code on {latest_date}</div>
    </div>
    <div class="stat-card">
      <div class="label">Total Flagged (all dates)</div>
      <div class="value">{total_flagged}</div>
      <div class="sub">unique worker-day combinations</div>
    </div>
    <div class="stat-card">
      <div class="label">Next Scheduled Run</div>
      <div class="value" style="font-size:22px;margin-top:8px;">8:00 AM</div>
      <div class="sub">daily — after 12 AM CSV refresh</div>
    </div>
  </div>

  <!-- Missing Cost Codes Table -->
  <div class="section">
    <div class="section-header">
      <h2>Workers with Missing Cost Code</h2>
      <select id="dateSelect" onchange="filterDate(this.value)">
        {date_options}
      </select>
    </div>
    <div class="section-body" style="padding:0;">
      <table>
        <thead>
          <tr><th>#</th><th>Name</th><th>Employee ID</th><th>Project</th></tr>
        </thead>
        <tbody id="workerTable"></tbody>
      </table>
    </div>
  </div>

  <!-- Phase Tracker -->
  <div class="section">
    <div class="section-header"><h2>Project Phases</h2></div>
    <div class="section-body" style="padding:0;">
      <table>
        <thead><tr><th>Phase</th><th>Description</th><th>Status</th></tr></thead>
        <tbody>{phase_rows}</tbody>
      </table>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">

    <!-- Config -->
    <div class="section">
      <div class="section-header"><h2>Configuration</h2></div>
      <div class="section-body">
        <div class="config-grid">
          <div class="config-item">
            <div class="key">CSV Path</div>
            <div class="val">Timecards.csv</div>
          </div>
          <div class="config-item">
            <div class="key">Recipient</div>
            <div class="val">Yan.Fikh@besi.ca</div>
          </div>
          <div class="config-item">
            <div class="key">Sender Email</div>
            <div class="val">gloriatesting8@gmail.com</div>
          </div>
          <div class="config-item">
            <div class="key">Cost Code Column</div>
            <div class="val">Index 13 (col 14)</div>
          </div>
          <div class="config-item">
            <div class="key">Schedule</div>
            <div class="val">0 8 * * * (daily 8 AM)</div>
          </div>
          <div class="config-item">
            <div class="key">App Password</div>
            <div class="val">⚠ Not configured</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Log -->
    <div class="section">
      <div class="section-header"><h2>Run Log</h2></div>
      <div class="section-body">
        {log_html}
      </div>
    </div>

  </div>

</div>

<footer>BESI Construction — Internal Tool · Refreshes on page reload</footer>

<script>
const data = {worker_data_json};

function filterDate(d) {{
  const workers = data[d] || [];
  const tbody = document.getElementById('workerTable');
  tbody.innerHTML = workers.map((w, i) =>
    `<tr><td>${{i+1}}</td><td>${{w.name}}</td><td>${{w.id}}</td><td>${{w.project}}</td></tr>`
  ).join('');
}}

// Load first date on page load
const firstDate = document.getElementById('dateSelect').value;
if (firstDate) filterDate(firstDate);
</script>
</body>
</html>"""


# ── Simple HTTP server ────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        by_date = load_data()
        html = render(by_date).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, format, *args):
        pass  # suppress request logs


if __name__ == "__main__":
    port = 5050
    print(f"Dashboard running → http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    HTTPServer(("", port), Handler).serve_forever()
