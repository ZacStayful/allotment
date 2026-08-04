"""Load the seed data into a fresh database. Idempotent - safe to re-run."""

import json
import re

from . import config, db, seeddata, tenancy


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:48]


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
        key = job.get("key") or slug(job["title"])
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

    if not conn.execute("SELECT COUNT(*) c FROM trouble_pins").fetchone()["c"]:
        for x, y, title, kind, sev, desc, remedy in seeddata.TROUBLE:
            conn.execute("INSERT INTO trouble_pins(x,y,title,kind,severity,description,"
                         "remedy,source) VALUES(?,?,?,?,?,?,?,'derived')",
                         (x, y, title, kind, sev, desc, remedy))

    for s in seeddata.STOCK:
        item = s[0]
        if conn.execute("SELECT 1 FROM stock WHERE item=?", (item,)).fetchone():
            continue
        conn.execute("INSERT INTO stock(item,category,unit,qty,reorder_at,location,unit_cost,"
                     "expires,organic_certified,bulk_kg,bulk_m3) VALUES(?,?,?,?,?,?,?,?,?,?,?)", s)

    tenancy.seed(conn)
    first_rent(conn)

    conn.commit()
    return {
        "zones": conn.execute("SELECT COUNT(*) c FROM zones").fetchone()["c"],
        "crops": conn.execute("SELECT COUNT(*) c FROM crops").fetchone()["c"],
        "jobs": conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"],
        "stock": conn.execute("SELECT COUNT(*) c FROM stock").fetchone()["c"],
        "documents": conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"],
    }


def first_rent(conn):
    """The part-year subscription, once.

    Taking a plot on in August is 50% of the year's rent under section 2 of the
    tenancy agreement - the plot is not free until January, and a ledger that
    starts at zero would say the first year cost less than it did. Guarded on the
    date and the amount, because `seed` runs on every cold start."""
    when = db.get_setting(conn, "tenancy_start", "2026-08-01")
    paid = round(config.SUBSCRIPTION * PRORATION[(parse_month(when) - 1) // 3], 2)
    if conn.execute("SELECT 1 FROM spend WHERE date=? AND budget_line='rent'",
                    (when,)).fetchone():
        return
    conn.execute("INSERT INTO spend(date,vendor,category,amount,budget_line,setup,notes) "
                 "VALUES(?,?,?,?,?,?,?)",
                 (when, config.SITE_NAME, "rent", paid, "rent", 0,
                  "Subscription for the remainder of the first year, prorated"))
    conn.commit()


PRORATION = (1.0, 0.75, 0.5, 0.25)      # tenancy agreement 2, by quarter signed


def parse_month(iso):
    try:
        return int(str(iso)[5:7])
    except ValueError:
        return 1
