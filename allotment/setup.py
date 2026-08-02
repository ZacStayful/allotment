"""Part one: getting the plot ready to grow food, in order.

The jobs engine is right for a running plot and wrong for an empty one. It
scores everything against everything and shows you the top five, which on a
plot with nothing on it is five things you cannot do and no sense of where the
work starts. This module reads the same jobs back as what they are - a
numbered sequence with one thing at the front of it.

The step numbers are the guide. The dependencies in the seed data are the
enforcement, and `test_setup_steps_never_depend_on_a_later_one` holds the two
together, because a guide that tells you to do step 7 before step 3 is worse
than no guide.
"""

from datetime import date

from . import seeddata, stock
from .rules import blocked_reason, parse

# States, worst last, so `sorted` and `min` do the obvious thing.
DONE, NOW, SHOPPING, WAITING = "done", "now", "shopping", "waiting"

# The step past which the plot can be sown. Re-exported so callers do not have
# to reach through this module into the seed data for it.
GROWING_READY = seeddata.GROWING_READY


def _jobs(conn):
    return conn.execute(
        "SELECT * FROM jobs WHERE stream='setup' AND active=1 "
        "ORDER BY step, id").fetchall()


def _run(conn, job_id):
    return conn.execute(
        "SELECT * FROM job_runs WHERE job_id=? ORDER BY due_date DESC, id DESC LIMIT 1",
        (job_id,)).fetchone()


def _done_row(conn, job_id):
    return conn.execute(
        "SELECT MAX(done_date) d, COUNT(*) c FROM job_runs WHERE job_id=? AND status='done'",
        (job_id,)).fetchone()


def steps(conn, today=None):
    """Every setup step in order, each with the state it is actually in.

    Weather is deliberately not consulted. This is the standing plan - what the
    order is and what is holding it up - not what to do this afternoon. Today
    answers that, and a step that is merely rained off should not read as though
    the sequence is stuck.
    """
    today = parse(today or date.today())
    out = []
    for job in _jobs(conn):
        done = _done_row(conn, job["id"])
        run = _run(conn, job["id"])
        short = stock.shortfalls(conn, job)
        blocked = blocked_reason(conn, job, None, today)
        if done and done["c"]:
            state, why = DONE, "Done %s" % done["d"]
        elif blocked:
            state, why = WAITING, blocked
        elif short:
            state = SHOPPING
            why = "Needs %s" % ", ".join(
                "%g %s (have %g)" % (need, item, have) for item, need, have in short)
        else:
            state, why = NOW, "Ready to do"
        out.append({
            "step": job["step"], "key": job["job_key"], "title": job["title"],
            "owner": job["owner"], "minutes": job["est_minutes"],
            "zone": job["zone_id"], "purpose": job["notes"], "state": state,
            "why": why, "done_date": done["d"] if done and done["c"] else None,
            "run_id": run["id"] if run and state != DONE else None,
            "buy": [{"item": i, "need": n, "have": h} for i, n, h in short],
            "grows_food_after": job["step"] == seeddata.GROWING_READY,
        })
    return out


def progress(conn, today=None):
    """Where the build has got to, in the two numbers worth printing."""
    rows = steps(conn, today)
    done = [s for s in rows if s["state"] == DONE]
    left = [s for s in rows if s["state"] != DONE]
    to_grow = [s for s in left if s["step"] <= seeddata.GROWING_READY]
    return {
        "steps": rows,
        "done": len(done), "total": len(rows),
        "minutes_left": sum(s["minutes"] for s in left),
        "next": left[0] if left else None,
        # Ready to grow is not the same as finished. The shed and the tunnel are
        # steps 9 to 16 and nothing is waiting to be sown on either of them.
        "growing_ready": not to_grow,
        "steps_to_growing": len(to_grow),
        "minutes_to_growing": sum(s["minutes"] for s in to_grow),
        "complete": not left,
    }


def growing_ready(conn, today=None):
    """True once the beds are built and filled - the point food can go in."""
    return progress(conn, today)["growing_ready"]


def actionable(conn, today=None, limit=3):
    """The steps that can be started right now, nearest the front of the queue.

    Three at most. A setup sequence that prints sixteen things is the wall of
    text the numbering exists to replace.
    """
    return [s for s in steps(conn, today)
            if s["state"] in (NOW, SHOPPING)][:limit]
