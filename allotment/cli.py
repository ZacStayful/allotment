"""`plot` - the CLI. CLI first; the web view is there for the map and for phones."""

import argparse
import json
import os
import sys
from datetime import date, timedelta

from . import (auth, config, db, ledger, money, planner, priority, rotation,
               rules, seed, stock, sun, weather, weeds)
from .rules import parse

BOLD, DIM, OFF = "\033[1m", "\033[2m", "\033[0m"


def _c(s, code):
    return s if not sys.stdout.isatty() else code + s + OFF


def hm(minutes):
    minutes = int(round(minutes or 0))
    h, m = divmod(minutes, 60)
    return ("%dh %02dm" % (h, m)) if h else "%dm" % m


def open_db(args):
    conn = db.connect(getattr(args, "db", None))
    db.init(conn)
    return conn


def where(args):
    return getattr(args, "db", None) or db.DATABASE_URL and "Postgres" or config.DB_PATH


def refresh(conn, today, offline=False):
    """Cache weather once a day, then materialise everything due.

    Nothing is generated before the season start: a plot taken on in August
    should not open with 'plant maincrop potatoes, overdue by 109 days'."""
    err = None
    if not offline:
        _, err = weather.refresh(conn, today)
    wx = weather.Weather(conn, today)
    rules.lapse(conn, today)
    season = parse(db.get_setting(conn, "season_start", today))
    start = max(today - timedelta(days=120), season)
    rules.ensure_runs(conn, start, today + timedelta(days=21), wx)
    return wx, err


def read_password(given=None, confirm=True):
    """--password, then ALLOTMENT_PASSWORD, then a prompt, then a random one."""
    import getpass
    import secrets
    pw = given or os.environ.get("ALLOTMENT_PASSWORD")
    if not pw and sys.stdin.isatty():
        pw = getpass.getpass("Password for the web login: ")
        if confirm and pw != getpass.getpass("Again: "):
            sys.exit("Passwords did not match.")
    if not pw:
        return secrets.token_urlsafe(12), True
    if len(pw) < config.MIN_PASSWORD:
        sys.exit("Password must be at least %d characters." % config.MIN_PASSWORD)
    return pw, False


# ------------------------------------------------------------------ commands

def cmd_init(args):
    conn = open_db(args)
    counts = seed.seed(conn)
    db.set_setting(conn, "season_start", (args.season or date.today().isoformat()))
    email = args.email or config.DEFAULT_EMAIL
    if auth.get_user(conn, email) is None:
        users = conn.execute("SELECT email FROM users").fetchall()
        if len(users) == 1:
            # a single account whose address was mistyped is corrected, not duplicated
            auth.rename(conn, users[0]["email"], email)
            print("Login email changed from %s to %s (password unchanged)"
                  % (users[0]["email"], email))
        else:
            pw, generated = read_password(args.password)
            auth.create_user(conn, email, pw, name=args.name, role="Both")
            print("Created login for %s" % email)
            if generated:
                print("Generated password: %s" % pw)
                print("Write it down - it is not stored anywhere in plain text.")
    print("Seeded: %(zones)d zones, %(crops)d crops, %(jobs)d jobs, %(stock)d stock lines"
          % counts)
    # A re-seed after a layout change retires what the seed no longer owns, but
    # never anything carrying history. Say what it had to leave behind.
    for line in counts.get("kept") or []:
        print("Kept (has history): %s" % line)
    today = date.today()
    wx, err = refresh(conn, today, args.offline)
    if err:
        print("Weather unavailable (%s) - the rest still works" % err)
    print("Database: %s" % where(args))
    print("Now run:  plot today")


def cmd_today(args):
    conn = open_db(args)
    today = parse(args.date) if args.date else date.today()
    wx, err = refresh(conn, today, args.offline)
    view = priority.plan_day(conn, today, wx, limit=args.limit)
    print(render_today(view, err))


def render_today(v, err=None):
    d = v["date"]
    out = ["%s %s          %s" % (_c(d.strftime("%A").upper(), BOLD),
                                  _c(d.strftime("%d %B").upper().lstrip("0"), BOLD),
                                  v["weather"])]
    if err:
        out.append(_c("  weather cache stale: %s" % err, DIM))
    if not v["top"]:
        out.append("  Nothing scheduled. Have a look round anyway.")
    for i, s in enumerate(v["top"], 1):
        out.append("  %d. %-44s %-7s %6s" % (i, s["title"][:44], s["owner"], hm(s["minutes"])))
        out.append("     %s" % _c(s["why"], DIM))
    if v["every_visit"]:
        bits = ", ".join("%s (%s)" % (e["title"].lower(), hm(e["minutes"]))
                         for e in v["every_visit"])
        out.append("  Also every visit: %s" % bits)
    if v["also"]:
        out.append("  Also due: %s" % ", ".join("%s (%s)" % (s["title"], hm(s["minutes"]))
                                                for s in v["also"][:6]))
    out.append("  Estimated total: %-14s Planned for %s: %sh, logged %sh"
               % (hm(v["minutes"]), d.strftime("%B"), v["hours"]["planned_h"],
                  v["hours"]["logged_h"]))
    for b in v["blocked"][:5]:
        out.append("  " + _c("Blocked: %s - %s" % (b["title"], b["blocked"]), BOLD))
    for kind, msg in v["risks"][:5]:
        out.append("  " + _c("! %-18s %s" % (kind, msg), BOLD))
    if v["inspection"]:
        n = (v["inspection"] - d).days
        out.append(_c("  Next inspection: %s (%d days)" % (v["inspection"], n), DIM))
    return "\n".join(out)


def cmd_week(args):
    conn = open_db(args)
    today = parse(args.date) if args.date else date.today()
    wx, _ = refresh(conn, today, args.offline)
    w = planner.plan_week(conn, today, wx)
    print(render_week(w))


def render_week(w):
    out = ["%s %s        Budget: 4h Sat, 3h Sun, 30m midweek"
           % (_c("WEEK OF", BOLD), _c(w["start"].strftime("%d %B").upper().lstrip("0"), BOLD))]
    for day in w["days"]:
        d = day["date"]
        label = d.strftime("%a").upper()
        if not day["items"]:
            out.append("%-4s  %-5s %s" % (label, "-", _c("Nothing due", DIM)))
            continue
        first = True
        for it in day["items"]:
            head = (label, hm(day["used"])) if first else ("", "")
            first = False
            out.append("%-4s %6s  %-44s %6s  %s"
                       % (head[0], head[1], it["title"][:44], hm(it["minutes"]),
                          _c(it["why"], DIM)))
    for df in w["deferred"][:6]:
        tail = (" - needs %s" % df["unblocks"]) if df["unblocks"] else ""
        out.append("%-10s %s - %s%s" % ("DEFERRED", df["title"], df["why"], tail))
    return "\n".join(out)


def cmd_done(args):
    conn = open_db(args)
    res = ledger.complete(conn, args.run_id, actual_minutes=args.minutes,
                          method="entered" if args.minutes else "allocated",
                          notes=args.notes, who=args.who)
    print("Done: %s%s" % (res["job"], " (%s)" % hm(args.minutes) if args.minutes else "")
          if res else "No such job run")


def cmd_skip(args):
    conn = open_db(args)
    ledger.skip(conn, args.run_id, args.notes)
    print("Skipped run %d" % args.run_id)


def cmd_arrive(args):
    conn = open_db(args)
    vid = ledger.arrive(conn, who=args.who)
    print("Visit %d started. `plot start <run_id>` to time a job." % vid)


def cmd_leave(args):
    conn = open_db(args)
    res = ledger.leave(conn, mood=args.mood, notes=args.notes)
    if not res:
        print("No visit open.")
        return
    print("Visit %d: %s, overhead %s" % (res["id"], hm(res["minutes"]), hm(res["overhead"])))


def cmd_start(args):
    conn = open_db(args)
    ledger.start_job(conn, args.run_id)
    print("Timing run %d" % args.run_id)


def cmd_stop(args):
    conn = open_db(args)
    res = ledger.stop_job(conn, args.run_id, notes=args.notes)
    print("Stopped: %s, %s" % (res["job"], hm(res["minutes"])) if res else "No such run")


def cmd_log(args):
    conn = open_db(args)
    runs = [int(x) for x in args.jobs.split(",")] if args.jobs else None
    vid = ledger.log_visit(conn, args.minutes, who=args.who, mood=args.mood,
                           notes=args.notes, when=args.date, run_ids=runs)
    print("Logged visit %d: %s, %s%s"
          % (vid, hm(args.minutes), args.who, ", %s" % args.mood if args.mood else ""))


def cmd_spend(args):
    conn = open_db(args)
    sid = money.add_spend(conn, args.amount, args.budget_line, vendor=args.vendor,
                          when=args.date, notes=args.notes)
    v = money.variance(conn)
    print("Spend %d: £%.2f %s / %s" % (sid, args.amount, args.vendor or "-",
                                       args.budget_line))
    print("Setup to date £%.2f of £%.0f-%.0f" % (v["setup_spent"], *v["setup_budget"]))


def cmd_budget(args):
    conn = open_db(args)
    v = money.variance(conn)
    print("SETUP  £%.2f of £%.0f-%.0f" % (v["setup_spent"], *v["setup_budget"]))
    for line in v["lines"]:
        print("  %-16s £%8.2f  (%d items)" % (line["budget_line"], line["t"], line["n"]))
    r = money.monthly_rate(conn)
    if r:
        print("RUNNING £%.2f/month over %d months (target £%.0f-%.0f)"
              % (r["per_month"], r["months"], *r["target"]))
    print("Sinking fund for depreciation: £%.2f/month" % money.sinking_fund(conn))
    for w in money.end_of_life(conn):
        print("  ! %s" % w)


def cmd_stock(args):
    conn = open_db(args)
    rows = conn.execute("SELECT * FROM stock ORDER BY category, item").fetchall()
    for r in rows:
        flag = " <- reorder" if r["qty"] <= r["reorder_at"] else ""
        print("%-26s %8.6g %-8s %-12s %s%s" % (r["item"], r["qty"], r["unit"] or "",
                                               r["category"], r["location"], flag))
    for item, note in stock.seed_review(conn):
        print("  ! %s %s" % (item, note))


def cmd_shop(args):
    conn = open_db(args)
    today = date.today()
    refresh(conn, today, args.offline)
    lines = stock.shopping_list(conn, today)
    if not lines:
        print("Nothing needed.")
        return
    print("SHOPPING - next trip")
    by_vendor = {}
    for l in lines:
        by_vendor.setdefault(l["vendor"], []).append(l)
    total = 0.0
    for vendor, items in by_vendor.items():
        print("  %s" % vendor)
        for l in items:
            total += l["cost"]
            carry = ("%d barrow trip%s (+%s)" % (l["trips"], "" if l["trips"] == 1 else "s",
                                                 hm(l["barrow_minutes"]))
                     if l["trips"] else "carry")
            print("      %-24s x%-6g £%-7.2f %-14s %s"
                  % (l["item"], l["qty"], l["cost"], l["budget_line"], carry))
            print("        %s" % _c("; ".join(l["why"]), DIM))
    print("  Estimated £%.2f" % total)


def cmd_time(args):
    conn = open_db(args)
    if args.job:
        c = ledger.calibration(conn, job_id=args.job)
        print("Job %d calibration: %s" % (args.job, c if c else "not enough data"))
        return
    c = ledger.calibration(conn)
    print("Calibration factor: %s" % (c if c else "not enough data yet"))
    if c:
        print("  %s" % ("estimates were optimistic - real hours run higher" if c > 1.1
                        else "estimates were pessimistic" if c < 0.9 else "estimates are honest"))
    oh = ledger.overhead_ratio(conn)
    if oh:
        print("Overhead: %s per visit across %d visits (%d%% of all time)"
              % (hm(oh["per_visit"]), oh["visits"], round(oh["ratio"] * 100)))
    by_cat = ledger.calibration_by_category(conn)
    for cat, f in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print("  %-10s %.2f" % (cat, f))
    print("\nMONTH      PLANNED  ACTUAL  VAR")
    for m, row in ledger.hours_by_month(conn, args.year).items():
        if row["actual"] or row["planned"]:
            print("  %-8s %7s %7s %5s" % (date(2000, m, 1).strftime("%B"), row["planned"],
                                          row["actual"], row["variance"]))


def cmd_report(args):
    conn = open_db(args)
    r = money.report(conn, args.year)
    m, t, f = r["money"], r["time"], r["food"]
    print("YEAR %s - to %s" % (r["year"], date.today().strftime("%d %B")))
    print("MONEY")
    print("  Setup spend          £%9.2f   (planned £%.0f-%.0f)"
          % (m["setup"], *m["setup_budget"]))
    print("  Running costs        £%9.2f" % m["running"])
    print("  Depreciation         £%9.2f" % m["depreciation"])
    print("  True cost of the year £%8.2f" % m["true_cost"])
    print("  Asset book value     £%9.2f" % m["book_value"])
    print("  Sinking fund         £%9.2f / month" % m["sinking_fund_monthly"])
    print("TIME")
    print("  Hours logged          %9.1f   (planned %d)" % (t["hours"], t["planned"]))
    print("  Calibration factor    %9s" % (t["calibration"] or "-"))
    if t["overhead"]:
        print("  Overhead per visit    %9s min" % t["overhead"]["per_visit"])
    if t["split"]:
        print("  Split                 %9s" % " / ".join(
            "%s %d%%" % (k, round(100 * v / max(sum(t["split"]["tally"].values()), 1)))
            for k, v in t["split"]["tally"].items()))
    if t["winter_attendance"] is not None:
        print("  Winter attendance     %8d%%" % t["winter_attendance"])
    print("FOOD")
    print("  Harvested             %9.1f kg" % f["kg"])
    print("  Retail value         £%9.2f" % f["value"])
    if f["cost_per_kg"]:
        print("  Cost per kg          £%9.2f   year one carries all the setup" % f["cost_per_kg"])
        print("  Cost per kg excl setup £%7.2f" % f["cost_per_kg_excl_setup"])
    if r["failures"]:
        print("FAILURES")
        for fl in r["failures"]:
            print("  %-20s %d plantings" % (fl["r"], fl["c"]))
    mood = {k: v for k, v in r["mood"].items() if k != "_n"}
    if mood:
        print("MOOD")
        print("  " + "  ".join("%s %d%%" % (k.title(), v) for k, v in mood.items()))
    print("\nThe three lines that matter: calibration factor, winter attendance, mood split.")


def cmd_weather(args):
    conn = open_db(args)
    today = date.today()
    n, err = weather.refresh(conn, today, force=True)
    wx = weather.Weather(conn, today)
    if err:
        print("Fetch failed: %s (showing cache)" % err)
    else:
        print("Cached %d days" % n)
    print(wx.summary(today))
    print("  rain 48h %.1f mm   3d %.1f mm   7d %.1f mm"
          % (wx.rain_48h(), wx.rain_3d(), wx.rain_7d()))
    print("  soil workable: %s   frost risk: %s   gale: %s   slug night: %s"
          % (wx.soil_workable(), wx.frost_risk(), wx.gale_risk(), wx.slug_night()))
    first = min(wx.days) if wx.days else today.isoformat()
    print("  growing degree days over the cached window (%s to %s): %.0f"
          % (first, today, wx.gdd_total(first, today)))


def cmd_sun(args):
    conn = open_db(args)
    when = parse(args.date) if args.date else date.today()
    print("Sun at %s, lat %.2f°N" % (when, config.LAT))
    for hour in (8, 10, 12, 14, 16):
        print("  %02d:00  altitude %5.1f°  a 2 m structure throws %s"
              % (hour, sun.altitude_deg(when, hour),
                 ("%.1f m" % sun.shadow_length(2.0, sun.solar(sun.day_of_year(when), hour)[0]))
                 if sun.altitude_deg(when, hour) > 2 else "-"))
    print("  daylight %.1f hours" % sun.daylight_hours(when))
    print("\nSun hours by zone on %s:" % when)
    for z in sun.zones_from_db(conn):
        h = sun.zone_sun_hours(conn, z["id"], when)
        if h is not None:
            print("  %-22s %4.1f h" % (z["name"], h))
    for msg in sun.check_all_placements(conn):
        print("  ! %s" % msg)
    for msg in sun.check_crop_placement(conn, 4):
        print("  ! %s" % msg)


def cmd_weeds(args):
    conn = open_db(args)
    if args.observe is not None:
        weeds.log_observation(conn, date.today(), args.observe, zone_id=args.zone,
                              minutes=args.minutes)
        print("Logged observed pressure %.2f in %s" % (args.observe, args.zone))
        return
    print("WEED PRESSURE (predicted, corrected by observation)")
    for z in weeds.zone_pressure(conn):
        bar = "#" * int(round(z["pressure"] * 20))
        print("  %-24s %4.2f %s" % (z["name"], z["pressure"], bar))
    print("\nToday's 20 minutes, worst first:")
    for w in weeds.weeding_order(conn):
        print("  %-24s %s" % (w["name"], hm(w["minutes"])))


def cmd_rotation(args):
    conn = open_db(args)
    p = rotation.propose(conn)
    print("ROTATION - proposal for year %d" % p["year"])
    for a in p["assignments"]:
        print("  %-8s %s" % (a["zone"], a["name"]))
        for problem in a["problems"]:
            print("      ! %s" % problem)


def cmd_harvest(args):
    conn = open_db(args)
    v = ledger.current_visit(conn)
    conn.execute("INSERT INTO harvests(visit_id,date,crop,kg) VALUES(?,?,?,?)",
                 (v["id"] if v else None, parse(args.date or date.today()).isoformat(),
                  args.crop, args.kg))
    conn.commit()
    t = money.harvest_totals(conn)
    print("Logged %.2f kg %s. Year to date %.1f kg, retail value £%.2f"
          % (args.kg, args.crop, t["kg"], t["value"]))


def cmd_jobs(args):
    conn = open_db(args)
    today = date.today()
    wx, _ = refresh(conn, today, args.offline)
    rows = conn.execute(
        "SELECT r.id, r.due_date, r.status, j.title, j.owner, j.est_minutes "
        "FROM job_runs r JOIN jobs j ON j.id=r.job_id WHERE r.status IN ('due','blocked','doing') "
        "AND r.due_date <= ? ORDER BY r.due_date",
        ((today + timedelta(days=args.days)).isoformat(),)).fetchall()
    for r in rows:
        print("%4d  %s  %-40s %-7s %s" % (r["id"], r["due_date"], r["title"],
                                          r["owner"], hm(r["est_minutes"])))


def cmd_permission(args):
    conn = open_db(args)
    db.set_setting(conn, "structures_permission", not args.revoke)
    print("Structure permission %s. Shed and tunnel jobs are now %s."
          % ("logged" if not args.revoke else "revoked",
             "unblocked" if not args.revoke else "blocked"))


def cmd_ban(args):
    conn = open_db(args)
    db.set_setting(conn, "hosepipe_ban", not args.off)
    print("Hosepipe ban %s. Watering estimates now %d minutes."
          % ("ON" if not args.off else "off",
             config.BAN_MINUTES if not args.off else config.HOSE_MINUTES))


def cmd_passwd(args):
    conn = open_db(args)
    pw, generated = read_password(args.password)
    if generated:
        print("Generated password: %s" % pw)
    n = auth.set_password(conn, args.email or config.DEFAULT_EMAIL, pw)
    print("Password updated" if n else "No such user")


def cmd_user(args):
    conn = open_db(args)
    if args.rename:
        if not args.to:
            sys.exit("--rename needs --to NEW_EMAIL")
        n = auth.rename(conn, args.rename, args.to)
        print("Renamed %s to %s" % (args.rename, args.to) if n else "No such user")
        return
    if args.add:
        pw, generated = read_password(args.password)
        auth.create_user(conn, args.add, pw, name=args.name, role=args.role)
        print("Created %s" % args.add)
        if generated:
            print("Generated password: %s" % pw)
        return
    for u in conn.execute("SELECT email,name,role,last_login FROM users").fetchall():
        print("%-32s %-10s %s" % (u["email"], u["role"], u["last_login"] or "never"))


def cmd_serve(args):
    from . import server
    server.serve(host=args.host, port=args.port, db_path=args.db)


def cmd_export(args):
    conn = open_db(args)
    today = date.today()
    wx, _ = refresh(conn, today, args.offline)
    view = priority.plan_day(conn, today, wx)
    view["date"] = view["date"].isoformat()
    view["inspection"] = view["inspection"].isoformat() if view["inspection"] else None
    print(json.dumps(view, indent=2, default=str))


# --------------------------------------------------------------------- main

def build_parser():
    p = argparse.ArgumentParser("plot", description="Albert Village allotment")
    p.add_argument("--db", default=None, help="database file")
    p.add_argument("--offline", action="store_true", help="never touch the network")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create the database and seed it")
    s.add_argument("--email"), s.add_argument("--password"), s.add_argument("--name")
    s.add_argument("--season", help="first day of year one (default today)")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("today", help="the daily view")
    s.add_argument("--date"), s.add_argument("--limit", type=int, default=5)
    s.set_defaults(fn=cmd_today)

    s = sub.add_parser("week", help="the weekly plan")
    s.add_argument("--date")
    s.set_defaults(fn=cmd_week)

    s = sub.add_parser("jobs", help="everything due")
    s.add_argument("--days", type=int, default=14)
    s.set_defaults(fn=cmd_jobs)

    s = sub.add_parser("done", help="mark a job run done")
    s.add_argument("run_id", type=int), s.add_argument("minutes", type=int, nargs="?")
    s.add_argument("--notes"), s.add_argument("--who")
    s.set_defaults(fn=cmd_done)

    s = sub.add_parser("skip")
    s.add_argument("run_id", type=int), s.add_argument("--notes")
    s.set_defaults(fn=cmd_skip)

    s = sub.add_parser("arrive", help="start the visit clock")
    s.add_argument("--who", default="Both")
    s.set_defaults(fn=cmd_arrive)

    s = sub.add_parser("leave")
    s.add_argument("--mood", choices=ledger.MOODS), s.add_argument("--notes")
    s.set_defaults(fn=cmd_leave)

    s = sub.add_parser("start", help="time a job")
    s.add_argument("run_id", type=int)
    s.set_defaults(fn=cmd_start)

    s = sub.add_parser("stop")
    s.add_argument("run_id", type=int), s.add_argument("--notes")
    s.set_defaults(fn=cmd_stop)

    s = sub.add_parser("log", help="retrospective visit log")
    s.add_argument("minutes", type=int), s.add_argument("who", nargs="?", default="Both")
    s.add_argument("mood", nargs="?", choices=ledger.MOODS)
    s.add_argument("--notes"), s.add_argument("--jobs"), s.add_argument("--date")
    s.set_defaults(fn=cmd_log)

    s = sub.add_parser("spend")
    s.add_argument("amount", type=float), s.add_argument("vendor")
    s.add_argument("budget_line", choices=config.BUDGET_LINES)
    s.add_argument("--date"), s.add_argument("--notes")
    s.set_defaults(fn=cmd_spend)

    sub.add_parser("budget").set_defaults(fn=cmd_budget)
    sub.add_parser("stock").set_defaults(fn=cmd_stock)
    sub.add_parser("shop").set_defaults(fn=cmd_shop)
    sub.add_parser("weather").set_defaults(fn=cmd_weather)
    sub.add_parser("rotation").set_defaults(fn=cmd_rotation)
    sub.add_parser("export").set_defaults(fn=cmd_export)

    s = sub.add_parser("time", help="calibration report")
    s.add_argument("--job", type=int), s.add_argument("--year", type=int)
    s.set_defaults(fn=cmd_time)

    s = sub.add_parser("report")
    s.add_argument("--year", type=int)
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("sun")
    s.add_argument("--date")
    s.set_defaults(fn=cmd_sun)

    s = sub.add_parser("weeds")
    s.add_argument("--observe", type=float), s.add_argument("--zone")
    s.add_argument("--minutes", type=int)
    s.set_defaults(fn=cmd_weeds)

    s = sub.add_parser("harvest")
    s.add_argument("crop"), s.add_argument("kg", type=float), s.add_argument("--date")
    s.set_defaults(fn=cmd_harvest)

    s = sub.add_parser("permission", help="log written permission for structures")
    s.add_argument("--revoke", action="store_true")
    s.set_defaults(fn=cmd_permission)

    s = sub.add_parser("ban", help="hosepipe ban on or off")
    s.add_argument("--off", action="store_true")
    s.set_defaults(fn=cmd_ban)

    s = sub.add_parser("passwd")
    s.add_argument("--email"), s.add_argument("--password")
    s.set_defaults(fn=cmd_passwd)

    s = sub.add_parser("user")
    s.add_argument("--add"), s.add_argument("--password"), s.add_argument("--name")
    s.add_argument("--role", default="Both")
    s.add_argument("--rename", metavar="OLD_EMAIL", help="change an address")
    s.add_argument("--to", metavar="NEW_EMAIL")
    s.set_defaults(fn=cmd_user)

    s = sub.add_parser("serve", help="the web view, with login")
    s.add_argument("--host", default=os.environ.get("ALLOTMENT_HOST", "127.0.0.1"))
    s.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)))
    s.set_defaults(fn=cmd_serve)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except BrokenPipeError:          # `plot today | head` should not traceback
        try:
            sys.stdout.close()
        finally:
            os._exit(0)


if __name__ == "__main__":
    main()
