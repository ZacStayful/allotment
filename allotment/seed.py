"""Load the seed data into a fresh database. Idempotent - safe to re-run."""

import json
import re

from . import db, seeddata


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:48]


def job_key(job):
    return job.get("key") or slug(job["title"])


def _in(ids):
    """A SQL IN list for a set of text ids, safe because ids are our own."""
    return ",".join("'" + str(i).replace("'", "''") + "'" for i in ids) or "''"


def retire(conn):
    """Drop what the seed used to own and no longer does.

    Everything above is an upsert, so a change of layout otherwise leaves the
    old one behind: a database seeded under the V1 plot and re-seeded under the
    V2 survey ended up with 37 zones - both plans at once - and trouble pins
    still at their V1 coordinates. Only ever deletes rows the seed itself put
    there, and never one carrying real history: a job that has been worked, a
    crop that has been planted or a zone still referenced keeps its place and
    is named in the return value instead.
    """
    zone_ids = {z[0] for z in seeddata.ZONES}
    crop_ids = {c[0] for c in seeddata.CROPS}
    keys = {job_key(j) for j in seeddata.BUILD + seeddata.JOBS}
    kept = []

    # Rotation rows and derived pins are pure derived data - no history to lose.
    conn.execute("DELETE FROM rotation WHERE zone_id NOT IN (%s)" % _in(zone_ids))
    conn.execute("DELETE FROM trouble_pins WHERE source='derived'")
    for x, y, title, kind, sev, desc, remedy in seeddata.TROUBLE:
        conn.execute("INSERT INTO trouble_pins(x,y,title,kind,severity,description,"
                     "remedy,source) VALUES(?,?,?,?,?,?,?,'derived')",
                     (x, y, title, kind, sev, desc, remedy))

    # Jobs first: they reference both crops and zones. job_runs cascade, so a
    # job that has ever been worked is history and stays.
    for r in conn.execute("SELECT id, job_key, title FROM jobs "
                          "WHERE job_key NOT IN (%s)" % _in(keys)).fetchall():
        worked = conn.execute("SELECT COUNT(*) c FROM job_runs WHERE job_id=? "
                              "AND status IS NOT NULL AND status <> 'due'",
                              (r["id"],)).fetchone()["c"]
        if worked:
            kept.append("job %s (%d logged runs)" % (r["job_key"], worked))
            continue
        conn.execute("DELETE FROM job_runs WHERE job_id=?", (r["id"],))
        conn.execute("DELETE FROM jobs WHERE id=?", (r["id"],))

    for r in conn.execute("SELECT id FROM crops WHERE id NOT IN (%s)" % _in(crop_ids)).fetchall():
        n = conn.execute("SELECT COUNT(*) c FROM plantings WHERE crop_id=?",
                         (r["id"],)).fetchone()["c"]
        if n:
            kept.append("crop %s (%d plantings)" % (r["id"], n))
            continue
        conn.execute("DELETE FROM crops WHERE id=?", (r["id"],))

    for r in conn.execute("SELECT id, name FROM zones WHERE id NOT IN (%s)" % _in(zone_ids)).fetchall():
        holds = 0
        for table in ("plantings", "jobs", "crops", "weed_observations"):
            holds += conn.execute("SELECT COUNT(*) c FROM %s WHERE zone_id=?" % table,
                                  (r["id"],)).fetchone()["c"]
        if holds:
            kept.append("zone %s (%d rows still reference it)" % (r["id"], holds))
            continue
        conn.execute("DELETE FROM zones WHERE id=?", (r["id"],))

    conn.commit()
    return kept


def seed(conn):
    for k, v in db.DEFAULT_SETTINGS.items():
        if db.get_setting(conn, k, None) is None:
            db.set_setting(conn, k, v)

    for z in seeddata.ZONES:
        zid, name, ztype, x, y, w, d, h, growable, colour, notes = z
        conn.execute(
            "INSERT INTO zones(id,name,type,area_m2,notes,x,y,w,d,height_m,growable,colour) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "name=excluded.name,type=excluded.type,area_m2=excluded.area_m2,x=excluded.x,"
            "y=excluded.y,w=excluded.w,d=excluded.d,height_m=excluded.height_m,"
            "growable=excluded.growable,colour=excluded.colour,notes=excluded.notes",
            (zid, name, ztype, round(w * d, 2), notes, x, y, w, d, h, growable, colour))

    for c in seeddata.CROPS:
        conn.execute(
            "INSERT INTO crops(id,name,zone_id,family,sow_indoor_from,sow_indoor_to,"
            "sow_from,sow_to,plant_from,plant_to,harvest_from,harvest_to,spacing_cm,"
            "needs_netting,needs_support,fruiting,notes) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "name=excluded.name,zone_id=excluded.zone_id,family=excluded.family,"
            "sow_indoor_from=excluded.sow_indoor_from,sow_indoor_to=excluded.sow_indoor_to,"
            "sow_from=excluded.sow_from,sow_to=excluded.sow_to,plant_from=excluded.plant_from,"
            "plant_to=excluded.plant_to,harvest_from=excluded.harvest_from,"
            "harvest_to=excluded.harvest_to,notes=excluded.notes", c)

    for job in seeddata.BUILD + seeddata.JOBS:
        key = job_key(job)
        params = dict(job["rule_params"])
        if job.get("requires"):
            # a job that needs a structure or a bed is blocked until it exists
            params["depends_on"] = sorted(set(params.get("depends_on", []))
                                          | set(job["requires"]))
        conn.execute(
            "INSERT INTO jobs(job_key,title,category,owner,est_minutes,planned_minutes,"
            "rule_type,rule_params,depends_on,one_off,zone_id,crop_id,consequence,"
            "stock_needs,every_visit,needs_permission,notes,phase) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(job_key) DO UPDATE SET "
            "title=excluded.title,category=excluded.category,owner=excluded.owner,"
            "rule_type=excluded.rule_type,rule_params=excluded.rule_params,"
            "depends_on=excluded.depends_on,zone_id=excluded.zone_id,"
            "crop_id=excluded.crop_id,consequence=excluded.consequence,"
            "stock_needs=excluded.stock_needs,every_visit=excluded.every_visit,"
            "needs_permission=excluded.needs_permission,notes=excluded.notes",
            (key, job["title"], job["category"], job["owner"], job["est_minutes"],
             job["est_minutes"], job["rule_type"], json.dumps(params),
             json.dumps(params.get("depends_on", [])), job.get("one_off", 0),
             job.get("zone_id"), job.get("crop_id"), job.get("consequence", 2),
             json.dumps(job["stock_needs"]) if job.get("stock_needs") else None,
             job.get("every_visit", 0), job.get("needs_permission", 0),
             job.get("notes"), job.get("phase", "build" if job.get("one_off") else "season")))

    for year, mapping in seeddata.ROTATION.items():
        for zid, group in mapping.items():
            conn.execute("INSERT INTO rotation(year,zone_id,family_group) VALUES(?,?,?) "
                         "ON CONFLICT(year,zone_id) DO UPDATE SET family_group=excluded.family_group",
                         (year, zid, group))

    for s in seeddata.STOCK:
        item = s[0]
        if conn.execute("SELECT 1 FROM stock WHERE item=?", (item,)).fetchone():
            continue
        conn.execute("INSERT INTO stock(item,category,unit,qty,reorder_at,location,unit_cost,"
                     "expires,organic_certified,bulk_kg,bulk_m3) VALUES(?,?,?,?,?,?,?,?,?,?,?)", s)

    conn.commit()
    kept = retire(conn)
    db.set_setting(conn, "seed_version", seeddata.SEED_VERSION)
    conn.commit()
    return {
        "kept": kept,
        "zones": conn.execute("SELECT COUNT(*) c FROM zones").fetchone()["c"],
        "crops": conn.execute("SELECT COUNT(*) c FROM crops").fetchone()["c"],
        "jobs": conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"],
        "stock": conn.execute("SELECT COUNT(*) c FROM stock").fetchone()["c"],
    }
