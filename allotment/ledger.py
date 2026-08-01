"""Visit and time ledger (§30).

The calibration factor is the headline number of the whole system: if it is 1.6,
every hour figure in the smallholding plan is 60% light. Overheads are separated
out, because burying the walk and the tool faff inside job times inflates every
estimate and makes the calibration factor lie.
"""

from datetime import date, datetime

from . import config, stock
from .rules import parse

METHOD_WEIGHT = {"timed": 1.0, "entered": 0.7, "allocated": 0.35}
MOODS = ["loved it", "fine", "hard going", "a chore"]


# ------------------------------------------------------------------- visits

def arrive(conn, when=None, who="Both", at=None):
    when = parse(when or date.today())
    at = at or datetime.now().strftime("%H:%M")
    open_visit = current_visit(conn)
    if open_visit:
        return open_visit["id"]
    cur = conn.execute("INSERT INTO visits(date,arrive_time,who) VALUES(?,?,?)",
                       (when.isoformat(), at, who))
    conn.commit()
    return cur.lastrowid


def current_visit(conn):
    return conn.execute(
        "SELECT * FROM visits WHERE leave_time IS NULL AND arrive_time IS NOT NULL "
        "ORDER BY id DESC LIMIT 1").fetchone()


def leave(conn, mood=None, notes=None, at=None, walk_minutes=12):
    v = current_visit(conn)
    if v is None:
        return None
    at = at or datetime.now().strftime("%H:%M")
    mins = _minutes_between(v["arrive_time"], at)
    conn.execute("UPDATE visits SET leave_time=?, minutes_total=?, mood=?, notes=? WHERE id=?",
                 (at, mins, mood, notes, v["id"]))
    conn.execute("INSERT INTO overheads(visit_id,walk_minutes) VALUES(?,?) "
                 "ON CONFLICT(visit_id) DO UPDATE SET walk_minutes=excluded.walk_minutes",
                 (v["id"], walk_minutes))
    conn.commit()
    return dict(id=v["id"], minutes=mins, overhead=overhead(conn, v["id"]))


def _minutes_between(a, b):
    fmt = "%H:%M"
    try:
        t0 = datetime.strptime(a[:5], fmt)
        t1 = datetime.strptime(b[:5], fmt)
    except (ValueError, TypeError):
        return 0
    delta = (t1 - t0).total_seconds() / 60.0
    if delta < 0:
        delta += 24 * 60
    return int(round(delta))


def log_visit(conn, minutes, who="Both", mood=None, notes=None, when=None,
              run_ids=None, walk_minutes=12):
    """Retrospective log. Unassigned time is split across the jobs in proportion
    to their estimates and marked `allocated`."""
    when = parse(when or date.today())
    cur = conn.execute(
        "INSERT INTO visits(date,minutes_total,who,mood,notes) VALUES(?,?,?,?,?)",
        (when.isoformat(), int(minutes), who, mood, notes))
    vid = cur.lastrowid
    conn.execute("INSERT INTO overheads(visit_id,walk_minutes) VALUES(?,?)",
                 (vid, walk_minutes))
    if run_ids:
        allocate(conn, vid, run_ids, int(minutes) - walk_minutes, who)
    else:
        # jobs already marked done today but not tied to a visit belong to this one
        conn.execute("UPDATE job_runs SET visit_id=? WHERE done_date=? AND visit_id IS NULL "
                     "AND status='done'", (vid, when.isoformat()))
    conn.commit()
    return vid


def allocate(conn, visit_id, run_ids, minutes, who="Both"):
    runs = [conn.execute("SELECT * FROM job_runs WHERE id=?", (r,)).fetchone()
            for r in run_ids]
    runs = [r for r in runs if r is not None]
    if not runs:
        return []
    total_est = sum(r["est_minutes"] or 30 for r in runs) or 1
    out = []
    for r in runs:
        share = int(round(minutes * (r["est_minutes"] or 30) / total_est))
        complete(conn, r["id"], actual_minutes=share, method="allocated",
                 visit_id=visit_id, who=who)
        out.append((r["id"], share))
    return out


def overhead(conn, visit_id):
    """§30 - minutes_total less the sum of job time. On a five minute walk this
    should settle around 12 minutes."""
    v = conn.execute("SELECT minutes_total FROM visits WHERE id=?", (visit_id,)).fetchone()
    if v is None or not v["minutes_total"]:
        return 0
    jobs = conn.execute("SELECT COALESCE(SUM(actual_minutes),0) m FROM job_runs "
                        "WHERE visit_id=?", (visit_id,)).fetchone()["m"]
    return max(0, v["minutes_total"] - (jobs or 0))


# --------------------------------------------------------------------- jobs

def start_job(conn, run_id, when=None):
    conn.execute("UPDATE job_runs SET started_at=?, status='doing' WHERE id=?",
                 (when or datetime.now().strftime("%H:%M"), run_id))
    conn.commit()


def stop_job(conn, run_id, notes=None, when=None, who=None):
    r = conn.execute("SELECT * FROM job_runs WHERE id=?", (run_id,)).fetchone()
    if r is None:
        return None
    at = when or datetime.now().strftime("%H:%M")
    mins = _minutes_between(r["started_at"], at) if r["started_at"] else None
    return complete(conn, run_id, actual_minutes=mins,
                    method="timed" if mins else "entered", notes=notes, who=who)


def complete(conn, run_id, actual_minutes=None, method="entered", notes=None,
             visit_id=None, who=None, when=None):
    r = conn.execute("SELECT * FROM job_runs WHERE id=?", (run_id,)).fetchone()
    if r is None:
        return None
    if visit_id is None:
        v = current_visit(conn)
        visit_id = v["id"] if v else None
    conn.execute(
        "UPDATE job_runs SET status='done', done_date=?, actual_minutes=?, timing_method=?, "
        "notes=COALESCE(?,notes), visit_id=COALESCE(?,visit_id), done_by=COALESCE(?,done_by) "
        "WHERE id=?",
        (parse(when or date.today()).isoformat(), actual_minutes, method, notes,
         visit_id, who, run_id))
    conn.commit()
    job = conn.execute("SELECT * FROM jobs WHERE id=?", (r["job_id"],)).fetchone()
    stock.consume_for_run(conn, job, visit_id=visit_id)
    recalibrate(conn, r["job_id"])
    return {"run_id": run_id, "job": job["title"], "minutes": actual_minutes}


def skip(conn, run_id, notes=None):
    conn.execute("UPDATE job_runs SET status='skipped', notes=? WHERE id=?", (notes, run_id))
    conn.commit()


# -------------------------------------------------------------- calibration

def recalibrate(conn, job_id, alpha=0.3, after=3):
    """§30 - after three runs the estimate becomes an EMA of what it really took.
    The original planned figure is kept, because the gap is the point."""
    rows = conn.execute(
        "SELECT actual_minutes FROM job_runs WHERE job_id=? AND status='done' "
        "AND actual_minutes IS NOT NULL ORDER BY done_date", (job_id,)).fetchall()
    if len(rows) < after:
        return None
    job = conn.execute("SELECT est_minutes FROM jobs WHERE id=?", (job_id,)).fetchone()
    est = job["est_minutes"]
    new = round((1 - alpha) * est + alpha * rows[-1]["actual_minutes"])
    conn.execute("UPDATE jobs SET est_minutes=? WHERE id=?", (new, job_id))
    conn.commit()
    return new


def calibration(conn, job_id=None, since=None):
    """Actual / estimated, weighted so timed data outranks allocated."""
    q = ("SELECT r.actual_minutes a, COALESCE(r.est_minutes, j.planned_minutes, j.est_minutes) e,"
         " r.timing_method m, j.category cat, j.title t FROM job_runs r "
         "JOIN jobs j ON j.id=r.job_id WHERE r.status='done' AND r.actual_minutes IS NOT NULL")
    args = []
    if job_id:
        q += " AND j.id=?"
        args.append(job_id)
    if since:
        q += " AND r.done_date >= ?"
        args.append(parse(since).isoformat())
    rows = conn.execute(q, args).fetchall()
    if not rows:
        return None
    num = den = 0.0
    for r in rows:
        w = METHOD_WEIGHT.get(r["m"], 0.5)
        num += w * r["a"]
        den += w * (r["e"] or r["a"])
    return round(num / den, 2) if den else None


def calibration_by_category(conn):
    out = {}
    rows = conn.execute(
        "SELECT j.category cat, r.actual_minutes a, "
        "COALESCE(r.est_minutes,j.planned_minutes,j.est_minutes) e, r.timing_method m "
        "FROM job_runs r JOIN jobs j ON j.id=r.job_id "
        "WHERE r.status='done' AND r.actual_minutes IS NOT NULL").fetchall()
    for r in rows:
        w = METHOD_WEIGHT.get(r["m"], 0.5)
        n, d = out.get(r["cat"], (0.0, 0.0))
        out[r["cat"]] = (n + w * r["a"], d + w * (r["e"] or r["a"]))
    return {k: round(n / d, 2) for k, (n, d) in out.items() if d}


def hours_by_month(conn, year=None):
    year = year or date.today().year
    out = {}
    for m in range(1, 13):
        row = conn.execute("SELECT COALESCE(SUM(minutes_total),0) t FROM visits "
                           "WHERE date LIKE ?", ("%d-%02d%%" % (year, m),)).fetchone()
        actual = round((row["t"] or 0) / 60.0, 1)
        planned = config.PLAN_HOURS.get(m, 0)
        out[m] = {"planned": planned, "actual": actual,
                  "variance": round(actual - planned, 1),
                  "factor": round(actual / planned, 2) if planned else None}
    return out


def overhead_ratio(conn):
    rows = conn.execute("SELECT id, minutes_total FROM visits "
                        "WHERE minutes_total IS NOT NULL").fetchall()
    if not rows:
        return None
    total = sum(r["minutes_total"] for r in rows) or 1
    oh = sum(overhead(conn, r["id"]) for r in rows)
    return {"per_visit": round(oh / len(rows)), "ratio": round(oh / total, 2),
            "visits": len(rows)}


def minutes_per_m2(conn):
    rows = conn.execute(
        "SELECT z.id, z.name, z.area_m2, COALESCE(SUM(r.actual_minutes),0) m "
        "FROM zones z LEFT JOIN job_runs r ON r.zone_id=z.id AND r.status='done' "
        "GROUP BY z.id ORDER BY 4 DESC").fetchall()
    return [{"zone": r["id"], "name": r["name"], "minutes": r["m"],
             "per_m2": round(r["m"] / r["area_m2"], 1) if r["area_m2"] else None}
            for r in rows if r["m"]]


def learning_rate(conn, job_id):
    """Change in actual minutes across repeats of the same job."""
    rows = conn.execute(
        "SELECT actual_minutes a FROM job_runs WHERE job_id=? AND status='done' "
        "AND actual_minutes IS NOT NULL ORDER BY done_date", (job_id,)).fetchall()
    if len(rows) < 2:
        return None
    first, last = rows[0]["a"], rows[-1]["a"]
    return round((last - first) / first, 2) if first else None
