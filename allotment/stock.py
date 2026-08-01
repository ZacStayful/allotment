"""Supplies (§7, §32) and the shopping list (§17).

The rule that makes it worth building: a job checks its materials when it is
scheduled, not when you arrive. No vehicle access means an unplanned trip costs
you an hour, not a fiver.
"""

import json
import math
from datetime import date, timedelta

from . import config
from .rules import parse

ORGANIC_REQUIRED = {"treatments"}


def needs(job):
    raw = job["stock_needs"] if "stock_needs" in job.keys() else None
    if not raw:
        return []
    try:
        return [tuple(x) for x in json.loads(raw)]
    except (ValueError, TypeError):
        return []


def find(conn, item):
    return conn.execute("SELECT * FROM stock WHERE item=? COLLATE NOCASE", (item,)).fetchone()


def shortfalls(conn, job):
    """[(item, needed, have)] for anything this job cannot be done with."""
    out = []
    for item, qty in needs(job):
        row = find(conn, item)
        have = row["qty"] if row else 0
        if have < qty:
            out.append((item, qty, have))
    return out


def move(conn, stock_id, delta, reason, ref=None, when=None, visit_id=None):
    when = parse(when or date.today()).isoformat()
    conn.execute("INSERT INTO stock_moves(date,stock_id,delta,reason,ref,visit_id) "
                 "VALUES(?,?,?,?,?,?)", (when, stock_id, delta, reason, ref, visit_id))
    conn.execute("UPDATE stock SET qty=MAX(0, qty + ?) WHERE id=?", (delta, stock_id))
    conn.commit()


def add(conn, item, category, unit, qty=0, reorder_at=0, location="shed",
        unit_cost=None, expires=None, supplier=None, organic=0,
        bulk_kg=None, bulk_m3=None):
    if category in ORGANIC_REQUIRED and not organic:
        raise ValueError(
            "%s is a treatment: record organic certification before adding it. "
            "Organic-only is a tenancy condition, not a preference." % item)
    cur = conn.execute(
        "INSERT INTO stock(item,category,unit,qty,reorder_at,location,unit_cost,expires,"
        "supplier,organic_certified,bulk_kg,bulk_m3) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (item, category, unit, qty, reorder_at, location, unit_cost, expires, supplier,
         1 if organic else 0, bulk_kg, bulk_m3))
    conn.commit()
    return cur.lastrowid


def consume_for_run(conn, conn_job, qty_scale=1.0, visit_id=None):
    """Deduct a job's materials when it is marked done."""
    used = []
    for item, qty in needs(conn_job):
        row = find(conn, item)
        if row is None:
            continue
        take = min(row["qty"], qty * qty_scale)
        if take > 0:
            move(conn, row["id"], -take, "used", ref="job:%s" % conn_job["id"],
                 visit_id=visit_id)
            used.append((item, take))
    return used


def barrow_trips(row, qty):
    """§17 - roughly 60 kg or 0.1 m³ a load. Time goes on the job, not in a footnote."""
    kg = (row["bulk_kg"] or 0) * qty
    m3 = (row["bulk_m3"] or 0) * qty
    trips = max(kg / config.BARROW_KG if kg else 0, m3 / config.BARROW_M3 if m3 else 0)
    return int(math.ceil(trips)) if trips > 0 else 0


def upcoming_needs(conn, today=None, horizon_days=14):
    """Everything scheduled in the horizon that has a material requirement."""
    today = parse(today or date.today())
    end = today + timedelta(days=horizon_days)
    rows = conn.execute(
        "SELECT r.id run_id, r.due_date, j.* FROM job_runs r JOIN jobs j ON j.id=r.job_id "
        "WHERE r.status IN ('due','blocked') AND r.due_date BETWEEN ? AND ? "
        "AND j.stock_needs IS NOT NULL ORDER BY r.due_date",
        (today.isoformat(), end.isoformat())).fetchall()
    out = []
    for r in rows:
        for item, qty, have in shortfalls(conn, r):
            out.append({"item": item, "needed": qty, "have": have,
                        "job": r["title"], "due": r["due_date"]})
    return out


def shopping_list(conn, today=None, horizon_days=14):
    """Reorder points plus anything a scheduled job is short of."""
    today = parse(today or date.today())
    lines = {}

    def put(item, qty, why, row):
        e = lines.setdefault(item, {
            "item": item, "qty": 0, "why": [], "budget_line": _budget_line(row),
            "vendor": (row["supplier"] if row else None) or _vendor(row),
            "trips": 0, "cost": 0.0, "location": row["location"] if row else "shed"})
        e["qty"] = max(e["qty"], qty)
        if why not in e["why"]:
            e["why"].append(why)
        if row is not None:
            e["trips"] = barrow_trips(row, e["qty"])
            e["cost"] = round((row["unit_cost"] or 0) * e["qty"], 2)

    for row in conn.execute("SELECT * FROM stock WHERE qty <= reorder_at").fetchall():
        top_up = max(row["reorder_at"] * 2 - row["qty"], row["reorder_at"], 1)
        put(row["item"], top_up, "below reorder point", row)

    for n in upcoming_needs(conn, today, horizon_days):
        row = find(conn, n["item"])
        put(n["item"], max(n["needed"] - n["have"], 1),
            "%s due %s" % (n["job"], n["due"]), row)

    out = sorted(lines.values(), key=lambda x: (-x["trips"], x["item"]))
    for e in out:
        e["barrow_minutes"] = e["trips"] * config.BARROW_MINUTES
    return out


def _vendor(row):
    if row is None:
        return "Garden centre"
    return {"growing_media": "Garden centre", "build": "Timber merchant",
            "seed": "Seed supplier", "plants": "Seed supplier",
            "protection": "Garden centre", "support": "Garden centre",
            "treatments": "Garden centre"}.get(row["category"], "Garden centre")


def _budget_line(row):
    if row is None:
        return "consumables"
    return {"growing_media": "growing_media", "seed": "seeds_plants",
            "plants": "seeds_plants", "protection": "protection",
            "support": "protection", "treatments": "protection",
            "build": "beds", "fixings": "consumables"}.get(row["category"], "consumables")


def seed_review(conn, today=None):
    """§32 - flag expiring seed each January, before the order goes in."""
    today = parse(today or date.today())
    out = []
    for row in conn.execute("SELECT * FROM stock WHERE category='seed'").fetchall():
        if not row["expires"]:
            continue
        exp = parse(row["expires"])
        if exp <= today:
            out.append((row["item"], "expired %s" % exp.isoformat()))
        elif exp <= today + timedelta(days=365):
            out.append((row["item"], "expires %s" % exp.isoformat()))
    return out
