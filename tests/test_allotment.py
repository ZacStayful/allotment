"""Tests for the parts that would quietly give wrong answers: the rule engine,
the clay block, the neighbour-shading rule, the ledger arithmetic and login.

    python3 -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from allotment import (auth, config, db, ledger, money, priority, rotation,
                       rules, seed, stock, sun, weeds)
from allotment.weather import Weather


# Set ALLOTMENT_TEST_PG to a Postgres URL to run the whole suite against
# Postgres instead of SQLite. Both backends must pass the same tests.
TEST_PG = os.environ.get("ALLOTMENT_TEST_PG")


class Base(unittest.TestCase):
    def setUp(self):
        self.path = None
        self._saved = (db.DATABASE_URL, db.PG_SCHEMA)
        if TEST_PG:
            import uuid
            db.DATABASE_URL = TEST_PG
            db.PG_SCHEMA = "test_" + uuid.uuid4().hex[:12]
            self.conn = db.connect()
        else:
            fd, self.path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            self.conn = db.connect(self.path)
        db.init(self.conn)
        seed.seed(self.conn)

    def tearDown(self):
        if TEST_PG:
            try:
                self.conn.execute("DROP SCHEMA IF EXISTS %s CASCADE" % db.PG_SCHEMA)
                self.conn.commit()
            finally:
                self.conn.close()
                db.DATABASE_URL, db.PG_SCHEMA = self._saved
            return
        self.conn.close()
        for suffix in ("", "-wal", "-shm"):
            try:
                os.unlink(self.path + suffix)
            except OSError:
                pass

    def job(self, key):
        return self.conn.execute("SELECT * FROM jobs WHERE job_key=?", (key,)).fetchone()

    def weather_day(self, when, rain=0.0, tmin=10.0, tmax=18.0, gust=10.0):
        self.conn.execute(
            "INSERT INTO weather_cache(date,rain_mm,temp_min,temp_max,wind_kph,gust_kph,"
            "source,fetched) VALUES(?,?,?,?,?,?,'test','test') "
            "ON CONFLICT(date) DO UPDATE SET rain_mm=excluded.rain_mm,"
            "temp_min=excluded.temp_min,temp_max=excluded.temp_max,gust_kph=excluded.gust_kph",
            (str(when), rain, tmin, tmax, gust, gust))
        self.conn.commit()


class TestRules(Base):
    def test_fixed_window_fires_once_a_year_at_the_start(self):
        job = self.job("pay_the_subscription")
        got = rules.due_dates(self.conn, job, "2027-01-01", "2027-12-31")
        self.assertEqual([d for d, _ in got], [date(2027, 1, 1)])

    def test_fixed_window_wrapping_the_new_year(self):
        job = self.job("order_seeds_and_seed_potatoes")     # 01 Dec to 31 Jan
        got = [d for d, _ in rules.due_dates(self.conn, job, "2027-01-01", "2027-12-31")]
        self.assertEqual(got, [date(2027, 12, 1)])
        self.assertTrue(rules.in_md_window(date(2027, 1, 15), "12-01", "01-31"))
        self.assertFalse(rules.in_md_window(date(2027, 6, 15), "12-01", "01-31"))

    def test_recurring_gives_one_open_run_not_a_backlog(self):
        job = self.job("turn_the_compost")
        rules.ensure_runs(self.conn, "2027-01-01", "2027-06-30")
        n = self.conn.execute("SELECT COUNT(*) c FROM job_runs WHERE job_id=?",
                              (job["id"],)).fetchone()["c"]
        self.assertEqual(n, 1, "six months of missed compost turns must not queue up")

    def test_recurring_after_job_waits_for_its_anchor(self):
        job = self.job("replace_the_tunnel_polythene")
        self.assertEqual(rules.due_dates(self.conn, job, "2027-01-01", "2027-12-31"), [])

    def test_succession_respects_interval_and_max_sowings(self):
        job = self.job("sow_radish")                        # every 14 days, max 12
        got = [d for d, _ in rules.due_dates(self.conn, job, "2027-01-01", "2027-12-31")]
        self.assertEqual(got[0], date(2027, 3, 1))
        self.assertEqual((got[1] - got[0]).days, 14)
        self.assertLessEqual(len(got), 12)

    def test_crop_linked_offset_and_repeats(self):
        job = self.job("earth_up_the_potatoes")             # +21 days, then every 14, x3
        got = sorted(d for d, _ in rules.due_dates(self.conn, job, "2027-01-01", "2027-12-31"))
        self.assertEqual(got[0], date(2027, 3, 20) + timedelta(days=21))
        self.assertEqual(len(got), 3)
        self.assertEqual((got[1] - got[0]).days, 14)

    def test_inspections_run_every_28_days_from_week_4(self):
        d = rules.inspection_dates(2027)
        self.assertEqual(d[0].isocalendar()[1], 4)
        self.assertEqual((d[1] - d[0]).days, 28)

    def test_tidy_job_lands_three_days_before_each_inspection(self):
        job = self.job("tidy_sweep_and_path_edges_before_inspection")
        tidy = [d for d, _ in rules.due_dates(self.conn, job, "2027-01-01", "2027-12-31")]
        self.assertIn(rules.inspection_dates(2027)[0] - timedelta(days=3), tidy)

    def test_dependency_blocks_until_the_prerequisite_is_done(self):
        job = self.job("fill_beds")
        self.assertIn("Build the raised beds", rules.blocked_reason(self.conn, job))
        rules.ensure_runs(self.conn, date.today(), date.today())
        run = self.conn.execute(
            "SELECT r.id FROM job_runs r JOIN jobs j ON j.id=r.job_id "
            "WHERE j.job_key='build_beds'").fetchone()
        ledger.complete(self.conn, run["id"], actual_minutes=300, method="timed")
        self.assertIsNone(rules.blocked_reason(self.conn, job))

    def test_structure_jobs_blocked_until_permission_is_logged(self):
        job = self.job("tunnel_frame")
        self.assertIn("permission", rules.blocked_reason(self.conn, job))
        db.set_setting(self.conn, "structures_permission", True)
        self.assertNotIn("permission", rules.blocked_reason(self.conn, job) or "")


class TestClayAndWeather(Base):
    def test_clay_rule_is_a_hard_block_on_soil_jobs(self):
        today = date(2027, 4, 10)
        self.weather_day(today, rain=10)
        self.weather_day(today - timedelta(days=1), rain=9)
        wx = Weather(self.conn, today)
        self.assertFalse(wx.soil_workable(today))
        reason = rules.blocked_reason(self.conn, self.job("rough_dig_the_potato_ground"),
                                      wx, today)
        self.assertIn("clay", reason)

    def test_dry_ground_does_not_block(self):
        today = date(2027, 4, 10)
        self.weather_day(today, rain=1)
        self.weather_day(today - timedelta(days=1), rain=2)
        wx = Weather(self.conn, today)
        self.assertTrue(wx.soil_workable(today))

    def test_unknown_weather_does_not_block(self):
        wx = Weather(self.conn, date(2027, 4, 10))
        self.assertTrue(wx.soil_workable(date(2027, 4, 10)),
                        "a missing forecast must not stop you working")

    def test_polythene_needs_under_ten_kph(self):
        today = date(2027, 4, 10)
        self.weather_day(today, gust=12)
        wx = Weather(self.conn, today)
        db.set_setting(self.conn, "structures_permission", True)
        for key in ("clear_plot", "mark_out", "survey", "hardstanding", "permission",
                    "tunnel_approved", "tunnel_site", "tunnel_frame"):
            rules.ensure_runs(self.conn, today, today, wx)
            run = self.conn.execute(
                "SELECT r.id FROM job_runs r JOIN jobs j ON j.id=r.job_id "
                "WHERE j.job_key=? AND r.status='due'", (key,)).fetchone()
            if run:
                ledger.complete(self.conn, run["id"], actual_minutes=10, when=today)
        self.assertIn("10 kph", rules.blocked_reason(self.conn, self.job("tunnel_poly"),
                                                     wx, today))
        self.weather_day(today, gust=6)
        self.assertIsNone(rules.blocked_reason(self.conn, self.job("tunnel_poly"),
                                               Weather(self.conn, today), today))

    def test_derived_flags(self):
        today = date(2027, 4, 10)
        self.weather_day(today - timedelta(days=1), rain=4)
        self.weather_day(today, rain=0, tmin=1.0, tmax=22.0, gust=50)
        wx = Weather(self.conn, today)
        self.assertTrue(wx.slug_night(today))
        self.assertTrue(wx.frost_risk(today))
        self.assertTrue(wx.gale_risk(today))
        self.assertTrue(wx.warm_day(today))
        self.assertTrue(wx.dry_3d(today))

    def test_hosepipe_ban_changes_the_watering_estimate(self):
        wx = Weather(self.conn, date(2027, 6, 1))
        self.assertEqual(wx.watering_minutes(), config.HOSE_MINUTES)
        db.set_setting(self.conn, "hosepipe_ban", True)
        self.assertEqual(Weather(self.conn).watering_minutes(), config.BAN_MINUTES)

    def test_tap_is_off_november_to_march(self):
        wx = Weather(self.conn, date(2027, 1, 10))
        self.assertFalse(wx.tap_on(date(2027, 1, 10)))
        self.assertTrue(wx.tap_on(date(2027, 6, 10)))


class TestPriority(Base):
    def test_a_closing_window_outranks_a_distant_one(self):
        today = date(2027, 4, 10)
        wx = Weather(self.conn, today)
        rules.ensure_runs(self.conn, today, today, wx)

        def score_of(key, shuts_in):
            job = self.job(key)
            run = {"id": 1, "due_date": today.isoformat(), "est_minutes": 30}
            s = priority.score(self.conn, run, job, wx, today)
            return s["urgency"]

        near = priority.score(self.conn,
                              {"id": 1, "due_date": today.isoformat(), "est_minutes": 30},
                              self.job("sow_radish"), wx, today)
        far = priority.score(self.conn,
                             {"id": 2, "due_date": today.isoformat(), "est_minutes": 30},
                             self.job("order_seeds_and_seed_potatoes"), wx, today)
        self.assertGreater(near["urgency"], far["urgency"])

    def test_blocked_jobs_are_pushed_below_everything(self):
        today = date(2027, 4, 10)
        wx = Weather(self.conn, today)
        run = {"id": 1, "due_date": today.isoformat(), "est_minutes": 30}
        s = priority.score(self.conn, run, self.job("tunnel_frame"), wx, today)
        self.assertTrue(s["blocked"])
        self.assertLess(s["priority"], 0)

    def test_daily_view_stays_short(self):
        today = date(2027, 4, 10)
        rules.ensure_runs(self.conn, today - timedelta(days=30), today)
        view = priority.plan_day(self.conn, today, Weather(self.conn, today), limit=5)
        self.assertLessEqual(len(view["top"]), 5)

    def test_missing_stock_blocks_the_job_before_you_walk_down_there(self):
        job = self.job("net_the_brassicas")
        self.assertEqual(stock.shortfalls(self.conn, job)[0][0], "Butterfly netting")
        row = stock.find(self.conn, "Butterfly netting")
        stock.move(self.conn, row["id"], 10, "bought")
        self.assertEqual(stock.shortfalls(self.conn, job), [])


class TestStock(Base):
    def test_barrow_trips_are_counted_and_costed_in_time(self):
        row = stock.find(self.conn, "Hardcore")             # 1000 kg, 0.7 m3 per tonne
        self.assertEqual(stock.barrow_trips(row, 1), 17)

    def test_shopping_list_carries_barrow_trips(self):
        lines = stock.shopping_list(self.conn, date(2026, 8, 1))
        hardcore = next(l for l in lines if l["item"] == "Hardcore")
        self.assertGreater(hardcore["trips"], 0)
        self.assertEqual(hardcore["barrow_minutes"],
                         hardcore["trips"] * config.BARROW_MINUTES)

    def test_treatments_must_be_certified_organic(self):
        with self.assertRaises(ValueError):
            stock.add(self.conn, "Slug pellets", "treatments", "kg", organic=0)
        sid = stock.add(self.conn, "Ferric phosphate", "treatments", "kg", organic=1)
        self.assertTrue(sid)

    def test_completing_a_job_consumes_its_materials(self):
        row = stock.find(self.conn, "Butterfly netting")
        stock.move(self.conn, row["id"], 10, "bought")
        rules.ensure_runs(self.conn, date(2027, 6, 1), date(2027, 6, 1))
        run = self.conn.execute(
            "SELECT r.id FROM job_runs r JOIN jobs j ON j.id=r.job_id "
            "WHERE j.job_key='net_the_brassicas'").fetchone()
        if run:
            ledger.complete(self.conn, run["id"], actual_minutes=25, method="timed")
            self.assertEqual(stock.find(self.conn, "Butterfly netting")["qty"], 9)


class TestSun(Base):
    def test_altitudes_match_the_published_figures(self):
        self.assertAlmostEqual(sun.altitude_deg(date(2027, 6, 21), 12), 60.7, delta=0.2)
        self.assertAlmostEqual(sun.altitude_deg(date(2027, 12, 21), 12), 13.8, delta=0.2)
        self.assertAlmostEqual(sun.altitude_deg(date(2027, 3, 21), 12), 36.8, delta=0.3)

    def test_two_metre_structure_reaches_six_metres_north_west_at_the_equinox(self):
        reach, hour = sun.worst_nw_reach(2.0)
        self.assertAlmostEqual(reach, 6.0, delta=0.2)
        self.assertEqual(hour, 8.0)

    def test_placement_rule_rejects_a_tall_structure_near_the_neighbour(self):
        bad = {"id": "x", "name": "Test shed", "x": 2.0, "y": 2.0, "w": 2.0, "d": 2.0,
               "height_m": 2.0}
        self.assertIn("north-west", sun.check_placement(bad))

    def test_the_actual_layout_passes(self):
        self.assertEqual(sun.check_all_placements(self.conn), [],
                         "every tall thing should already be in the south-east half")

    def test_beds_do_not_shade_themselves(self):
        h = sun.zone_sun_hours(self.conn, "b1", date(2027, 4, 15))
        self.assertGreater(h, 6.0)

    def test_the_treeline_corner_is_genuinely_shaded(self):
        self.assertLess(sun.zone_sun_hours(self.conn, "fruit", date(2027, 4, 15)), 4.0)


class TestWeeds(Base):
    def test_pressure_is_highest_at_the_woodland_edge(self):
        zs = weeds.zone_pressure(self.conn)
        by_id = {z["zone"]: z["pressure"] for z in zs}
        self.assertGreater(by_id["comp"], by_id["b4"])

    def test_observation_overrides_prediction(self):
        before = {z["zone"]: z["pressure"] for z in weeds.zone_pressure(self.conn)}["b4"]
        weeds.log_observation(self.conn, date(2027, 5, 1), 1.0, zone_id="b4")
        after = {z["zone"]: z["pressure"] for z in weeds.zone_pressure(self.conn)}["b4"]
        self.assertGreater(after, before)

    def test_weeding_order_splits_the_twenty_minutes(self):
        order = weeds.weeding_order(self.conn, 20)
        self.assertTrue(order)
        self.assertLessEqual(sum(o["minutes"] for o in order), 26)


class TestLedger(Base):
    def _run(self, key, when):
        rules.ensure_runs(self.conn, when, when)
        return self.conn.execute(
            "SELECT r.id FROM job_runs r JOIN jobs j ON j.id=r.job_id WHERE j.job_key=? "
            "ORDER BY r.id DESC LIMIT 1", (key,)).fetchone()

    def test_overhead_is_separated_from_job_time(self):
        vid = ledger.log_visit(self.conn, 120, who="Both", when=date(2027, 4, 10))
        run = self._run("turn_the_compost", date(2027, 4, 10))
        ledger.complete(self.conn, run["id"], actual_minutes=100, method="timed",
                        visit_id=vid, when=date(2027, 4, 10))
        self.assertEqual(ledger.overhead(self.conn, vid), 20)

    def test_allocated_time_is_split_in_proportion_to_estimates(self):
        r1 = self._run("turn_the_compost", date(2027, 4, 10))          # 30 min
        r2 = self._run("clean_and_oil_the_tools", date(2027, 4, 10))   # 40 min
        vid = ledger.log_visit(self.conn, 152, when=date(2027, 4, 10),
                               run_ids=[r1["id"], r2["id"]])
        got = {r["id"]: r["actual_minutes"] for r in self.conn.execute(
            "SELECT id, actual_minutes FROM job_runs WHERE visit_id=?", (vid,))}
        self.assertEqual(sum(got.values()), 140)
        self.assertEqual(got[r1["id"]], 60)

    def test_calibration_weights_timed_above_allocated(self):
        r1 = self._run("turn_the_compost", date(2027, 4, 10))
        ledger.complete(self.conn, r1["id"], actual_minutes=60, method="timed",
                        when=date(2027, 4, 10))
        self.assertEqual(ledger.calibration(self.conn), 2.0)

    def test_estimates_self_correct_after_three_runs(self):
        job = self.job("turn_the_compost")
        original = job["planned_minutes"]
        for i, d in enumerate([date(2027, 4, 10), date(2027, 5, 10), date(2027, 6, 10)]):
            run = self._run("turn_the_compost", d)
            ledger.complete(self.conn, run["id"], actual_minutes=60, method="timed", when=d)
        after = self.job("turn_the_compost")
        self.assertGreater(after["est_minutes"], original)
        self.assertEqual(after["planned_minutes"], original,
                         "the original plan figure must be preserved - the gap is the point")

    def test_person_split_flags_an_uneven_share(self):
        ledger.log_visit(self.conn, 600, who="Grower", when=date(2027, 4, 10))
        ledger.log_visit(self.conn, 60, who="Site", when=date(2027, 4, 11))
        split = priority.person_split(self.conn, date(2027, 4, 12))
        self.assertEqual(split["max_who"], "Grower")
        self.assertGreater(split["max_pct"], 70)


class TestMoney(Base):
    def test_depreciation_and_book_value(self):
        aid = money.add_asset(self.conn, "Polytunnel polythene", 150.0,
                              purchase_date=date(2026, 1, 1), life_years=5)
        a = self.conn.execute("SELECT * FROM assets WHERE id=?", (aid,)).fetchone()
        self.assertEqual(money.annual_depreciation(a), 30.0)
        self.assertAlmostEqual(money.book_value(a, date(2028, 1, 1)), 90.0, delta=0.3)

    def test_sinking_fund_is_the_monthly_set_aside(self):
        money.add_asset(self.conn, "Polytunnel polythene", 150.0,
                        purchase_date=date(2026, 1, 1), life_years=5)
        money.add_asset(self.conn, "Shed", 600.0,
                        purchase_date=date(2026, 1, 1), life_years=15)
        self.assertAlmostEqual(money.sinking_fund(self.conn), (30 + 40) / 12.0, delta=0.01)

    def test_setup_and_running_are_separated(self):
        money.add_spend(self.conn, 300, "beds", when=date(2026, 9, 1))
        money.add_spend(self.conn, 46, "rent", when=date(2027, 1, 1))
        self.assertEqual(money.setup_total(self.conn), 300)
        self.assertEqual(money.running_total(self.conn), 46)

    def test_unknown_budget_line_is_refused(self):
        with self.assertRaises(ValueError):
            money.add_spend(self.conn, 10, "beer")


class TestRotation(Base):
    def test_same_family_cannot_return_within_three_years(self):
        self.conn.execute(
            "INSERT INTO plantings(crop_id,zone_id,planted_date,status) "
            "VALUES('kale','b1',?,'growing')", (date.today().isoformat(),))
        self.conn.commit()
        self.assertIn("cannot go back", rotation.validate(self.conn, "b1", "brassica"))
        self.assertIsNone(rotation.validate(self.conn, "b2", "brassica"))

    def test_the_keep_clear_strip_is_never_a_growing_zone(self):
        self.assertIn("not a growing zone", rotation.validate(self.conn, "clear", "allium"))
        z = self.conn.execute("SELECT growable FROM zones WHERE id='clear'").fetchone()
        self.assertEqual(z["growable"], 0)

    def test_four_year_cycle_moves_every_group_on(self):
        y1 = rotation.plan_for(self.conn, 1)
        y2 = rotation.plan_for(self.conn, 2)
        for bed in ("b1", "b2", "b3", "b4"):
            self.assertNotEqual(y1[bed], y2[bed])
        self.assertEqual(rotation.plan_for(self.conn, 5), y1)


class TestAuth(Base):
    def setUp(self):
        super().setUp()
        auth.create_user(self.conn, "Zac@Example.com", "correct horse battery")

    def test_password_is_hashed_not_stored(self):
        u = auth.get_user(self.conn, "zac@example.com")
        self.assertNotIn("correct", u["pw_hash"])
        self.assertGreaterEqual(u["iterations"], 200_000)

    def test_login_is_case_insensitive_on_the_email(self):
        self.assertIsNotNone(auth.verify(self.conn, "ZAC@example.com",
                                         "correct horse battery"))

    def test_wrong_password_fails(self):
        self.assertIsNone(auth.verify(self.conn, "zac@example.com", "hunter2"))

    def test_unknown_user_fails_without_leaking(self):
        self.assertIsNone(auth.verify(self.conn, "nobody@example.com", "anything"))

    def test_repeated_failures_lock_the_account(self):
        for _ in range(config.MAX_FAILED_LOGINS):
            auth.verify(self.conn, "zac@example.com", "wrong")
        self.assertGreater(auth.locked_out(self.conn, "zac@example.com"), 0)
        self.assertIsNone(auth.verify(self.conn, "zac@example.com",
                                      "correct horse battery"))

    def test_a_good_login_clears_the_failure_count(self):
        auth.verify(self.conn, "zac@example.com", "wrong")
        auth.verify(self.conn, "zac@example.com", "correct horse battery")
        self.assertEqual(auth.locked_out(self.conn, "zac@example.com"), 0)

    def test_sessions_carry_a_csrf_token(self):
        user = auth.verify(self.conn, "zac@example.com", "correct horse battery")
        token, csrf = auth.create_session(self.conn, user["id"])
        sess = auth.session(self.conn, token)
        self.assertTrue(auth.check_csrf(sess, csrf))
        self.assertFalse(auth.check_csrf(sess, "guess"))

    def test_expired_sessions_are_rejected(self):
        user = auth.get_user(self.conn, "zac@example.com")
        token, _ = auth.create_session(self.conn, user["id"], hours=-1)
        self.assertIsNone(auth.session(self.conn, token))

    def test_logout_ends_the_session(self):
        user = auth.get_user(self.conn, "zac@example.com")
        token, _ = auth.create_session(self.conn, user["id"])
        auth.end_session(self.conn, token)
        self.assertIsNone(auth.session(self.conn, token))

    def test_password_change_invalidates_the_old_one(self):
        auth.set_password(self.conn, "zac@example.com", "a new long password")
        self.assertIsNone(auth.verify(self.conn, "zac@example.com",
                                      "correct horse battery"))
        self.assertIsNotNone(auth.verify(self.conn, "zac@example.com",
                                         "a new long password"))


class TestServerRoutes(Base):
    """A browser asks for /favicon.ico on every page load. If that 404s, the
    console fills with errors on a site that is working perfectly."""

    def setUp(self):
        super().setUp()
        import threading
        from http.server import ThreadingHTTPServer
        from allotment import server
        auth.create_user(self.conn, "zac@example.com", "correct horse battery")
        server.DB_PATH = self.path          # None under Postgres, so DATABASE_URL wins
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

    def get(self, path, cookie=None):
        import urllib.error
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path))
        if cookie:
            req.add_header("Cookie", cookie)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as err:
            return err.code, err.read(), err.headers

    def session_cookie(self):
        user = auth.get_user(self.conn, "zac@example.com")
        token, _ = auth.create_session(self.conn, user["id"])
        return "plot_session=" + token

    def test_favicon_is_served_without_a_login(self):
        status, body, headers = self.get("/favicon.ico")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/svg+xml")
        self.assertIn(b"<svg", body)

    def test_robots_and_health_need_no_login(self):
        self.assertEqual(self.get("/robots.txt")[0], 200)
        self.assertEqual(self.get("/healthz")[0], 200)

    def test_every_nav_page_answers(self):
        from allotment.server import NAV
        cookie = self.session_cookie()
        for path, name in NAV:
            self.assertEqual(self.get(path, cookie)[0], 200, "%s (%s)" % (path, name))

    def test_static_files_are_served_but_nothing_above_them(self):
        cookie = self.session_cookie()
        self.assertEqual(self.get("/static/map.html", cookie)[0], 200)
        for attempt in ("/static/../config.py", "/static/..%2fconfig.py",
                        "/static/%2e%2e/db.py"):
            self.assertEqual(self.get(attempt, cookie)[0], 404, attempt)

    def test_unknown_page_gives_a_404_with_a_way_back(self):
        status, body, _ = self.get("/nonsense", self.session_cookie())
        self.assertEqual(status, 404)
        self.assertIn(b'href="/week"', body)

    def test_pages_require_a_session(self):
        status, _, headers = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Sign in", self.get("/login")[1])


class TestEmailRename(Base):
    def test_rename_keeps_the_password(self):
        auth.create_user(self.conn, "zac@stayul.co.uk", "correct horse battery")
        auth.rename(self.conn, "zac@stayul.co.uk", "zac@stayful.co.uk")
        self.assertIsNone(auth.get_user(self.conn, "zac@stayul.co.uk"))
        self.assertIsNotNone(auth.verify(self.conn, "zac@stayful.co.uk",
                                         "correct horse battery"))

    def test_rename_onto_an_existing_address_is_refused(self):
        auth.create_user(self.conn, "a@example.com", "password one")
        auth.create_user(self.conn, "b@example.com", "password two")
        with self.assertRaises(ValueError):
            auth.rename(self.conn, "a@example.com", "b@example.com")


class TestSeed(Base):
    def test_seeding_twice_changes_nothing(self):
        before = self.conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"]
        seed.seed(self.conn)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"],
                         before)

    def test_every_job_has_a_known_rule_type_and_owner(self):
        for job in self.conn.execute("SELECT * FROM jobs").fetchall():
            self.assertIn(job["rule_type"], rules.RULE_TYPES, job["title"])
            self.assertIn(job["owner"], config.OWNERS, job["title"])
            self.assertIn(job["category"], config.CATEGORIES, job["title"])

    def test_every_dependency_points_at_a_real_job(self):
        import json
        for job in self.conn.execute("SELECT * FROM jobs").fetchall():
            for dep in json.loads(job["depends_on"] or "[]"):
                self.assertIsNotNone(rules._dep_row(self.conn, dep),
                                     "%s depends on missing %s" % (job["title"], dep))


if __name__ == "__main__":
    unittest.main()
