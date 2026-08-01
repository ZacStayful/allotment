"""Crop rotation (§13). Four groups moving one bed a year, proposed each
November, validated against what was actually planted rather than what was
intended."""

from datetime import date

from . import db, seeddata
from .rules import parse

BEDS = ["b1", "b2", "b3", "b4"]


def season_year(conn, today=None):
    """Which year of the four-year cycle we are in (1-4)."""
    today = parse(today or date.today())
    start = parse(db.get_setting(conn, "season_start", "2026-08-01"))
    years = (today - start).days // 365
    return int(years % 4) + 1


def plan_for(conn, year):
    idx = ((year - 1) % 4) + 1
    rows = conn.execute("SELECT zone_id, family_group FROM rotation WHERE year=?",
                        (idx,)).fetchall()
    return {r["zone_id"]: r["family_group"] for r in rows}


def group_name(group):
    return seeddata.GROUP_NAMES.get(group, group)


def history(conn, zone_id, years=3, today=None):
    """Families actually grown in a bed, from plantings."""
    today = parse(today or date.today())
    cutoff = date(today.year - years, today.month, min(today.day, 28)).isoformat()
    rows = conn.execute(
        "SELECT DISTINCT c.family, COALESCE(p.planted_date,p.sown_date) d "
        "FROM plantings p JOIN crops c ON c.id=p.crop_id "
        "WHERE p.zone_id=? AND COALESCE(p.planted_date,p.sown_date) >= ?",
        (zone_id, cutoff)).fetchall()
    return {r["family"]: r["d"] for r in rows if r["family"]}


def validate(conn, zone_id, family, today=None):
    """Reject any assignment putting the same family back within three years."""
    if not family:
        return None
    seen = history(conn, zone_id, 3, today)
    if family in seen:
        return ("%s was last grown in %s on %s - the same family cannot go back within "
                "three years" % (family, zone_id, seen[family]))
    z = conn.execute("SELECT growable, name FROM zones WHERE id=?", (zone_id,)).fetchone()
    if z is not None and not z["growable"]:
        return "%s is not a growing zone" % z["name"]
    return None


def propose(conn, today=None):
    """November planning: next year's bed assignment, with any clashes flagged."""
    today = parse(today or date.today())
    nxt = season_year(conn, today) + 1
    plan = plan_for(conn, nxt)
    out = []
    for zone_id, group in sorted(plan.items()):
        families = seeddata.GROUP_FAMILIES.get(group, [])
        problems = [p for p in (validate(conn, zone_id, f, today) for f in families) if p]
        out.append({"zone": zone_id, "group": group, "name": group_name(group),
                    "problems": problems})
    return {"year": nxt, "assignments": out}
