"""Spending (§6), the asset register (§34) and the year report (§35).

The asset register replaces the plan's £3/month polythene and £2/month tools
guesses with a calculated figure. It will come out higher - which is the point.
"""

from datetime import date, timedelta

from . import config, seeddata
from .rules import parse

SETUP_LINES = {"clearance", "tools", "shed", "water", "polytunnel", "beds",
               "growing_media", "paths"}
RETAIL_PER_KG = {                       # rough farm-shop prices, for the food column
    "potato": 1.60, "onion": 1.80, "garlic": 8.00, "broad beans": 4.50,
    "beetroot": 2.20, "chard": 6.00, "kale": 5.00, "salad": 12.00,
    "courgette": 3.00, "runner beans": 5.00, "french beans": 5.50,
    "tomato": 4.50, "cucumber": 3.00, "radish": 4.00, "turnip": 2.00,
}
DEFAULT_RETAIL = 3.50


def add_spend(conn, amount, budget_line, vendor=None, category=None, when=None,
              notes=None, setup=None, receipt_id=None):
    """Record a spend. `category` is what the thing actually was.

    Budget lines are a dozen buckets for the variance report; "growing_media"
    six months later does not tell you it was four bags of peat-free for bed 3.
    Both are kept, and the log book reads them back.
    """
    if budget_line not in config.BUDGET_LINES:
        raise ValueError("Unknown budget line %r. One of: %s"
                         % (budget_line, ", ".join(config.BUDGET_LINES)))
    when = parse(when or date.today())
    if setup is None:
        setup = 1 if budget_line in SETUP_LINES else 0
    cur = conn.execute(
        "INSERT INTO spend(date,vendor,category,amount,budget_line,setup,notes,receipt_id) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (when.isoformat(), vendor, category, float(amount), budget_line,
         int(bool(setup)), notes, receipt_id))
    conn.commit()
    return cur.lastrowid


def recent(conn, limit=25, setup_only=None):
    """Individual spends, newest first - the rows the totals are made of."""
    q = "SELECT * FROM spend"
    args = []
    if setup_only is not None:
        q += " WHERE setup=?"
        args.append(1 if setup_only else 0)
    q += " ORDER BY date DESC, id DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(q, args).fetchall()]


def by_line(conn, setup_only=None):
    q = "SELECT budget_line, SUM(amount) t, COUNT(*) n FROM spend"
    args = []
    if setup_only is not None:
        q += " WHERE setup=?"
        args.append(1 if setup_only else 0)
    q += " GROUP BY budget_line ORDER BY 2 DESC"
    return [dict(r) for r in conn.execute(q, args).fetchall()]


def setup_total(conn):
    return conn.execute("SELECT COALESCE(SUM(amount),0) t FROM spend "
                        "WHERE setup=1").fetchone()["t"]


def running_total(conn, months=None):
    q = "SELECT COALESCE(SUM(amount),0) t FROM spend WHERE setup=0"
    args = []
    if months:
        since = (date.today() - timedelta(days=30 * months)).isoformat()
        q += " AND date >= ?"
        args.append(since)
    return conn.execute(q, args).fetchone()["t"]


def monthly_rate(conn, today=None):
    today = parse(today or date.today())
    row = conn.execute("SELECT MIN(date) d FROM spend WHERE setup=0").fetchone()
    if not row["d"]:
        return None
    first = parse(row["d"])
    months = max(1, (today.year - first.year) * 12 + today.month - first.month + 1)
    total = running_total(conn)
    return {"months": months, "total": round(total, 2),
            "per_month": round(total / months, 2),
            "target": config.RUNNING_BUDGET}


def variance(conn):
    spent = setup_total(conn)
    lo, hi = config.SETUP_BUDGET
    return {"setup_spent": round(spent, 2), "setup_budget": (lo, hi),
            "over": round(spent - hi, 2) if spent > hi else 0.0,
            "contingency": round(hi * config.CONTINGENCY_PCT, 2),
            "lines": by_line(conn, setup_only=True)}


# ---------------------------------------------------------------- assets §34

def add_asset(conn, item, price, purchase_date=None, life_years=None, category=None,
              residual=0.0, **kw):
    if life_years is None:
        life_years = seeddata.ASSET_LIVES.get(item, 10)
    cur = conn.execute(
        "INSERT INTO assets(item,category,purchase_date,purchase_price,expected_life_years,"
        "residual_value,condition,location,serial,supplier,notes) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (item, category, parse(purchase_date or date.today()).isoformat(), float(price),
         float(life_years), float(residual), kw.get("condition", "new"),
         kw.get("location"), kw.get("serial"), kw.get("supplier"), kw.get("notes")))
    conn.commit()
    return cur.lastrowid


def annual_depreciation(asset):
    if asset["depreciation"] == "none" or not asset["expected_life_years"]:
        return 0.0
    return ((asset["purchase_price"] or 0) - (asset["residual_value"] or 0)) \
        / asset["expected_life_years"]


def book_value(asset, today=None):
    today = parse(today or date.today())
    if not asset["purchase_date"]:
        return asset["purchase_price"] or 0.0
    years = (today - parse(asset["purchase_date"])).days / 365.25
    val = (asset["purchase_price"] or 0) - years * annual_depreciation(asset)
    return round(max(val, asset["residual_value"] or 0.0), 2)


def register(conn, today=None):
    rows = conn.execute("SELECT * FROM assets WHERE disposal_date IS NULL").fetchall()
    out = []
    for a in rows:
        dep = annual_depreciation(a)
        out.append({"id": a["id"], "item": a["item"], "price": a["purchase_price"],
                    "life": a["expected_life_years"], "annual_dep": round(dep, 2),
                    "book": book_value(a, today), "condition": a["condition"],
                    "purchased": a["purchase_date"]})
    return out


def sinking_fund(conn):
    total = sum(annual_depreciation(a) for a in
                conn.execute("SELECT * FROM assets WHERE disposal_date IS NULL").fetchall())
    return round(total / 12.0, 2)


def end_of_life(conn, today=None, warn_years=1.0):
    today = parse(today or date.today())
    out = []
    for a in conn.execute("SELECT * FROM assets WHERE disposal_date IS NULL").fetchall():
        if not (a["purchase_date"] and a["expected_life_years"]):
            continue
        age = (today - parse(a["purchase_date"])).days / 365.25
        left = a["expected_life_years"] - age
        if left <= warn_years:
            out.append("%s is %.1f years old of %g - start the fund now"
                       % (a["item"], age, a["expected_life_years"]))
        if a["condition"] in ("poor", "failed"):
            out.append("%s is marked %s - schedule a repair or replacement"
                       % (a["item"], a["condition"]))
    return out


# -------------------------------------------------------------- harvest §35

def harvest_totals(conn, year=None):
    year = year or date.today().year
    rows = conn.execute("SELECT crop, SUM(kg) kg FROM harvests WHERE date LIKE ? "
                        "GROUP BY crop ORDER BY 2 DESC", ("%d%%" % year,)).fetchall()
    kg = sum(r["kg"] for r in rows)
    value = 0.0
    for r in rows:
        key = next((k for k in RETAIL_PER_KG if k in (r["crop"] or "").lower()), None)
        value += r["kg"] * (RETAIL_PER_KG.get(key, DEFAULT_RETAIL))
    return {"kg": round(kg, 1), "value": round(value, 2),
            "by_crop": [dict(r) for r in rows]}


def report(conn, year=None, today=None):
    """§35 - one command, the numbers that matter."""
    from . import ledger, priority
    year = year or date.today().year
    today = parse(today or date.today())

    setup = setup_total(conn)
    running = conn.execute(
        "SELECT COALESCE(SUM(amount),0) t FROM spend WHERE setup=0 AND date LIKE ?",
        ("%d%%" % year,)).fetchone()["t"]
    dep = sum(annual_depreciation(a) for a in
              conn.execute("SELECT * FROM assets WHERE disposal_date IS NULL").fetchall())
    books = sum(book_value(a, today) for a in
                conn.execute("SELECT * FROM assets WHERE disposal_date IS NULL").fetchall())

    mins = conn.execute("SELECT COALESCE(SUM(minutes_total),0) t FROM visits "
                        "WHERE date LIKE ?", ("%d%%" % year,)).fetchone()["t"]
    hours = round(mins / 60.0, 1)
    planned = sum(config.PLAN_HOURS.values())

    h = harvest_totals(conn, year)
    true_cost = running + dep
    fails = conn.execute("SELECT failure_reason r, COUNT(*) c FROM plantings "
                         "WHERE status='failed' AND failure_reason IS NOT NULL "
                         "GROUP BY 1 ORDER BY 2 DESC").fetchall()
    split = priority.person_split(conn, today)

    return {
        "year": year,
        "money": {"setup": round(setup, 2), "setup_budget": config.SETUP_BUDGET,
                  "running": round(running, 2), "depreciation": round(dep, 2),
                  "true_cost": round(true_cost + (setup if year == _first_year(conn) else 0), 2),
                  "book_value": round(books, 2),
                  "sinking_fund_monthly": sinking_fund(conn)},
        "time": {"hours": hours, "planned": planned,
                 "calibration": ledger.calibration(conn),
                 "overhead": ledger.overhead_ratio(conn),
                 "split": split,
                 "winter_attendance": priority.winter_attendance(conn, today)},
        "food": {"kg": h["kg"], "value": h["value"],
                 "cost_per_kg": round((true_cost + setup) / h["kg"], 2) if h["kg"] else None,
                 "cost_per_kg_excl_setup": round(true_cost / h["kg"], 2) if h["kg"] else None,
                 "by_crop": h["by_crop"]},
        "failures": [dict(f) for f in fails],
        "mood": priority.mood_split(conn),
    }


def _first_year(conn):
    row = conn.execute("SELECT MIN(date) d FROM spend").fetchone()
    return parse(row["d"]).year if row["d"] else date.today().year
