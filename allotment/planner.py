"""Weekly planner (§28). The daily view answers 'what today?'; this answers
'when this week?', which matters more when your time comes in weekend blocks.

Always shows why a job landed on a day, and what was deferred. A planner you
don't trust is a planner you override, and then it is just noise.
"""

from datetime import date, timedelta

from . import config, sun
from .priority import score, window_shuts, every_visit_jobs
from .rules import parse
from .weather import suitability


def day_budget(d):
    return config.DAY_BUDGET.get(d.weekday(), config.MIDWEEK_BUDGET)


def daylight_factor(wx, d):
    """Short January afternoons genuinely limit what fits into a visit."""
    h = sun.daylight_hours(d)
    return max(0.35, min(1.0, h / 10.0))


def plan_week(conn, start=None, wx=None, days=7, limit_per_day=6):
    start = parse(start or date.today())
    if wx is None:
        from .weather import Weather
        wx = Weather(conn, start)
    end = start + timedelta(days=days - 1)

    rows = conn.execute(
        "SELECT r.* FROM job_runs r WHERE r.status IN ('due','blocked') AND r.due_date <= ? "
        "ORDER BY r.due_date", (end.isoformat(),)).fetchall()

    candidates = []
    for r in rows:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (r["job_id"],)).fetchone()
        base = score(conn, r, job, wx, start)
        shuts = window_shuts(conn, r, job)
        fits = []
        for i in range(days):
            d = start + timedelta(days=i)
            if parse(r["due_date"]) > d:
                continue
            if shuts and d > shuts:
                continue
            blocked = _blocked_on(conn, job, wx, d)
            if blocked:
                fits.append((d, 0.0, blocked))
                continue
            urgency = max(0.5, base["urgency"] + (1.0 if shuts and (shuts - d).days <= 2 else 0))
            fit = suitability(job, wx, d) * urgency * daylight_factor(wx, d)
            fits.append((d, fit, None))
        candidates.append({"run": r, "job": job, "base": base, "fits": fits, "shuts": shuts})

    plan = {(start + timedelta(days=i)): [] for i in range(days)}
    used = {d: 0 for d in plan}
    deferred = []

    def best(c):
        ok = [f for f in c["fits"] if f[1] > 0]
        return max((f[1] for f in ok), default=0.0)

    for c in sorted(candidates, key=lambda c: -(best(c) + c["base"]["consequence"])):
        job, r = c["job"], c["run"]
        mins = r["est_minutes"] or job["est_minutes"]
        placed = False
        for d, fit, blocked in sorted([f for f in c["fits"] if f[1] > 0], key=lambda f: -f[1]):
            if used[d] + mins > day_budget(d):
                continue
            if len(plan[d]) >= limit_per_day:
                continue
            plan[d].append({"run_id": r["id"], "title": job["title"], "minutes": mins,
                            "owner": job["owner"], "why": _why_day(job, wx, d, c["shuts"]),
                            "fit": round(fit, 2)})
            used[d] += mins
            placed = True
            break
        if not placed:
            why = next((f[2] for f in c["fits"] if f[2]), None)
            if not why:
                why = ("No room in the week's budget" if best(c) > 0
                       else "Conditions wrong every day this week")
            deferred.append({"title": job["title"], "minutes": mins, "why": why,
                             "unblocks": _unblocks(job, c["base"])})

    return {
        "start": start, "end": end,
        "days": [{"date": d, "budget": day_budget(d), "used": used[d],
                  "items": plan[d], "weather": wx.summary(d)}
                 for d in sorted(plan)],
        "deferred": deferred,
        "every_visit": every_visit_jobs(conn, start),
    }


def _blocked_on(conn, job, wx, d):
    from .rules import blocked_reason
    return blocked_reason(conn, job, wx, d)


def _why_day(job, wx, d, shuts):
    cat, title = job["category"], (job["title"] or "").lower()
    bits = []
    if shuts:
        n = (shuts - d).days
        bits.append("window shuts in %d day%s" % (n, "" if n == 1 else "s") if n > 0
                    else "last day of the window")
    if cat in config.SOIL_CATEGORIES:
        bits.append("soil workable, %.0f mm in 48 h" % wx.rain_48h(d))
    elif cat == "sow" and wx.rain_due_24h(d):
        bits.append("rain forecast tomorrow - ideal")
    elif cat == "plant" and not wx.frost_risk(d):
        bits.append("no frost forecast")
    elif "water" in title and "tunnel" in title:
        bits.append("the tunnel never gets rain")
    elif "water" in title:
        bits.append("only %.0f mm rain in 3 days" % wx.rain_3d(d))
    elif "slug" in title:
        bits.append("rain yesterday, evening job")
    elif cat == "build":
        bits.append("wind %.0f kph" % wx.wind(d))
    return ". ".join(b[0].upper() + b[1:] for b in bits) if bits else "Due"


def _unblocks(job, base):
    b = base.get("blocked") or ""
    if b.startswith("Blocked until"):
        return None                      # the reason already names the job
    if "clay" in b or "rain" in b:
        return "two dry days"
    if "kph" in b:
        return "calmer weather"
    if "in stock" in b:
        return "buying the item"
    if "permission" in b:
        return "logging written permission"
    return None
