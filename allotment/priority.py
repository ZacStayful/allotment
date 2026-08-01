"""Priority scoring and the daily view (§5).

    priority = urgency + consequence + weather_fit - blocked_penalty

Short output on purpose. Twenty jobs is the same as no jobs.
"""

import json
from datetime import date, timedelta

from . import config, db, stock
from .rules import (blocked_reason, in_md_window, next_inspection, parse,
                    window_close)
from .rules import shuts as rules_shuts
from .weather import suitability

BLOCKED_PENALTY = 100.0


def window_shuts(conn, run, job):
    """When the chance to do this job goes away. One definition, shared with lapse()."""
    return rules_shuts(conn, run, job)


def score(conn, run, job, wx, today=None):
    today = parse(today or date.today())
    due = parse(run["due_date"])
    shuts = window_shuts(conn, run, job)

    # urgency: how fast the door is closing
    if shuts is not None:
        days_left = (shuts - today).days
        urgency = max(0.0, 10.0 - max(days_left, 0) / 3.0)
    else:
        urgency = 3.0
    overdue = (today - due).days
    if overdue > 0:
        urgency += min(overdue, 20) / 2.0

    consequence = (job["consequence"] or 2) * 1.5
    fit = suitability(job, wx, today)
    weather_fit = (fit - 1.0) * 4.0

    reason_blocked = blocked_reason(conn, job, wx, today)
    short = stock.shortfalls(conn, job)
    if short and not reason_blocked:
        reason_blocked = "No %s in stock (need %g, have %g)" % (
            short[0][0], short[0][1], short[0][2])

    penalty = BLOCKED_PENALTY if reason_blocked else 0.0
    total = urgency + consequence + weather_fit - penalty

    return {
        "run_id": run["id"], "job_id": job["id"], "title": job["title"],
        "owner": job["owner"], "category": job["category"], "zone": job["zone_id"],
        "minutes": run["est_minutes"] or job["est_minutes"],
        "due": due.isoformat(), "shuts": shuts.isoformat() if shuts else None,
        "days_left": (shuts - today).days if shuts else None,
        "overdue": max(overdue, 0),
        "urgency": round(urgency, 2), "consequence": round(consequence, 2),
        "weather_fit": round(weather_fit, 2), "blocked": reason_blocked,
        "priority": round(total, 2), "shortfalls": short,
        "why": _why(job, run, wx, today, shuts, overdue, reason_blocked),
    }


def _why(job, run, wx, today, shuts, overdue, blocked):
    if blocked:
        return blocked
    if job["rule_type"] == "weather_conditional":
        t = (job["title"] or "").lower()
        if "tunnel" in t and "water" in t:
            return "The tunnel never gets rain"
        if "slug" in t:
            return "Rain yesterday - they will be out tonight"
        if "frost" in t:
            return "Frost forecast within 48 hours"
        if "gale" in t or "anchoring" in t:
            return "Gusts over 45 kph forecast"
        if "water" in t:
            return "Only %.0f mm rain in the last 3 days" % wx.rain_3d(today)
        if "ventilate" in t:
            return "Forecast max over 20°C"
        if "butt" in t:
            return "Butts below half and the tap is still on"
    if overdue > 0:
        return "Overdue by %d day%s" % (overdue, "" if overdue == 1 else "s")
    if shuts is not None:
        n = (shuts - today).days
        if n <= 0:
            return "Last day of the window"
        return "Window closes in %d day%s" % (n, "" if n == 1 else "s")
    if job["notes"]:
        return job["notes"]
    return "Due today"


def every_visit_jobs(conn, today=None):
    today = parse(today or date.today())
    out = []
    for job in conn.execute(
            "SELECT * FROM jobs WHERE every_visit=1 AND active=1 ORDER BY id").fetchall():
        p = json.loads(job["rule_params"] or "{}")
        if not in_md_window(today, p.get("from_md"), p.get("to_md")):
            continue
        if blocked_reason(conn, job, None, today):
            continue                      # no point opening a tunnel that isn't built
        out.append({"title": job["title"], "owner": job["owner"],
                    "minutes": job["est_minutes"], "job_id": job["id"]})
    return out


def plan_day(conn, today=None, wx=None, limit=5):
    """The daily view. Top 3-5, total minutes, one line each on why."""
    today = parse(today or date.today())
    if wx is None:
        from .weather import Weather
        wx = Weather(conn, today)

    rows = conn.execute(
        "SELECT r.*, j.id AS jid FROM job_runs r JOIN jobs j ON j.id=r.job_id "
        "WHERE r.status IN ('due','blocked') AND r.due_date <= ? ORDER BY r.due_date",
        (today.isoformat(),)).fetchall()

    scored = []
    for r in rows:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (r["job_id"],)).fetchone()
        scored.append(score(conn, r, job, wx, today))

    scored.sort(key=lambda s: -s["priority"])
    live = [s for s in scored if not s["blocked"]]
    blocked = [s for s in scored if s["blocked"]]

    top = live[:limit]
    also = live[limit:]
    visit = every_visit_jobs(conn, today)

    minutes = sum(s["minutes"] for s in top) + sum(v["minutes"] for v in visit)
    return {
        "date": today,
        "weather": wx.summary(today),
        "soil_workable": wx.soil_workable(today),
        "top": top, "also": also, "blocked": blocked, "every_visit": visit,
        "minutes": minutes,
        "inspection": next_inspection(today),
        "risks": risks(conn, wx, today),
        "hours": month_hours(conn, today),
    }


def month_hours(conn, today=None):
    today = parse(today or date.today())
    row = conn.execute(
        "SELECT COALESCE(SUM(minutes_total),0) m FROM visits WHERE date LIKE ?",
        ("%s-%02d%%" % (today.year, today.month),)).fetchone()
    return {"planned_h": config.PLAN_HOURS.get(today.month, 0),
            "logged_h": round((row["m"] or 0) / 60.0, 1)}


# ------------------------------------------------------------------- §18 risks

def risks(conn, wx, today=None):
    today = parse(today or date.today())
    out = []

    last = conn.execute("SELECT MAX(date) d FROM visits").fetchone()["d"]
    if 3 <= today.month <= 9:
        gap = (today - parse(last)).days if last else None
        if gap is None:
            out.append(("Cultivation risk", "No visit has ever been logged - the plot is "
                        "inspected every four weeks"))
        elif gap >= 21:
            out.append(("Cultivation risk", "No visit logged in %d days - the plot is "
                        "inspected every four weeks" % gap))

    if wx.known_48h(today) and not wx.soil_workable(today):
        out.append(("Soil blocked", "%.0f mm rain in 48 h - clay. All soil jobs held"
                    % wx.rain_48h(today)))
    if wx.gale_risk(today):
        out.append(("Wind", "Gusts %.0f kph - check tunnel anchoring today" % wx.wind(today)))
    if 4 <= today.month <= 6 and wx.slug_night(today):
        out.append(("Slugs", "Rain yesterday - patrol the shaded SE corner tonight"))
    if wx.frost_risk(today) and 3 <= today.month <= 5:
        out.append(("Frost", "Under 2°C forecast - fleece anything tender"))

    split = person_split(conn, today)
    if split and split["max_pct"] > 70 and split["months"] >= 6:
        out.append(("Shared project", "%s has done %d%% of the hours"
                    % (split["max_who"], split["max_pct"])))

    mood = mood_split(conn)
    hard = mood.get("hard going", 0) + mood.get("a chore", 0)
    if mood.get("_n", 0) >= 10 and hard > 50:
        out.append(("Mood", "%d%% of visits logged as hard going or a chore - review "
                    "before committing to livestock" % hard))

    if today.month in (11, 12, 1, 2):
        wa = winter_attendance(conn, today)
        if wa is not None and wa < 60:
            out.append(("Winter attendance", "%d%% of planned winter visits - the honest "
                        "signal" % wa))

    for n in stock.upcoming_needs(conn, today, 14):
        if n["have"] <= 0:
            out.append(("Stock", "No %s and %s is due %s" % (n["item"], n["job"], n["due"])))

    return out


def person_split(conn, today=None):
    today = parse(today or date.today())
    rows = conn.execute("SELECT who, minutes_total, date FROM visits").fetchall()
    if not rows:
        return None
    tally, first = {}, None
    for r in rows:
        who = [w.strip() for w in (r["who"] or "").split(",") if w.strip()] or ["Both"]
        if "Both" in who:
            who = [db.get_setting(conn, "person_a", "Grower"),
                   db.get_setting(conn, "person_b", "Site")]
        share = (r["minutes_total"] or 0) / len(who)
        for w in who:
            tally[w] = tally.get(w, 0) + share
        d = parse(r["date"])
        first = d if first is None or d < first else first
    total = sum(tally.values()) or 1
    who, mins = max(tally.items(), key=lambda kv: kv[1])
    months = (today.year - first.year) * 12 + today.month - first.month
    return {"tally": tally, "max_who": who, "max_pct": round(100 * mins / total),
            "months": months}


def mood_split(conn):
    rows = conn.execute("SELECT LOWER(mood) m, COUNT(*) c FROM visits "
                        "WHERE mood IS NOT NULL AND mood<>'' GROUP BY 1").fetchall()
    n = sum(r["c"] for r in rows)
    out = {r["m"]: round(100 * r["c"] / n) for r in rows} if n else {}
    out["_n"] = n
    return out


def winter_attendance(conn, today=None):
    """Planned winter visits assume roughly one visit per 90 planned minutes."""
    today = parse(today or date.today())
    year = today.year if today.month <= 2 else today.year + 1
    months = [(year - 1, 11), (year - 1, 12), (year, 1), (year, 2)]
    planned = actual = 0
    for y, m in months:
        if date(y, m, 1) > today:
            continue
        planned += max(1, round(config.PLAN_HOURS.get(m, 0) * 60 / 90.0))
        actual += conn.execute("SELECT COUNT(*) c FROM visits WHERE date LIKE ?",
                               ("%d-%02d%%" % (y, m),)).fetchone()["c"]
    if not planned:
        return None
    return round(100 * actual / planned)
