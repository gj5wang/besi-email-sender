"""
BESI Email Sender — Web Dashboard
Run:  python3 dashboard.py
Then open:  http://localhost:5050
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR     = Path(__file__).parent
CSV_PATH     = BASE_DIR / "Timecards.csv"
LOG_PATH     = BASE_DIR / "email_log.txt"
SETTINGS_PATH = BASE_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "recipient":   "Yan.Fikh@besi.ca",
    "sender":      "gloriatesting8@gmail.com",
    "send_time":   "08:00",
    "enabled":     True,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_settings():
    if SETTINGS_PATH.exists():
        return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_PATH.read_text())}
    return DEFAULT_SETTINGS.copy()

def save_settings(data):
    SETTINGS_PATH.write_text(json.dumps(data, indent=2))

def load_data():
    by_date = defaultdict(list)
    seen = set()
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) <= 13: continue
            cost = row[13].strip().upper()
            if cost not in ("", "NULL", "N/A", "NONE"): continue
            try:
                d = datetime.strptime(row[9].strip(), "%Y-%m-%d %H:%M:%S").date()
            except: continue
            key = (row[0].strip(), str(d), row[5].strip())
            if key in seen: continue
            seen.add(key)
            by_date[str(d)].append({
                "name":       row[0].strip(),
                "id":         row[1].strip(),
                "role":       row[4].strip(),
                "project":    row[5].strip(),
                "clockIn":    row[9].strip(),
                "clockOut":   row[10].strip(),
            })
    return by_date

def read_log():
    if not LOG_PATH.exists(): return []
    return LOG_PATH.read_text().strip().splitlines()[-8:]

# ── HTML ──────────────────────────────────────────────────────────────────────

def render_page(by_date, settings):
    dates_sorted  = sorted(by_date.keys(), reverse=True)
    total_flagged = sum(len(v) for v in by_date.values())
    data_json     = json.dumps(by_date)
    log_lines     = read_log()

    date_tabs = ""
    for d in dates_sorted[:10]:
        count = len(by_date[d])
        date_tabs += f'<button class="date-tab" data-date="{d}" onclick="selectDate(\'{d}\')">{d} <span class="tab-count">{count}</span></button>'

    log_html = "".join(
        f'<div class="log-row">{l}</div>' for l in log_lines
    ) if log_lines else '<div class="log-row muted">No log entries yet.</div>'

    enabled_checked = "checked" if settings.get("enabled", True) else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BESI — Cost Code Monitor</title>
<style>
  :root {{
    --green:      #2a6e3f;
    --green-dark: #1d4f2d;
    --green-light:#e8f4ec;
    --green-mid:  #3d8f56;
    --white:      #ffffff;
    --bg:         #f5f7f5;
    --border:     #d8e8dc;
    --text:       #1a1a1a;
    --muted:      #6b7c6e;
    --red:        #c0392b;
    --radius:     4px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); color: var(--text); font-size: 14px; }}

  /* ── Top bar ── */
  .topbar {{
    background: var(--white);
    border-bottom: 1px solid var(--border);
    padding: 8px 32px;
    font-size: 12px;
    color: var(--muted);
    display: flex;
    gap: 24px;
  }}
  .topbar span {{ color: var(--green); font-weight: 600; }}

  /* ── Header ── */
  header {{
    background: var(--white);
    border-bottom: 2px solid var(--border);
    padding: 0 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 64px;
  }}
  .logo {{ display: flex; align-items: center; gap: 12px; text-decoration: none; }}
  .logo-hex {{
    width: 40px; height: 40px;
    background: var(--green);
    clip-path: polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%);
    display: flex; align-items: center; justify-content: center;
    color: white; font-weight: 900; font-size: 18px; letter-spacing: -1px;
  }}
  .logo-text {{ font-size: 22px; font-weight: 300; color: var(--green-dark); letter-spacing: 1px; }}
  .logo-text strong {{ font-weight: 700; }}

  nav {{ display: flex; gap: 0; }}
  nav a {{
    padding: 0 18px; height: 64px; display: flex; align-items: center;
    text-decoration: none; color: var(--text); font-size: 13px; font-weight: 500;
    border-bottom: 3px solid transparent; transition: all .15s;
  }}
  nav a:hover, nav a.active {{ color: var(--green); border-bottom-color: var(--green); }}

  /* ── Page shell ── */
  .page-header {{
    background: var(--green);
    color: white;
    padding: 24px 32px;
  }}
  .page-header h1 {{ font-size: 20px; font-weight: 300; letter-spacing: .5px; }}
  .page-header h1 strong {{ font-weight: 700; }}
  .page-header p {{ font-size: 13px; opacity: .8; margin-top: 4px; }}

  .container {{ max-width: 1200px; margin: 0 auto; padding: 28px 20px; }}

  /* ── Stat cards ── */
  .stats {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 24px; }}
  .stat {{
    background: var(--white); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 18px 20px;
  }}
  .stat .label {{ font-size: 11px; text-transform: uppercase; color: var(--muted); letter-spacing: .5px; }}
  .stat .value {{ font-size: 28px; font-weight: 700; color: var(--green-dark); margin-top: 4px; }}
  .stat .sub   {{ font-size: 11px; color: var(--muted); margin-top: 3px; }}
  .stat.alert .value {{ color: var(--red); }}

  /* ── Panels ── */
  .panel {{
    background: var(--white); border: 1px solid var(--border);
    border-radius: var(--radius); margin-bottom: 20px; overflow: hidden;
  }}
  .panel-header {{
    background: var(--green-dark); color: white;
    padding: 12px 20px; font-size: 13px; font-weight: 600;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .panel-body {{ padding: 20px; }}

  /* ── Date tabs ── */
  .date-tabs {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }}
  .date-tab {{
    padding: 6px 14px; border: 1px solid var(--border); border-radius: 20px;
    background: var(--white); cursor: pointer; font-size: 12px; color: var(--muted);
    transition: all .15s;
  }}
  .date-tab:hover {{ border-color: var(--green); color: var(--green); }}
  .date-tab.active {{ background: var(--green); color: white; border-color: var(--green); }}
  .tab-count {{
    display: inline-block; background: rgba(255,255,255,.3);
    border-radius: 10px; padding: 0 6px; margin-left: 4px; font-size: 11px;
  }}
  .date-tab:not(.active) .tab-count {{ background: var(--green-light); color: var(--green); }}

  /* ── Search bar ── */
  .search-bar {{
    display: flex; gap: 10px; margin-bottom: 16px; align-items: center;
  }}
  .search-bar input {{
    flex: 1; padding: 8px 12px; border: 1px solid var(--border);
    border-radius: var(--radius); font-size: 13px; outline: none;
  }}
  .search-bar input:focus {{ border-color: var(--green); }}
  .result-count {{ font-size: 12px; color: var(--muted); white-space: nowrap; }}

  /* ── Table ── */
  table {{ width: 100%; border-collapse: collapse; }}
  th {{
    text-align: left; padding: 9px 14px;
    font-size: 11px; text-transform: uppercase; color: var(--muted);
    border-bottom: 2px solid var(--border); background: #fafafa;
    letter-spacing: .4px; cursor: pointer; user-select: none;
  }}
  th:hover {{ color: var(--green); }}
  td {{ padding: 11px 14px; border-bottom: 1px solid #f0f0f0; font-size: 13px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: var(--green-light); }}
  .empty-row td {{ text-align: center; color: var(--muted); padding: 32px; }}

  .badge-role {{
    display: inline-block; padding: 2px 8px; border-radius: 3px;
    font-size: 11px; background: var(--green-light); color: var(--green-dark);
  }}

  /* ── Two-col layout ── */
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}

  /* ── Settings form ── */
  .form-group {{ margin-bottom: 18px; }}
  .form-group label {{
    display: block; font-size: 11px; text-transform: uppercase;
    color: var(--muted); letter-spacing: .4px; margin-bottom: 6px;
  }}
  .form-group input[type=text],
  .form-group input[type=time],
  .form-group input[type=email] {{
    width: 100%; padding: 8px 12px; border: 1px solid var(--border);
    border-radius: var(--radius); font-size: 13px; outline: none;
  }}
  .form-group input:focus {{ border-color: var(--green); }}

  .toggle-row {{ display: flex; align-items: center; gap: 12px; }}
  .toggle {{
    position: relative; width: 44px; height: 24px;
    background: #ccc; border-radius: 12px; cursor: pointer;
    transition: background .2s;
  }}
  .toggle.on {{ background: var(--green); }}
  .toggle::after {{
    content: ''; position: absolute; top: 3px; left: 3px;
    width: 18px; height: 18px; border-radius: 50%; background: white;
    transition: left .2s;
  }}
  .toggle.on::after {{ left: 23px; }}
  .toggle-label {{ font-size: 13px; }}

  .btn {{
    padding: 9px 22px; border-radius: var(--radius); border: none;
    font-size: 13px; font-weight: 600; cursor: pointer; transition: background .15s;
  }}
  .btn-green {{ background: var(--green); color: white; }}
  .btn-green:hover {{ background: var(--green-dark); }}
  .btn-outline {{
    background: white; color: var(--green);
    border: 1px solid var(--green);
  }}
  .btn-outline:hover {{ background: var(--green-light); }}

  .save-row {{ display: flex; gap: 10px; margin-top: 20px; }}

  /* ── Log ── */
  .log-row {{
    font-family: monospace; font-size: 11px; padding: 5px 0;
    border-bottom: 1px solid #f4f4f4; color: #444;
  }}
  .log-row.muted {{ color: var(--muted); }}

  .saved-msg {{
    display: none; color: var(--green); font-size: 12px;
    font-weight: 600; align-items: center; gap: 4px;
  }}

  footer {{
    text-align: center; color: var(--muted); font-size: 11px;
    padding: 24px 0 40px; border-top: 1px solid var(--border); margin-top: 8px;
  }}
</style>
</head>
<body>

<!-- Top info bar -->
<div class="topbar">
  <div>Cost Code Monitor — Internal Tool</div>
  <div>Total flagged (all dates): <span>{total_flagged}</span></div>
  <div>CSV refreshes nightly at 12:00 AM</div>
</div>

<!-- Header -->
<header>
  <a class="logo" href="#">
    <div class="logo-hex">B</div>
    <div class="logo-text"><strong>Besi</strong></div>
  </a>
  <nav>
    <a href="#" onclick="showTab('monitor')">Cost Code Monitor</a>
    <a href="#" onclick="showTab('settings')">Email Settings</a>
    <a href="#" onclick="showTab('log')">Run Log</a>
  </nav>
</header>

<!-- Page header -->
<div class="page-header">
  <h1><strong>Cost Code</strong> Monitor</h1>
  <p>Workers who clocked in without submitting a cost code — updated nightly</p>
</div>

<div class="container">

  <!-- Stats -->
  <div class="stats">
    <div class="stat alert">
      <div class="label">Flagged Today</div>
      <div class="value" id="statToday">—</div>
      <div class="sub">for selected date</div>
    </div>
    <div class="stat">
      <div class="label">Total Flagged</div>
      <div class="value">{total_flagged}</div>
      <div class="sub">across all dates in CSV</div>
    </div>
    <div class="stat">
      <div class="label">Dates with Issues</div>
      <div class="value">{len(dates_sorted)}</div>
      <div class="sub">distinct dates</div>
    </div>
    <div class="stat">
      <div class="label">Email Schedule</div>
      <div class="value" style="font-size:20px;padding-top:6px;">{settings['send_time']}</div>
      <div class="sub">daily — to {settings['recipient']}</div>
    </div>
  </div>

  <!-- Main table tab -->
  <div id="tab-monitor">

    <div class="panel">
      <div class="panel-header">
        <span>Workers with Missing Cost Code</span>
        <span id="headerDate" style="font-weight:300;font-size:12px;opacity:.8;"></span>
      </div>
      <div class="panel-body">

        <div class="date-tabs" id="dateTabs">
          {date_tabs}
        </div>

        <div class="search-bar">
          <input type="text" id="searchBox" placeholder="Search by name, ID, or project…" oninput="filterTable()">
          <span class="result-count" id="resultCount"></span>
        </div>

        <table>
          <thead>
            <tr>
              <th onclick="sortTable(0)">#</th>
              <th onclick="sortTable(1)">Name ↕</th>
              <th onclick="sortTable(2)">Employee ID ↕</th>
              <th onclick="sortTable(3)">Role</th>
              <th onclick="sortTable(4)">Project ↕</th>
              <th onclick="sortTable(5)">Clock In</th>
              <th onclick="sortTable(6)">Clock Out</th>
            </tr>
          </thead>
          <tbody id="workerTable"></tbody>
        </table>

      </div>
    </div>

  </div>

  <!-- Settings tab -->
  <div id="tab-settings" style="display:none;">
    <div class="two-col">

      <div class="panel">
        <div class="panel-header">Email Settings</div>
        <div class="panel-body">

          <div class="form-group">
            <label>Recipient Email</label>
            <input type="email" id="s-recipient" value="{settings['recipient']}">
          </div>
          <div class="form-group">
            <label>Sender Email</label>
            <input type="email" id="s-sender" value="{settings['sender']}">
          </div>
          <div class="form-group">
            <label>Send Time (daily)</label>
            <input type="time" id="s-time" value="{settings['send_time']}">
          </div>
          <div class="form-group">
            <label>Automated Sending</label>
            <div class="toggle-row">
              <div class="toggle {'on' if settings['enabled'] else ''}" id="toggleEl" onclick="toggleEnabled()"></div>
              <span class="toggle-label" id="toggleLabel">{'Enabled' if settings['enabled'] else 'Disabled'}</span>
            </div>
          </div>

          <div class="save-row">
            <button class="btn btn-green" onclick="saveSettings()">Save Settings</button>
            <span class="saved-msg" id="savedMsg">✓ Saved</span>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">Configuration Reference</div>
        <div class="panel-body">
          <table>
            <tr><td style="color:var(--muted);font-size:12px;padding:8px 0;border-bottom:1px solid #f0f0f0;">CSV Path</td><td style="padding:8px 0;border-bottom:1px solid #f0f0f0;font-family:monospace;font-size:12px;">Timecards.csv</td></tr>
            <tr><td style="color:var(--muted);font-size:12px;padding:8px 0;border-bottom:1px solid #f0f0f0;">Cost Code Column</td><td style="padding:8px 0;border-bottom:1px solid #f0f0f0;font-family:monospace;font-size:12px;">Index 13</td></tr>
            <tr><td style="color:var(--muted);font-size:12px;padding:8px 0;border-bottom:1px solid #f0f0f0;">Date Column</td><td style="padding:8px 0;border-bottom:1px solid #f0f0f0;font-family:monospace;font-size:12px;">Index 9</td></tr>
            <tr><td style="color:var(--muted);font-size:12px;padding:8px 0;">CSV Refresh</td><td style="padding:8px 0;font-family:monospace;font-size:12px;">12:00 AM nightly</td></tr>
          </table>
          <p style="margin-top:16px;font-size:12px;color:var(--muted);line-height:1.6;">
            To update the Gmail app password, set the <code>GMAIL_APP_PASSWORD</code> environment variable before running the script.
          </p>
        </div>
      </div>

    </div>
  </div>

  <!-- Log tab -->
  <div id="tab-log" style="display:none;">
    <div class="panel">
      <div class="panel-header">Run Log (last 8 entries)</div>
      <div class="panel-body">
        {log_html}
      </div>
    </div>
  </div>

</div>

<footer>BESI Construction — Internal Tool &nbsp;·&nbsp; Refreshes on page reload</footer>

<script>
const DATA = {data_json};
let currentDate = '';
let sortCol = -1, sortAsc = true;
let toggleState = {'true' if settings['enabled'] else 'false'};

// ── Tab navigation ──────────────────────────────────────────────────────────
function showTab(name) {{
  event.preventDefault();
  ['monitor','settings','log'].forEach(t => {{
    document.getElementById('tab-'+t).style.display = t===name ? '' : 'none';
  }});
  document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
  event.target.classList.add('active');
}}

// ── Date selection ──────────────────────────────────────────────────────────
function selectDate(d) {{
  currentDate = d;
  document.querySelectorAll('.date-tab').forEach(b => {{
    b.classList.toggle('active', b.dataset.date === d);
  }});
  document.getElementById('headerDate').textContent = d;
  document.getElementById('statToday').textContent = (DATA[d]||[]).length;
  document.getElementById('searchBox').value = '';
  renderTable(DATA[d]||[]);
}}

// ── Table render ────────────────────────────────────────────────────────────
function renderTable(rows) {{
  const tbody = document.getElementById('workerTable');
  if (!rows.length) {{
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">No workers flagged for this date.</td></tr>';
    document.getElementById('resultCount').textContent = '0 results';
    return;
  }}
  tbody.innerHTML = rows.map((w,i) => `
    <tr>
      <td style="color:var(--muted)">${{i+1}}</td>
      <td><strong>${{w.name}}</strong></td>
      <td style="color:var(--muted)">${{w.id}}</td>
      <td><span class="badge-role">${{w.role}}</span></td>
      <td>${{w.project}}</td>
      <td style="color:var(--muted);font-size:12px;">${{w.clockIn.split(' ')[1]||''}}</td>
      <td style="color:var(--muted);font-size:12px;">${{w.clockOut.split(' ')[1]||''}}</td>
    </tr>`).join('');
  document.getElementById('resultCount').textContent = rows.length + ' worker' + (rows.length!==1?'s':'');
}}

// ── Search ──────────────────────────────────────────────────────────────────
function filterTable() {{
  const q = document.getElementById('searchBox').value.toLowerCase();
  const rows = (DATA[currentDate]||[]).filter(w =>
    w.name.toLowerCase().includes(q) ||
    w.id.includes(q) ||
    w.project.toLowerCase().includes(q)
  );
  renderTable(rows);
}}

// ── Sort ────────────────────────────────────────────────────────────────────
function sortTable(col) {{
  if (sortCol===col) sortAsc=!sortAsc; else {{ sortCol=col; sortAsc=true; }}
  const keys = ['_idx','name','id','role','project','clockIn','clockOut'];
  const rows = [...(DATA[currentDate]||[])].sort((a,b) => {{
    const av = col===0 ? 0 : (a[keys[col]]||'');
    const bv = col===0 ? 0 : (b[keys[col]]||'');
    return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
  }});
  renderTable(rows);
}}

// ── Toggle ──────────────────────────────────────────────────────────────────
function toggleEnabled() {{
  toggleState = !toggleState;
  const el = document.getElementById('toggleEl');
  el.classList.toggle('on', toggleState);
  document.getElementById('toggleLabel').textContent = toggleState ? 'Enabled' : 'Disabled';
}}

// ── Save settings ───────────────────────────────────────────────────────────
function saveSettings() {{
  const payload = {{
    recipient: document.getElementById('s-recipient').value,
    sender:    document.getElementById('s-sender').value,
    send_time: document.getElementById('s-time').value,
    enabled:   toggleState,
  }};
  fetch('/save-settings', {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify(payload)
  }}).then(r => r.json()).then(() => {{
    const msg = document.getElementById('savedMsg');
    msg.style.display = 'flex';
    setTimeout(() => msg.style.display='none', 2500);
  }});
}}

// ── Init ────────────────────────────────────────────────────────────────────
const dates = Object.keys(DATA).sort().reverse();
if (dates.length) selectDate(dates[0]);
</script>
</body>
</html>"""


# ── Server ────────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        by_date  = load_data()
        settings = load_settings()
        html = render_page(by_date, settings).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def do_POST(self):
        if self.path == "/save-settings":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)
            s      = load_settings()
            s.update(data)
            save_settings(s)
            resp = json.dumps({"ok": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

    def log_message(self, *args): pass


if __name__ == "__main__":
    port = 5050
    print(f"Dashboard → http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    HTTPServer(("", port), Handler).serve_forever()
