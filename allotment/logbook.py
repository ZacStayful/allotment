"""The log book: everything that was entered, with what was entered about it.

Every other page in this system aggregates. Money shows totals by budget line,
Time shows a calibration factor, Report shows the year. Those are the right
shape for deciding things and the wrong shape for remembering them: you enter a
vendor, a date, a note about which bed and what it was for, and the next screen
says `growing_media £412.00 3 items`. The detail is all in the database and none
of it was ever read back, which is indistinguishable from having lost it.

So: one reverse-chronological list, every source, nothing summarised away. It is
the slowest page here to read and the only one that answers "what did I actually
buy in March".
"""

from datetime import date, timedelta

from .rules import parse

KINDS = ("spend", "stock", "visit", "job", "harvest", "photo")


def _iso(value, fallback="0000-00-00"):
    return str(value)[:10] if value else fallback


def entries(conn, limit=80, kinds=None, since=None, until=None):
    """Everything logged, newest first. `kinds` filters to a subset of KINDS."""
    kinds = tuple(kinds) if kinds else KINDS
    since = parse(since).isoformat() if since else None
    until = parse(until).isoformat() if until else None
    out = []

    def keep(row):
        if since and row["date"] < since:
            return
        if until and row["date"] > until:
            return
        out.append(row)

    if "spend" in kinds:
        # A scalar subquery rather than a join: two photos of one receipt would
        # otherwise list the spend twice.
        for r in conn.execute(
                "SELECT s.*, (SELECT MAX(p.id) FROM photos p "
                "WHERE p.subject = 'receipt:' || s.receipt_id) photo_id "
                "FROM spend s ORDER BY s.date DESC, s.id DESC").fetchall():
            keep({
                "date": _iso(r["date"]), "at": _iso(r["date"]), "kind": "spend",
                "title": "£%.2f %s" % (r["amount"], r["vendor"] or "unrecorded shop"),
                "what": r["category"], "line": r["budget_line"],
                "amount": r["amount"], "notes": r["notes"],
                "tag": "setup" if r["setup"] else "running",
                "photo_id": r["photo_id"], "id": r["id"],
            })

    if "stock" in kinds:
        for r in conn.execute(
                "SELECT m.*, s.item, s.unit FROM stock_moves m "
                "JOIN stock s ON s.id=m.stock_id ORDER BY m.date DESC, m.id DESC").fetchall():
            keep({
                "date": _iso(r["date"]), "at": _iso(r["date"]), "kind": "stock",
                "title": "%+g %s %s" % (r["delta"], r["unit"] or "", r["item"]),
                "what": r["reason"], "line": r["ref"], "amount": None,
                "notes": r["notes"], "tag": "in" if r["delta"] > 0 else "out",
                "photo_id": None, "id": r["id"],
            })

    if "visit" in kinds:
        for r in conn.execute("SELECT * FROM visits ORDER BY date DESC, id DESC").fetchall():
            span = ("%s-%s" % (r["arrive_time"], r["leave_time"])
                    if r["arrive_time"] and r["leave_time"] else None)
            keep({
                "date": _iso(r["date"]), "at": _iso(r["date"]), "kind": "visit",
                "title": "Visit - %s minutes" % (r["minutes_total"] or 0),
                "what": r["who"], "line": span, "amount": None, "notes": r["notes"],
                "tag": r["mood"], "photo_id": None, "id": r["id"],
            })

    if "job" in kinds:
        for r in conn.execute(
                "SELECT r.*, j.title, j.stream, j.category FROM job_runs r "
                "JOIN jobs j ON j.id=r.job_id WHERE r.status IN ('done','skipped') "
                "ORDER BY COALESCE(r.done_date, r.due_date) DESC, r.id DESC").fetchall():
            keep({
                "date": _iso(r["done_date"] or r["due_date"]),
                "at": _iso(r["done_date"] or r["due_date"]), "kind": "job",
                "title": r["title"],
                "what": "%s minutes, %s" % (r["actual_minutes"], r["timing_method"])
                        if r["actual_minutes"] is not None else r["status"],
                "line": r["done_by"], "amount": None, "notes": r["notes"],
                "tag": r["stream"] or r["category"], "photo_id": None, "id": r["id"],
            })

    if "harvest" in kinds:
        for r in conn.execute("SELECT * FROM harvests ORDER BY date DESC, id DESC").fetchall():
            keep({
                "date": _iso(r["date"]), "at": _iso(r["date"]), "kind": "harvest",
                "title": "%.2f kg %s" % (r["kg"], r["crop"]), "what": None,
                "line": None, "amount": None, "notes": r["notes"], "tag": "harvest",
                "photo_id": None, "id": r["id"],
            })

    if "photo" in kinds:
        for r in conn.execute(
                "SELECT id, taken, subject, caption FROM photos "
                "ORDER BY taken DESC, id DESC").fetchall():
            keep({
                "date": _iso(r["taken"]), "at": str(r["taken"])[:16].replace("T", " "),
                "kind": "photo", "title": r["caption"] or "Photograph",
                "what": r["subject"], "line": None, "amount": None, "notes": None,
                "tag": r["subject"].split(":")[0], "photo_id": r["id"], "id": r["id"],
            })

    out.sort(key=lambda r: (r["date"], r["at"], r["id"]), reverse=True)
    return out[:limit] if limit else out


def totals(conn, since=None, until=None):
    """What the window adds up to, so the list has a header worth reading."""
    rows = entries(conn, limit=None, since=since, until=until)
    spend = [r for r in rows if r["kind"] == "spend"]
    return {
        "entries": len(rows),
        "spend": round(sum(r["amount"] or 0 for r in spend), 2),
        "spend_items": len(spend),
        "visits": len([r for r in rows if r["kind"] == "visit"]),
        "jobs": len([r for r in rows if r["kind"] == "job"]),
        "harvest_kg": round(sum(float(r["title"].split()[0])
                                for r in rows if r["kind"] == "harvest"), 1),
        "first": min((r["date"] for r in rows), default=None),
        "last": max((r["date"] for r in rows), default=None),
    }


def month(conn, when=None):
    """One calendar month of the log book, for the page that opens on this one."""
    when = parse(when or date.today())
    start = when.replace(day=1)
    nxt = (start.replace(year=start.year + 1, month=1) if start.month == 12
           else start.replace(month=start.month + 1))
    return entries(conn, limit=None, since=start, until=nxt - timedelta(days=1))
