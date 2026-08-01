"""The web view, behind a login. Standard library only - no framework, no build.

CLI first (§10); this exists because the map wants a screen and because a phone
in a shed is easier than a laptop.
"""

import html
import json
import os
import urllib.parse
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import (auth, config, db, ledger, money, planner, priority, rotation,
               seed, stock, sun, weeds)
from .cli import hm, refresh
from .rules import parse

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
DB_PATH = None

NAV = [("/", "Today"), ("/week", "Week"), ("/map", "Map"), ("/stock", "Stock"),
       ("/shop", "Shop"), ("/money", "Money"), ("/time", "Time"), ("/report", "Report")]


def e(s):
    return html.escape(str(s if s is not None else ""))


CSS = """
:root{--ground:#111917;--ground-2:#1C2722;--bone:#FFF;--dim:#D8E0D9;--rule:#4A5C52;
--sun:#FFD166;--alert:#FF8B7E;--green:#8FC46B;
--ui:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
--data:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--bone);font-family:var(--ui);font-weight:500}
.wrap{max-width:820px;margin:0 auto;padding:18px 15px 70px}
header{border-bottom:1px solid var(--rule);padding-bottom:12px;margin-bottom:16px;
display:flex;justify-content:space-between;align-items:flex-end;gap:10px;flex-wrap:wrap}
.sub{font-family:var(--data);font-size:10.5px;font-weight:700;letter-spacing:.14em;
text-transform:uppercase;color:var(--sun);margin:0 0 6px}
h1{font-size:clamp(24px,5vw,34px);font-weight:800;letter-spacing:-.02em;margin:0;line-height:1}
h2{font-size:17px;font-weight:800;margin:24px 0 8px}
p{font-size:15px;line-height:1.5;margin:0 0 10px;color:var(--dim)}
nav{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}
nav a{font-family:var(--data);font-size:11px;font-weight:700;letter-spacing:.09em;
text-transform:uppercase;text-decoration:none;color:var(--dim);border:1px solid var(--rule);
padding:7px 11px}
nav a:hover,nav a.on{color:#111917;background:var(--sun);border-color:var(--sun)}
.job{border:1px solid var(--rule);border-left:3px solid var(--sun);padding:11px 13px;
margin-bottom:9px;display:flex;gap:12px;align-items:flex-start;justify-content:space-between}
.job.blocked{border-left-color:var(--alert);opacity:.75}
.job h3{margin:0 0 3px;font-size:16px;font-weight:800}
.job .why{font-family:var(--data);font-size:11.5px;color:var(--sun);letter-spacing:.03em}
.job .meta{font-family:var(--data);font-size:11px;color:var(--dim);white-space:nowrap}
.risk{border:1px solid var(--alert);border-left:3px solid var(--alert);padding:9px 12px;
margin-bottom:8px;font-size:14px}
.risk b{font-family:var(--data);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
color:var(--alert);display:block;margin-bottom:3px}
table{width:100%;border-collapse:collapse;font-size:14px}
th{font-family:var(--data);font-size:10.5px;letter-spacing:.11em;text-transform:uppercase;
text-align:left;color:var(--dim);border-bottom:1px solid var(--rule);padding:7px 6px}
td{padding:7px 6px;border-bottom:1px solid rgba(74,92,82,.4)}
td.num{text-align:right;font-family:var(--data)}
form.inline{display:inline}
input,select,textarea{font-family:var(--ui);font-size:15px;padding:9px 10px;
background:var(--ground-2);border:1px solid var(--rule);color:var(--bone);width:100%}
label{display:block;font-family:var(--data);font-size:10.5px;font-weight:700;
letter-spacing:.11em;text-transform:uppercase;color:var(--dim);margin:12px 0 5px}
button,.btn{font-family:var(--ui);font-weight:700;font-size:14px;padding:9px 14px;
background:none;border:1px solid var(--rule);color:var(--dim);cursor:pointer}
button:hover{color:#111917;background:var(--sun);border-color:var(--sun)}
button.go{background:var(--sun);border-color:var(--sun);color:#111917}
.row{display:flex;gap:10px;flex-wrap:wrap}
.row>div{flex:1;min-width:150px}
.stat{font-family:var(--data);font-size:12.5px;color:var(--sun);letter-spacing:.05em}
.err{border:1px solid var(--alert);color:var(--alert);padding:10px 12px;margin-bottom:12px;
font-size:14px}
.login{max-width:340px;margin:12vh auto}
.foot{font-family:var(--data);font-size:10.5px;color:var(--dim);letter-spacing:.09em;
text-transform:uppercase;margin-top:26px;border-top:1px solid var(--rule);padding-top:12px}
"""


# A leaf, drawn in the page's own colours. Inline so nothing has to be fetched -
# without it every page load asks for /favicon.ico and gets a 404.
FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" fill="#111917"/>'
    '<path d="M8 25C8 13 16 7 25 7c0 11-7 18-17 18z" fill="#8FC46B"/>'
    '<path d="M8 25C12 19 18 14 25 11" stroke="#111917" stroke-width="2" fill="none"/>'
    '</svg>')
ROBOTS = "User-agent: *\nDisallow: /\n"


def page(title, body, sess=None, path="/"):
    nav = ""
    if sess:
        nav = "<nav>" + "".join(
            '<a class="%s" href="%s">%s</a>' % ("on" if p == path else "", p, n)
            for p, n in NAV) + '<a href="/logout" onclick="return confirm(\'Log out?\')">Log out</a></nav>'
    return ("<!doctype html><html lang=en><head><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1'>"
            "<link rel=icon href='/favicon.ico' type='image/svg+xml'>"
            "<title>%s</title><style>%s</style></head><body><div class=wrap>"
            "<header><div><p class=sub>%s</p><h1>%s</h1></div></header>%s%s"
            "<p class=foot>Albert Village &middot; 11.4 x 11.4 m &middot; organic only "
            "&middot; no vehicle access</p></div></body></html>"
            % (e(title), CSS, e(config.SITE_NAME), e(title), nav, body))


# --------------------------------------------------------------------- views

def view_today(conn, sess, q):
    today = parse(q.get("date", [None])[0]) if q.get("date") else date.today()
    wx, err = refresh(conn, today)
    v = priority.plan_day(conn, today, wx)
    out = ['<p class=stat>%s &middot; %s</p>' % (e(today.strftime("%A %d %B")), e(v["weather"]))]
    if err:
        out.append('<p class=stat>Weather cache stale: %s</p>' % e(err))

    for kind, msg in v["risks"]:
        out.append('<div class=risk><b>%s</b>%s</div>' % (e(kind), e(msg)))

    out.append("<h2>Today</h2>")
    if not v["top"]:
        out.append("<p>Nothing scheduled. Have a look round anyway.</p>")
    for s in v["top"]:
        out.append(job_card(s, sess))
    if v["every_visit"]:
        out.append("<h2>Every visit</h2>")
        for ev in v["every_visit"]:
            out.append('<div class=job><div><h3>%s</h3><span class=why>%s</span></div>'
                       '<span class=meta>%s %s</span></div>'
                       % (e(ev["title"]), "Always", e(ev["owner"]), hm(ev["minutes"])))
    if v["also"]:
        out.append("<h2>Also due</h2>")
        for s in v["also"][:8]:
            out.append(job_card(s, sess))
    if v["blocked"]:
        out.append("<h2>Blocked</h2>")
        for s in v["blocked"][:10]:
            out.append(job_card(s, sess, blocked=True))

    out.append('<p class=stat>Estimated total %s &middot; planned for %s %sh, logged %sh</p>'
               % (hm(v["minutes"]), today.strftime("%B"), v["hours"]["planned_h"],
                  v["hours"]["logged_h"]))
    if v["inspection"]:
        out.append('<p class=stat>Next inspection %s (%d days)</p>'
                   % (v["inspection"], (v["inspection"] - today).days))

    out.append(visit_form(conn, sess))
    return "".join(out)


def job_card(s, sess, blocked=False):
    btn = ""
    if not blocked:
        btn = ('<form method=post action="/done" class=inline>'
               '<input type=hidden name=csrf value="%s">'
               '<input type=hidden name=run_id value="%d">'
               '<button class=go>Done</button></form>' % (e(sess["csrf"]), s["run_id"]))
    return ('<div class="job%s"><div><h3>%s</h3><span class=why>%s</span></div>'
            '<div style="text-align:right"><span class=meta>%s &middot; %s</span><br>%s</div></div>'
            % (" blocked" if blocked else "", e(s["title"]), e(s["why"]),
               e(s["owner"]), hm(s["minutes"]), btn))


def visit_form(conn, sess):
    v = ledger.current_visit(conn)
    if v:
        return ('<h2>Visit in progress</h2><form method=post action="/leave">'
                '<input type=hidden name=csrf value="%s">'
                '<div class=row><div><label>Mood</label><select name=mood>%s</select></div>'
                '<div><label>Notes</label><input name=notes placeholder="slugs got the lettuce">'
                '</div></div><p></p><button class=go>Leave - close the visit</button></form>'
                % (e(sess["csrf"]),
                   "".join('<option>%s</option>' % m for m in ledger.MOODS)))
    return ('<h2>Log a visit</h2><form method=post action="/log">'
            '<input type=hidden name=csrf value="%s">'
            '<div class=row><div><label>Minutes</label><input name=minutes type=number required>'
            '</div><div><label>Who</label><select name=who>'
            '<option>Both</option><option>Grower</option><option>Site</option></select></div>'
            '<div><label>Mood</label><select name=mood>%s</select></div></div>'
            '<label>Notes</label><input name=notes>'
            '<p></p><button class=go>Log it</button> '
            '<button name=arrive value=1>Or start the clock now</button></form>'
            % (e(sess["csrf"]), "".join('<option>%s</option>' % m for m in ledger.MOODS)))


def view_week(conn, sess, q):
    today = date.today()
    wx, _ = refresh(conn, today)
    w = planner.plan_week(conn, today, wx)
    out = ['<p class=stat>Budget: 4h Saturday, 3h Sunday, 30m midweek</p>']
    for day in w["days"]:
        d = day["date"]
        out.append("<h2>%s &middot; %s of %s</h2>"
                   % (e(d.strftime("%A %d %b")), hm(day["used"]), hm(day["budget"])))
        if not day["items"]:
            out.append("<p>Nothing due.</p>")
        for it in day["items"]:
            out.append('<div class=job><div><h3>%s</h3><span class=why>%s</span></div>'
                       '<span class=meta>%s &middot; %s</span></div>'
                       % (e(it["title"]), e(it["why"]), e(it["owner"]), hm(it["minutes"])))
    if w["deferred"]:
        out.append("<h2>Deferred</h2>")
        for df in w["deferred"]:
            tail = " Needs %s." % df["unblocks"] if df["unblocks"] else ""
            out.append('<div class=risk><b>%s</b>%s.%s</div>'
                       % (e(df["title"]), e(df["why"]), e(tail)))
    return "".join(out)


def view_stock(conn, sess, q):
    rows = conn.execute("SELECT * FROM stock ORDER BY category, item").fetchall()
    out = ["<table><tr><th>Item</th><th>Category</th><th class=num>Qty</th>"
           "<th class=num>Reorder</th><th>Where</th><th></th></tr>"]
    for r in rows:
        low = r["qty"] <= r["reorder_at"]
        out.append('<tr><td>%s%s</td><td>%s</td><td class=num>%g %s</td>'
                   '<td class=num>%g</td><td>%s</td><td>'
                   '<form method=post action="/stockmove" class=inline>'
                   '<input type=hidden name=csrf value="%s"><input type=hidden name=id value="%d">'
                   '<input name=delta size=4 style="width:70px;display:inline-block" '
                   'placeholder="+/-"><button>Move</button></form></td></tr>'
                   % (e(r["item"]), " &larr; reorder" if low else "", e(r["category"]),
                      r["qty"], e(r["unit"] or ""), r["reorder_at"], e(r["location"]),
                      e(sess["csrf"]), r["id"]))
    out.append("</table>")
    exp = stock.seed_review(conn)
    if exp:
        out.append("<h2>Seed viability</h2>")
        for item, note in exp:
            out.append('<div class=risk><b>%s</b>%s</div>' % (e(item), e(note)))
    return "".join(out)


def view_shop(conn, sess, q):
    lines = stock.shopping_list(conn)
    if not lines:
        return "<p>Nothing needed. Reorder points are all clear.</p>"
    by_vendor = {}
    for l in lines:
        by_vendor.setdefault(l["vendor"], []).append(l)
    out, total = [], 0.0
    for vendor, items in by_vendor.items():
        out.append("<h2>%s</h2><table><tr><th>Item</th><th class=num>Qty</th>"
                   "<th class=num>Cost</th><th>Budget line</th><th>Carry</th></tr>" % e(vendor))
        for l in items:
            total += l["cost"]
            carry = ("%d barrow trip%s, +%s" % (l["trips"], "" if l["trips"] == 1 else "s",
                                                hm(l["barrow_minutes"]))
                     if l["trips"] else "carry")
            out.append('<tr><td>%s<br><span class=why>%s</span></td><td class=num>%g</td>'
                       '<td class=num>£%.2f</td><td>%s</td><td>%s</td></tr>'
                       % (e(l["item"]), e("; ".join(l["why"])), l["qty"], l["cost"],
                          e(l["budget_line"]), e(carry)))
        out.append("</table>")
    out.append('<p class=stat>Estimated £%.2f. Bulk items are estimated at 60 kg or 0.1 m³ '
               'a barrow load, and the time goes on the job.</p>' % total)
    return "".join(out)


def view_money(conn, sess, q):
    v = money.variance(conn)
    r = money.monthly_rate(conn)
    out = ['<p class=stat>Setup £%.2f of £%.0f-%.0f%s</p>'
           % (v["setup_spent"], v["setup_budget"][0], v["setup_budget"][1],
              " &middot; OVER by £%.2f" % v["over"] if v["over"] else "")]
    if r:
        out.append('<p class=stat>Running £%.2f/month over %d months (target £%.0f-%.0f)</p>'
                   % (r["per_month"], r["months"], r["target"][0], r["target"][1]))
    out.append('<p class=stat>Depreciation sinking fund £%.2f/month</p>'
               % money.sinking_fund(conn))

    out.append("<h2>By budget line</h2><table><tr><th>Line</th><th class=num>Spend</th>"
               "<th class=num>Items</th></tr>")
    for line in money.by_line(conn):
        out.append("<tr><td>%s</td><td class=num>£%.2f</td><td class=num>%d</td></tr>"
                   % (e(line["budget_line"]), line["t"], line["n"]))
    out.append("</table>")

    out.append('<h2>Add spend</h2><form method=post action="/spend">'
               '<input type=hidden name=csrf value="%s">'
               '<div class=row><div><label>Amount</label><input name=amount type=number '
               'step=0.01 required></div><div><label>Vendor</label><input name=vendor></div>'
               '<div><label>Budget line</label><select name=budget_line>%s</select></div></div>'
               '<label>Notes</label><input name=notes><p></p><button class=go>Record</button>'
               '</form>'
               % (e(sess["csrf"]),
                  "".join("<option>%s</option>" % b for b in config.BUDGET_LINES)))

    reg = money.register(conn)
    if reg:
        out.append("<h2>Asset register</h2><table><tr><th>Item</th><th class=num>Price</th>"
                   "<th class=num>Life</th><th class=num>Dep/yr</th><th class=num>Book</th></tr>")
        for a in reg:
            out.append("<tr><td>%s</td><td class=num>£%.2f</td><td class=num>%g yr</td>"
                       "<td class=num>£%.2f</td><td class=num>£%.2f</td></tr>"
                       % (e(a["item"]), a["price"], a["life"], a["annual_dep"], a["book"]))
        out.append("</table>")
    for w in money.end_of_life(conn):
        out.append('<div class=risk><b>Asset</b>%s</div>' % e(w))
    return "".join(out)


def view_time(conn, sess, q):
    c = ledger.calibration(conn)
    oh = ledger.overhead_ratio(conn)
    out = ['<p class=stat>Calibration factor: %s</p>' % (c if c else "not enough data yet")]
    if c:
        out.append("<p>%s If it stays here, every hour figure in the smallholding plan "
                   "moves by the same factor.</p>"
                   % ("Estimates were optimistic - the real thing takes longer." if c > 1.1
                      else "Estimates were pessimistic." if c < 0.9
                      else "Estimates are honest."))
    if oh:
        out.append('<p class=stat>Overhead %s per visit across %d visits (%d%% of all time)</p>'
                   % (hm(oh["per_visit"]), oh["visits"], round(oh["ratio"] * 100)))
    out.append("<h2>Hours by month</h2><table><tr><th>Month</th><th class=num>Planned</th>"
               "<th class=num>Actual</th><th class=num>Variance</th></tr>")
    for m, row in ledger.hours_by_month(conn).items():
        if row["planned"] or row["actual"]:
            out.append("<tr><td>%s</td><td class=num>%s</td><td class=num>%s</td>"
                       "<td class=num>%s</td></tr>"
                       % (date(2000, m, 1).strftime("%B"), row["planned"], row["actual"],
                          row["variance"]))
    out.append("</table>")
    by_cat = ledger.calibration_by_category(conn)
    if by_cat:
        out.append("<h2>By job type</h2><table><tr><th>Category</th>"
                   "<th class=num>Factor</th></tr>")
        for cat, f in sorted(by_cat.items(), key=lambda kv: -kv[1]):
            out.append("<tr><td>%s</td><td class=num>%.2f</td></tr>" % (e(cat), f))
        out.append("</table>")
    mpm = ledger.minutes_per_m2(conn)
    if mpm:
        out.append("<h2>Minutes per m²</h2><table><tr><th>Zone</th><th class=num>Minutes</th>"
                   "<th class=num>Per m²</th></tr>")
        for z in mpm:
            out.append("<tr><td>%s</td><td class=num>%d</td><td class=num>%s</td></tr>"
                       % (e(z["name"]), z["minutes"], z["per_m2"]))
        out.append("</table>")
    return "".join(out)


def view_report(conn, sess, q):
    r = money.report(conn)
    m, t, f = r["money"], r["time"], r["food"]
    out = ["<h2>Money</h2><table>"]
    for label, val in [("Setup spend", "£%.2f" % m["setup"]),
                       ("Running costs", "£%.2f" % m["running"]),
                       ("Depreciation", "£%.2f" % m["depreciation"]),
                       ("True cost of the year", "£%.2f" % m["true_cost"]),
                       ("Asset book value", "£%.2f" % m["book_value"]),
                       ("Sinking fund", "£%.2f / month" % m["sinking_fund_monthly"])]:
        out.append("<tr><td>%s</td><td class=num>%s</td></tr>" % (label, val))
    out.append("</table><h2>Time</h2><table>")
    for label, val in [("Hours logged", t["hours"]), ("Planned", t["planned"]),
                       ("Calibration factor", t["calibration"] or "-"),
                       ("Overhead per visit", "%s min" % t["overhead"]["per_visit"]
                        if t["overhead"] else "-"),
                       ("Winter attendance", "%s%%" % t["winter_attendance"]
                        if t["winter_attendance"] is not None else "-")]:
        out.append("<tr><td>%s</td><td class=num>%s</td></tr>" % (label, e(val)))
    out.append("</table><h2>Food</h2><table>")
    out.append("<tr><td>Harvested</td><td class=num>%.1f kg</td></tr>" % f["kg"])
    out.append("<tr><td>Retail value</td><td class=num>£%.2f</td></tr>" % f["value"])
    if f["cost_per_kg"]:
        out.append("<tr><td>Cost per kg</td><td class=num>£%.2f</td></tr>" % f["cost_per_kg"])
        out.append("<tr><td>Cost per kg excl setup</td><td class=num>£%.2f</td></tr>"
                   % f["cost_per_kg_excl_setup"])
    out.append("</table>")
    if r["failures"]:
        out.append("<h2>Failures</h2><table>")
        for fl in r["failures"]:
            out.append("<tr><td>%s</td><td class=num>%d plantings</td></tr>"
                       % (e(fl["r"]), fl["c"]))
        out.append("</table>")
    mood = {k: v for k, v in r["mood"].items() if k != "_n"}
    if mood:
        out.append("<h2>Mood</h2><p>%s</p>"
                   % "  ".join("%s %d%%" % (e(k.title()), v) for k, v in mood.items()))
    out.append("<p>The three lines that actually matter: calibration factor, winter "
               "attendance, and the mood split. Everything else is bookkeeping.</p>")
    rot = rotation.propose(conn)
    out.append("<h2>Rotation proposal, year %d</h2><table>" % rot["year"])
    for a in rot["assignments"]:
        out.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                   % (e(a["zone"]), e(a["name"]),
                      e("; ".join(a["problems"]) if a["problems"] else "")))
    out.append("</table>")
    for msg in sun.check_all_placements(conn):
        out.append('<div class=risk><b>Neighbour shading</b>%s</div>' % e(msg))
    return "".join(out)


def view_map(conn, sess, q):
    with open(os.path.join(STATIC, "map.html"), encoding="utf-8") as fh:
        doc = fh.read()
    zones = [dict(r) for r in conn.execute(
        "SELECT id,name,x,y,w,d,height_m,colour,notes,growable FROM zones").fetchall()]
    pins = [dict(r) for r in conn.execute("SELECT * FROM trouble_pins").fetchall()]
    plantings = [dict(r) for r in conn.execute(
        "SELECT p.zone_id, c.name crop, p.variety, p.status, p.sown_date, p.planted_date, "
        "p.expected_first_harvest FROM plantings p LEFT JOIN crops c ON c.id=p.crop_id "
        "WHERE p.status NOT IN ('finished','failed')").fetchall()]
    rot = {y: rotation.plan_for(conn, y) for y in (1, 2, 3, 4)}
    payload = {"zones": zones, "pins": pins, "plantings": plantings, "rotation": rot,
               "groups": {k: v for k, v in
                          __import__("allotment.seeddata", fromlist=["x"]).GROUP_NAMES.items()},
               "weeds": weeds.current(conn, zones), "lat": config.LAT,
               "nav": NAV}
    return doc.replace("/*__PLOT_DATA__*/null",
                       json.dumps(payload).replace("</", "<\\/"))


VIEWS = {"/": view_today, "/week": view_week, "/stock": view_stock, "/shop": view_shop,
         "/money": view_money, "/time": view_time, "/report": view_report}


# ------------------------------------------------------------------- handler

class Handler(BaseHTTPRequestHandler):
    server_version = "allotment"

    def log_message(self, fmt, *args):
        pass

    # -- plumbing ---------------------------------------------------------
    def _conn(self):
        conn = db.connect(DB_PATH)
        db.init(conn)
        return conn

    def _cookie(self):
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == "plot_session":
                return v
        return None

    def _send(self, body, status=200, ctype="text/html; charset=utf-8", headers=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (headers or []):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, to, headers=None):
        self.send_response(303)
        self.send_header("Location", to)
        for k, v in (headers or []):
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _form(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode("utf-8") if n else ""
        return {k: v[0] for k, v in urllib.parse.parse_qs(body).items()}

    # -- GET --------------------------------------------------------------
    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        path, q = parts.path, urllib.parse.parse_qs(parts.query)
        # served without a session: a browser asks for these before you log in
        if path == "/favicon.ico":
            return self._send(FAVICON, ctype="image/svg+xml",
                              headers=[("Cache-Control", "max-age=86400")])
        if path == "/robots.txt":
            return self._send(ROBOTS, ctype="text/plain; charset=utf-8")
        if path in ("/index.html", "/index.htm"):
            return self._redirect("/")
        if path == "/healthz":
            return self._send("ok", ctype="text/plain; charset=utf-8")

        conn = self._conn()
        try:
            sess = auth.session(conn, self._cookie())
            if path == "/login":
                return self._send(login_page(q.get("e", [None])[0]))
            if sess is None:
                return self._redirect("/login")
            if path == "/logout":
                auth.end_session(conn, sess["token"])
                return self._redirect("/login", [("Set-Cookie",
                                                  "plot_session=; Max-Age=0; Path=/")])
            if path == "/map":
                return self._send(view_map(conn, sess, q))
            if path.startswith("/static/"):
                return self._static(path[len("/static/"):])
            fn = VIEWS.get(path)
            if fn is None:
                return self._send(page("Not here", not_found(path), sess, path), 404)
            title = dict(NAV).get(path, "Plot")
            return self._send(page(title, fn(conn, sess, q), sess, path))
        finally:
            conn.close()

    def _static(self, rel):
        """Files from allotment/static, and nothing outside it."""
        full = os.path.realpath(os.path.join(STATIC, rel))
        if not full.startswith(os.path.realpath(STATIC) + os.sep) or not os.path.isfile(full):
            return self._send(page("Not here", not_found("/static/" + rel)), 404)
        ctype = {".html": "text/html; charset=utf-8", ".css": "text/css",
                 ".js": "text/javascript", ".svg": "image/svg+xml",
                 ".png": "image/png", ".jpg": "image/jpeg"}.get(
                     os.path.splitext(full)[1], "application/octet-stream")
        with open(full, "rb") as fh:
            return self._send(fh.read(), ctype=ctype)

    # -- POST -------------------------------------------------------------
    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        conn = self._conn()
        try:
            form = self._form()
            if path == "/login":
                user = auth.verify(conn, form.get("email", ""), form.get("password", ""))
                if user is None:
                    left = auth.locked_out(conn, form.get("email", ""))
                    msg = ("Too many attempts. Try again in %d minutes." % left if left
                           else "Wrong email or password.")
                    return self._send(login_page(msg), 401)
                token, _ = auth.create_session(conn, user["id"])
                cookie = ("plot_session=%s; HttpOnly; SameSite=Lax; Path=/; Max-Age=%d"
                          % (token, config.SESSION_HOURS * 3600))
                return self._redirect("/", [("Set-Cookie", cookie)])

            sess = auth.session(conn, self._cookie())
            if sess is None:
                return self._redirect("/login")
            if not auth.check_csrf(sess, form.get("csrf")):
                return self._send(page("Rejected", "<p class=err>Bad CSRF token. Reload "
                                       "and try again.</p>", sess), 400)
            handler = POSTS.get(path)
            if handler is None:
                return self._send(page("Not here", "<p>No such action.</p>", sess), 404)
            return self._redirect(handler(conn, sess, form) or "/")
        finally:
            conn.close()


def not_found(path):
    return ('<p>There is no page at <code>%s</code>.</p>'
            '<p>%s</p>' % (e(path), " &middot; ".join(
                '<a href="%s" style="color:var(--sun)">%s</a>' % (p, n) for p, n in NAV)))


def login_page(msg=None):
    body = ('<div class=login>%s<form method=post action="/login">'
            '<label>Email</label><input name=email type=email autocomplete=username required>'
            '<label>Password</label><input name=password type=password '
            'autocomplete=current-password required>'
            '<p></p><button class=go style="width:100%%">Sign in</button></form></div>'
            % ('<p class=err>%s</p>' % e(msg) if msg else ""))
    return page("Sign in", body)


# ------------------------------------------------------------------- actions

def post_done(conn, sess, form):
    mins = form.get("minutes")
    ledger.complete(conn, int(form["run_id"]),
                    actual_minutes=int(mins) if mins else None,
                    method="entered" if mins else "allocated",
                    who=sess["role"], notes=form.get("notes"))
    return "/"


def post_log(conn, sess, form):
    if form.get("arrive"):
        ledger.arrive(conn, who=form.get("who", "Both"))
        return "/"
    ledger.log_visit(conn, int(form.get("minutes") or 0), who=form.get("who", "Both"),
                     mood=form.get("mood"), notes=form.get("notes"))
    return "/"


def post_leave(conn, sess, form):
    ledger.leave(conn, mood=form.get("mood"), notes=form.get("notes"))
    return "/"


def post_spend(conn, sess, form):
    money.add_spend(conn, float(form["amount"]), form["budget_line"],
                    vendor=form.get("vendor"), notes=form.get("notes"))
    return "/money"


def post_stockmove(conn, sess, form):
    try:
        delta = float(form.get("delta") or 0)
    except ValueError:
        return "/stock"
    if delta:
        stock.move(conn, int(form["id"]), delta, "bought" if delta > 0 else "used")
    return "/stock"


POSTS = {"/done": post_done, "/log": post_log, "/leave": post_leave,
         "/spend": post_spend, "/stockmove": post_stockmove}


def serve(host="127.0.0.1", port=8765, db_path=None):
    global DB_PATH
    DB_PATH = db_path or config.DB_PATH
    conn = db.connect(DB_PATH)
    db.init(conn)
    seed.seed(conn)
    if not conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]:
        auth.create_user(conn, config.DEFAULT_EMAIL, config.DEFAULT_PASSWORD)
        print("Created login for %s" % config.DEFAULT_EMAIL)
    auth.purge(conn)
    conn.close()
    httpd = ThreadingHTTPServer((host, port), Handler)
    shown = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    print("Plot running on http://%s:%d  (Ctrl-C to stop)" % (shown, port))
    if host not in ("127.0.0.1", "localhost", "::1"):
        print("Bound to %s - reachable from the network. Plain HTTP, so put TLS in "
              "front of it before it leaves your own machine." % host)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
