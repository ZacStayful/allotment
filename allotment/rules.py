"""The rule engine. Every job resolves to a due date through one of seven rule
types (§2 plus the succession rule added in §12)."""

import json
from datetime import date, timedelta

from . import config

RULE_TYPES = ("fixed_window", "recurring", "weather_conditional", "crop_linked",
              "dependency", "inspection_linked", "succession", "every_visit")


# ---------------------------------------------------------------- date helpers

def parse(d):
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d)[:10])


def md(year, s):
    """'MM-DD' in a given year."""
    m, dd = int(s[:2]), int(s[3:5])
    if m == 2 and dd == 29:
        dd = 28
    return date(year, m, dd)


def in_md_window(d, from_md, to_md):
    """True if d falls in a MM-DD window, handling windows that wrap the year."""
    if not from_md and not to_md:
        return True
    from_md = from_md or "01-01"
    to_md = to_md or "12-31"
    key = (d.month, d.day)
    a = (int(from_md[:2]), int(from_md[3:5]))
    b = (int(to_md[:2]), int(to_md[3:5]))
    if a <= b:
        return a <= key <= b
    return key >= a or key <= b          # wraps December into February


def window_close(d, from_md, to_md):
    """The date the current MM-DD window shuts, for a date inside it."""
    if not to_md:
        return None
    end = md(d.year, to_md)
    if end < d:
        end = md(d.year + 1, to_md)
    return end


def daterange(a, b):
    cur = a
    while cur <= b:
        yield cur
        cur += timedelta(days=1)


# ------------------------------------------------------------- inspections §14

def inspection_dates(year):
    """Every 28 days from calendar week 4."""
    jan4 = date(year, 1, 4)                       # ISO week 1 always contains 4 Jan
    week1_mon = jan4 - timedelta(days=jan4.weekday())
    first = week1_mon + timedelta(weeks=config.INSPECTION_START_WEEK - 1)
    out, cur = [], first
    while cur.year <= year:
        if cur.year == year:
            out.append(cur)
        cur += timedelta(days=config.INSPECTION_INTERVAL_DAYS)
    return out


def next_inspection(today):
    today = parse(today)
    for d in inspection_dates(today.year) + inspection_dates(today.year + 1):
        if d >= today:
            return d
    return None


# ------------------------------------------------------------------ rule logic

def _params(job):
    p = job["rule_params"] if not isinstance(job, dict) else job.get("rule_params", "{}")
    if isinstance(p, str):
        try:
            return json.loads(p or "{}")
        except ValueError:
            return {}
    return p or {}


def _last_done(conn, job_id):
    row = conn.execute(
        "SELECT MAX(done_date) AS d FROM job_runs WHERE job_id=? AND status='done'",
        (job_id,)).fetchone()
    return parse(row["d"]) if row and row["d"] else None


def _latest_run(conn, job_id):
    return conn.execute(
        "SELECT * FROM job_runs WHERE job_id=? ORDER BY due_date DESC, id DESC LIMIT 1",
        (job_id,)).fetchone()


def _crop(conn, crop_id):
    return conn.execute("SELECT * FROM crops WHERE id=?", (crop_id,)).fetchone()


ANCHOR_COL = {"sow": "sow_from", "sow_indoor": "sow_indoor_from",
              "plant": "plant_from", "harvest": "harvest_from"}


def due_dates(conn, job, start, end, wx=None):
    """All due dates for a job inside [start, end]. Returns [(date, seq)]."""
    rt = job["rule_type"]
    p = _params(job)
    start, end = parse(start), parse(end)
    fn = globals().get("_due_" + rt)
    if fn is None:
        return []
    return fn(conn, job, p, start, end, wx)


def _due_every_visit(conn, job, p, start, end, wx):
    return []                                    # shown every visit, never scheduled


def _due_fixed_window(conn, job, p, start, end, wx):
    out = []
    freq = p.get("frequency", "once")
    one_off = job["one_off"] and _latest_run(conn, job["id"]) is None
    for year in range(start.year - 1, end.year + 2):
        try:
            a = md(year, p["start_md"])
        except (KeyError, ValueError):
            continue
        b = md(year, p.get("end_md", p["start_md"]))
        if b < a:                                # window wraps the new year
            b = md(year + 1, p.get("end_md"))
        if freq == "weekly":
            cur, seq = a, 0
            while cur <= b:
                if start <= cur <= end:
                    out.append((cur, seq))
                cur += timedelta(days=7)
                seq += 1
        elif start <= a <= end:
            out.append((a, 0))
        elif one_off and a < start <= b:
            # Take the plot on halfway through the window and the one thing that
            # had to happen this year is silently skipped until the window comes
            # round again. A one-off is due for as long as its window is open.
            out.append((start, 0))
    return out


def _due_recurring(conn, job, p, start, end, wx):
    """One open run at a time. Missing five compost turns should not produce five rows."""
    interval = int(p.get("interval_days", 30))
    latest = _latest_run(conn, job["id"])
    if latest is not None and latest["status"] not in ("done", "skipped", "missed"):
        return []                                # already an open run
    if latest is not None:
        anchor = parse(latest["done_date"] or latest["due_date"])
        nxt = anchor + timedelta(days=interval)
    elif p.get("after_job"):
        # e.g. replace the polythene five years after it was fitted, not on day one
        row = _dep_row(conn, p["after_job"])
        if row is None or not row["done"]:
            return []
        nxt = parse(row["done_date"]) + timedelta(days=interval)
    else:
        nxt = start
    while not in_md_window(nxt, p.get("from_md"), p.get("to_md")):
        nxt += timedelta(days=1)
        if nxt > end + timedelta(days=400):
            return []
    if nxt < start:
        nxt = start                              # overdue: due now, not repeatedly
        while not in_md_window(nxt, p.get("from_md"), p.get("to_md")):
            nxt += timedelta(days=1)
    return [(nxt, 0)] if nxt <= end else []


def _due_succession(conn, job, p, start, end, wx):
    interval = int(p.get("interval_days", 14))
    maxn = int(p.get("max_sowings", 99))
    out = []
    for year in range(start.year - 1, end.year + 1):
        try:
            a = md(year, p["window_start"])
            b = md(year, p["window_end"])
        except (KeyError, ValueError):
            continue
        cur, seq = a, 0
        while cur <= b and seq < maxn:
            if start <= cur <= end:
                out.append((cur, seq))
            cur += timedelta(days=interval)
            seq += 1
    return out


def _due_crop_linked(conn, job, p, start, end, wx):
    crop = _crop(conn, p.get("crop_id") or job["crop_id"])
    if crop is None:
        return []
    col = ANCHOR_COL.get(p.get("anchor", "plant"), "plant_from")
    anchor_md = crop[col]
    if not anchor_md:
        return []
    offset = int(p.get("offset_days", 0))
    reps = int(p.get("repeat_count", 1))
    rep_days = int(p.get("repeat_days", 0))
    out = []
    for year in range(start.year - 1, end.year + 2):
        try:
            base = md(year, anchor_md) + timedelta(days=offset)
        except ValueError:
            continue
        for i in range(max(1, reps)):
            d = base + timedelta(days=i * rep_days)
            if start <= d <= end:
                out.append((d, i))
    return out


def _due_inspection_linked(conn, job, p, start, end, wx):
    before = int(p.get("days_before", 3))
    out = []
    for year in range(start.year, end.year + 1):
        for insp in inspection_dates(year):
            d = insp - timedelta(days=before)
            if start <= d <= end:
                out.append((d, 0))
    return out


def _due_dependency(conn, job, p, start, end, wx):
    """Due as soon as its prerequisites are done; shown blocked until then."""
    latest = _latest_run(conn, job["id"])
    if latest is not None and latest["status"] in ("done", "skipped"):
        return []
    if latest is not None:
        return []
    return [(start, 0)]


def _due_weather_conditional(conn, job, p, start, end, wx):
    if wx is None:
        return []
    cond = p.get("condition", "always")
    out = []
    for d in daterange(max(start, wx.horizon_start), min(end, wx.horizon_end)):
        if not in_md_window(d, p.get("from_md"), p.get("to_md")):
            continue
        if wx.condition(cond, d):
            out.append((d, 0))
    return out


# ------------------------------------------------------------- materialisation

def ensure_runs(conn, start, end, wx=None):
    """Create job_run rows for everything due in [start, end]. Idempotent."""
    start, end = parse(start), parse(end)
    made = 0
    for job in conn.execute("SELECT * FROM jobs WHERE active=1").fetchall():
        for d, seq in due_dates(conn, job, start, end, wx):
            if job["active_from"] and parse(job["active_from"]) > d:
                continue
            if job["active_to"] and parse(job["active_to"]) < d:
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO job_runs(job_id,due_date,status,est_minutes,seq,zone_id) "
                "VALUES(?,?,'due',?,?,?)",
                (job["id"], d.isoformat(), job["est_minutes"], seq, job["zone_id"]))
            made += cur.rowcount
    conn.commit()
    return made


def shuts(conn, run, job):
    """When the chance to do this job goes away. None means it just waits."""
    p = _params(job)
    due = parse(run["due_date"])
    rt = job["rule_type"]
    if rt == "fixed_window" and p.get("end_md"):
        return window_close(due, p.get("start_md"), p["end_md"])
    if rt == "succession":
        return due + timedelta(days=int(p.get("interval_days", 14)))
    if rt == "weather_conditional":
        return due
    if rt == "inspection_linked":
        return due + timedelta(days=int(p.get("days_before", 3)))
    if rt == "crop_linked":
        crop = _crop(conn, p.get("crop_id") or job["crop_id"])
        if crop is not None:
            col = {"sow": "sow_to", "sow_indoor": "sow_indoor_to",
                   "plant": "plant_to", "harvest": "harvest_to"}.get(
                       p.get("anchor", "plant"), "plant_to")
            if crop[col]:
                return window_close(due, None, crop[col])
    return None


def lapse(conn, today):
    """Mark runs whose window has shut as missed, so they stop cluttering the view."""
    today = parse(today)
    n = 0
    rows = conn.execute(
        "SELECT r.*, j.rule_type, j.rule_params, j.crop_id FROM job_runs r "
        "JOIN jobs j ON j.id=r.job_id WHERE r.status='due' AND r.due_date < ?",
        (today.isoformat(),)).fetchall()
    for r in rows:
        shut = shuts(conn, r, r)
        if r["rule_type"] == "weather_conditional" and shut:
            shut = shut + timedelta(days=1)
        if shut and today > shut:
            conn.execute("UPDATE job_runs SET status='missed' WHERE id=?", (r["id"],))
            n += 1
    conn.commit()
    return n


# ------------------------------------------------------------------- blocking §2

def blocked_reason(conn, job, wx=None, today=None):
    """Why this job cannot be done today, or None. The clay rule is a hard block."""
    today = parse(today or date.today())
    p = _params(job)

    if job["needs_permission"]:
        from . import db as _db
        if not _db.get_setting(conn, "structures_permission", False):
            return "Written permission for structures has not been logged"

    deps = p.get("depends_on") or json.loads(job["depends_on"] or "[]")
    for dep in deps:
        row = _dep_row(conn, dep)
        if row is None:
            continue
        if not row["done"]:
            return "Blocked until %s is done" % row["title"]

    if wx is not None:
        if job["category"] in config.SOIL_CATEGORIES and not wx.soil_workable(today):
            return ("Soil jobs blocked - %.0f mm rain in 48 h, clay too wet"
                    % wx.rain_48h(today))
        if "polythene" in (job["title"] or "").lower():
            g = wx.wind(today)
            if g > config.POLYTHENE_MAX_WIND_KPH:
                return "Polythene needs under 10 kph. Forecast %.0f kph" % g
        elif job["category"] == "build" and wx.wind(today) > config.STRUCTURE_MAX_WIND_KPH:
            return "Structure work wants under 20 kph. Forecast %.0f kph" % wx.wind(today)
    return None


def _dep_row(conn, dep):
    """Dependencies are stored as job keys (stable across reseeds) or as ids."""
    if isinstance(dep, int) or (isinstance(dep, str) and str(dep).isdigit()):
        row = conn.execute("SELECT id, title FROM jobs WHERE id=?", (int(dep),)).fetchone()
    else:
        row = conn.execute("SELECT id, title FROM jobs WHERE job_key=? OR title=?",
                           (str(dep), str(dep))).fetchone()
    if row is None:
        return None
    d = conn.execute("SELECT COUNT(*) c, MAX(done_date) dd FROM job_runs "
                     "WHERE job_id=? AND status='done'", (row["id"],)).fetchone()
    return {"title": row["title"], "done": d["c"], "done_date": d["dd"]}
