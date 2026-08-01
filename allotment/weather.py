"""Open-Meteo, cached once a day (§27). Never called per job evaluation.

Everything degrades gracefully offline: if the fetch fails you get the cache,
and if the cache is empty the weather rules simply stop firing rather than
guessing. A wrong `soil_workable` is worse than no answer.
"""

import json
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

from . import config, db
from .rules import parse

FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&daily=precipitation_sum,temperature_2m_max,temperature_2m_min,"
    "windspeed_10m_max,windgusts_10m_max,sunrise,sunset"
    "&timezone=Europe/London&forecast_days=7")
ARCHIVE_URL = (
    "https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
    "&start_date={start}&end_date={end}"
    "&daily=precipitation_sum,temperature_2m_max,temperature_2m_min,"
    "windspeed_10m_max,windgusts_10m_max,sunrise,sunset&timezone=Europe/London")


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "allotment/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _store(conn, payload, source):
    d = payload.get("daily") or {}
    days = d.get("time") or []
    now = datetime.now().isoformat(timespec="seconds")

    def col(name, i):
        v = d.get(name)
        return v[i] if v and i < len(v) and v[i] is not None else None

    for i, day in enumerate(days):
        conn.execute(
            "INSERT INTO weather_cache(date,rain_mm,temp_min,temp_max,wind_kph,gust_kph,"
            "sunrise,sunset,source,fetched) VALUES(?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(date) DO UPDATE SET rain_mm=excluded.rain_mm,"
            "temp_min=excluded.temp_min,temp_max=excluded.temp_max,wind_kph=excluded.wind_kph,"
            "gust_kph=excluded.gust_kph,sunrise=excluded.sunrise,sunset=excluded.sunset,"
            "source=excluded.source,fetched=excluded.fetched",
            (day, col("precipitation_sum", i), col("temperature_2m_min", i),
             col("temperature_2m_max", i), col("windspeed_10m_max", i),
             col("windgusts_10m_max", i), col("sunrise", i), col("sunset", i), source, now))
    conn.commit()
    return len(days)


def refresh(conn, today=None, force=False, history_days=14):
    """One call a day, cached. Returns (rows_written, error_or_None)."""
    today = parse(today or date.today())
    last = db.get_setting(conn, "weather_fetched")
    if last == today.isoformat() and not force:
        return 0, None
    n = 0
    try:
        n += _store(conn, _get(FORECAST_URL.format(lat=config.LAT, lon=config.LON)), "forecast")
        start = (today - timedelta(days=history_days)).isoformat()
        endh = (today - timedelta(days=1)).isoformat()
        n += _store(conn, _get(ARCHIVE_URL.format(lat=config.LAT, lon=config.LON,
                                                 start=start, end=endh)), "archive")
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        return n, "%s: %s" % (type(e).__name__, e)
    db.set_setting(conn, "weather_fetched", today.isoformat())
    return n, None


class Weather:
    """Derived values the rules need (§27). Reads the cache, never the network."""

    def __init__(self, conn, today=None):
        self.conn = conn
        self.today = parse(today or date.today())
        self.days = {r["date"]: dict(r) for r in
                     conn.execute("SELECT * FROM weather_cache").fetchall()}
        self.hosepipe_ban = bool(db.get_setting(conn, "hosepipe_ban", False))
        self.butt_level = float(db.get_setting(conn, "butt_level_pct", 100))
        keys = sorted(self.days) or [self.today.isoformat()]
        self.horizon_start = self.today
        self.horizon_end = max(parse(keys[-1]), self.today)

    # -- raw -----------------------------------------------------------------
    def has(self, d=None):
        return parse(d or self.today).isoformat() in self.days

    def day(self, d=None):
        return self.days.get(parse(d or self.today).isoformat(), {})

    def rain(self, d=None):
        return self.day(d).get("rain_mm") or 0.0

    def wind(self, d=None):
        row = self.day(d)
        return row.get("gust_kph") or row.get("wind_kph") or 0.0

    def tmax(self, d=None):
        return self.day(d).get("temp_max")

    def tmin(self, d=None):
        return self.day(d).get("temp_min")

    # -- rolling sums --------------------------------------------------------
    def _sum(self, d, days, include_today):
        d = parse(d or self.today)
        total, seen = 0.0, 0
        rng = range(0 if include_today else 1, days + (0 if include_today else 1))
        for i in rng:
            k = (d - timedelta(days=i)).isoformat()
            if k in self.days:
                total += self.days[k].get("rain_mm") or 0.0
                seen += 1
        return total if seen else None

    def rain_48h(self, d=None):
        return self._sum(d, 2, True) or 0.0

    def rain_3d(self, d=None):
        return self._sum(d, 3, True) or 0.0

    def rain_7d(self, d=None):
        return self._sum(d, 7, True) or 0.0

    def known_48h(self, d=None):
        return self._sum(d, 2, True) is not None

    # -- derived flags -------------------------------------------------------
    def soil_workable(self, d=None):
        """The clay block. Unknown weather is treated as workable, not blocked -
        a false block stops you working for no reason."""
        if not self.known_48h(d):
            return True
        return self.rain_48h(d) < config.CLAY_BLOCK_MM

    def dry_3d(self, d=None):
        return self.has(d) and self.rain_3d(d) < config.RAIN_3D_DRY_MM

    def frost_risk(self, d=None):
        d = parse(d or self.today)
        for i in (0, 1, 2):
            t = self.tmin(d + timedelta(days=i))
            if t is not None and t < config.FROST_MIN_C:
                return True
        return False

    def gale_risk(self, d=None):
        return self.wind(d) > config.GALE_GUST_KPH

    def slug_night(self, d=None):
        d = parse(d or self.today)
        y = (d - timedelta(days=1)).isoformat()
        return (self.days.get(y, {}).get("rain_mm") or 0.0) >= 1.0

    def warm_day(self, d=None):
        t = self.tmax(d)
        return t is not None and t > config.VENTILATE_MAX_C

    def butts_low(self, d=None):
        d = parse(d or self.today)
        tap_on = d.month not in config.TAP_OFF_MONTHS
        return tap_on and self.butt_level < 50

    def rain_due_24h(self, d=None):
        d = parse(d or self.today)
        return (self.days.get((d + timedelta(days=1)).isoformat(), {}).get("rain_mm") or 0.0) >= 2.0

    def gdd(self, d=None):
        row = self.day(d)
        tx, tn = row.get("temp_max"), row.get("temp_min")
        if tx is None or tn is None:
            return 0.0
        return max(0.0, (tx + tn) / 2.0 - config.GDD_BASE)

    def gdd_total(self, start, end=None):
        start, end = parse(start), parse(end or self.today)
        t, cur = 0.0, start
        while cur <= end:
            t += self.gdd(cur)
            cur += timedelta(days=1)
        return t

    def condition(self, name, d=None):
        if name == "always":
            return True
        fn = getattr(self, name, None)
        return bool(fn(d)) if callable(fn) else False

    # -- watering ------------------------------------------------------------
    def watering_minutes(self, base=None):
        """§11 - a hosepipe ban turns a 5 minute job into a 20 minute one."""
        if self.hosepipe_ban:
            return config.BAN_MINUTES
        return base if base is not None else config.HOSE_MINUTES

    def tap_on(self, d=None):
        return parse(d or self.today).month not in config.TAP_OFF_MONTHS

    def summary(self, d=None):
        d = parse(d or self.today)
        if not self.has(d):
            return "No weather cached - run `plot weather` when you have a connection"
        return "Rain 3d: %.0fmm   Max %.0f°C   Min %.0f°C   Soil: %s" % (
            self.rain_3d(d), self.tmax(d) or 0, self.tmin(d) or 0,
            "workable" if self.soil_workable(d) else "TOO WET")


def suitability(job, wx, d):
    """§28 weather suitability by job type, 0 to 1.4. Above 1 means today is a
    good day for this specifically; 0 means don't."""
    cat = job["category"]
    title = (job["title"] or "").lower()
    if not wx.has(d):
        return 1.0
    if cat in config.SOIL_CATEGORIES:
        if not wx.soil_workable(d):
            return 0.0
        dry_behind = wx.rain_48h(d) < 2.0
        return 1.3 if dry_behind else 0.9
    if cat == "sow":
        if wx.frost_risk(d):
            return 0.2
        return 1.3 if wx.rain_due_24h(d) else 1.0
    if cat == "plant":
        if wx.frost_risk(d):
            return 0.0
        if (wx.tmax(d) or 0) > 26:
            return 0.4
        return 1.2
    if cat == "build":
        limit = (config.POLYTHENE_MAX_WIND_KPH if "polythene" in title
                 else config.STRUCTURE_MAX_WIND_KPH)
        return 0.0 if wx.wind(d) > limit else 1.1
    if cat == "harvest":
        return 0.7 if wx.rain(d) > 3 else 1.2
    if cat == "tend":
        if "water" in title:
            if "tunnel" in title:
                return 1.2                      # never gets rain, ever
            return 0.2 if wx.rain_due_24h(d) else (1.3 if wx.dry_3d(d) else 0.6)
        if "slug" in title:
            return 1.4 if wx.slug_night(d) else 0.3
        if "weed" in title:
            if wx.rain_48h(d) > config.CLAY_BLOCK_MM:
                return 0.5
            return 1.2 if 1.0 <= wx.rain_3d(d) <= 12 else 1.0
        return 1.0
    return 1.0                                   # compost, mulch, admin: anything
