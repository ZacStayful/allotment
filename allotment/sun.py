"""Real solar geometry for 52.76°N (§21) and the neighbour-shading rule (§29).

Verified against known values: 60.7° at midsummer noon, 13.8° at midwinter noon,
36.8° at the equinox. Deterministic arithmetic over a 20 x 18 grid - no
dependencies, no mapping library.

Coordinates are the V2 plot frame used by the map: x runs across the plot from
the fenced neighbour (x = 0), y runs from the woodland edge (y = 0) down to the
gate (y = PLOT_D). Up the plot - decreasing y - is the 070° bearing, so a shadow
cast toward the top of the drawing has a negative y component.
"""

import math
from datetime import date

from . import config
from .rules import parse

GRID = 0.6
GNX = int(math.ceil(config.PLOT_W / GRID))
GNY = int(math.ceil(config.PLOT_D / GRID))
GN = GNX          # kept for callers that only ever indexed the x axis
# The woodland runs the full length of the front face, off-plot beyond y = 0,
# and overhangs both ends. Height is assumed, not measured (config.CANOPY_M).
WOODLAND = {"x": -3.0, "y": -1.5, "w": config.PLOT_W + 6.0, "d": 1.5,
            "height_m": config.CANOPY_M}
MONTH_DAY = [15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349]


def day_of_year(d):
    d = parse(d)
    return d.timetuple().tm_yday


def declination(n):
    return math.radians(23.45 * math.sin(2 * math.pi * (284 + n) / 365.0))


def solar(n, hour):
    """Altitude and azimuth in the plot frame (azimuth rotated by the plot bearing)."""
    dec = declination(n)
    lat = math.radians(config.LAT)
    H = math.radians((hour - 12) * 15)
    alt = math.asin(math.sin(lat) * math.sin(dec) +
                    math.cos(lat) * math.cos(dec) * math.cos(H))
    az = math.atan2(math.sin(H),
                    math.cos(H) * math.sin(lat) - math.tan(dec) * math.cos(lat))
    az = az + math.pi - math.radians(config.BEARING)
    return alt, az


def altitude_deg(d, hour):
    return math.degrees(solar(day_of_year(d), hour)[0])


def daylight_hours(d):
    dec = declination(day_of_year(d))
    lat = math.radians(config.LAT)
    c = -math.tan(lat) * math.tan(dec)
    if c <= -1:
        return 24.0
    if c >= 1:
        return 0.0
    return 2 * math.degrees(math.acos(c)) / 15.0


def shadow_vector(alt, az):
    """Shadow direction per metre of height, in the V2 plot frame.

    az is already rotated into the plot frame, where 0 points up the plot. Up
    the plot is -y here (the gate is at y = PLOT_D), so the y component carries
    the opposite sign to the x component: at midwinter noon the sun is due
    south, and shadows run toward the fence and the woodland — -x and -y.
    """
    if alt <= 0.03:
        return None
    L = min(30.0, 1.0 / math.tan(alt))
    return (-math.sin(az) * L, math.cos(az) * L)


def shadow_length(height, alt):
    if alt <= 0.03:
        return None
    return height / math.tan(alt)


def _hull(points):
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def shadow_polygon(zone, sv, min_height=0.25):
    h = zone["height_m"] or 0
    if sv is None or h <= min_height:
        return None
    x, y, w, d = zone["x"], zone["y"], zone["w"], zone["d"]
    base = [(x, y), (x + w, y), (x + w, y + d), (x, y + d)]
    moved = [(px + sv[0] * h, py + sv[1] * h) for px, py in base]
    return _hull(base + moved)


def in_polygon(px, py, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _footprint(z):
    return (z["x"], z["y"], z["x"] + z["w"], z["y"] + z["d"])


def sun_hours(zones, d, step=0.5):
    """Hours of direct sun for every 0.6 m cell on a given date.

    A structure never shades its own footprint - the top of a 0.3 m raised bed
    is in full sun, and the inside of the tunnel is lit through the polythene.
    """
    n = day_of_year(d)
    grid = [[0.0] * GNY for _ in range(GNX)]
    hour = 3.0
    while hour <= 21.0:
        alt, az = solar(n, hour)
        if alt > 0.05:
            sv = shadow_vector(alt, az)
            casters = []
            for z in list(zones) + [WOODLAND]:
                p = shadow_polygon(z, sv)
                if p:
                    casters.append((p, _footprint(z)))
            for i in range(GNX):
                cx = (i + 0.5) * GRID
                for j in range(GNY):
                    cy = (j + 0.5) * GRID
                    lit = True
                    for poly, (x0, y0, x1, y1) in casters:
                        if x0 <= cx <= x1 and y0 <= cy <= y1:
                            continue            # its own footprint
                        if in_polygon(cx, cy, poly):
                            lit = False
                            break
                    if lit:
                        grid[i][j] += step
        hour += step
    return grid


def zones_from_db(conn):
    return [dict(r) for r in conn.execute(
        "SELECT id,name,x,y,w,d,height_m FROM zones").fetchall()]


def zone_sun_hours(conn, zone_id, when):
    """Mean direct sun over a zone's cells on a date."""
    zones = zones_from_db(conn)
    grid = sun_hours(zones, when)
    z = next((z for z in zones if z["id"] == zone_id), None)
    if z is None:
        return None
    vals = []
    for i in range(GNX):
        cx = (i + 0.5) * GRID
        if not (z["x"] <= cx <= z["x"] + z["w"]):
            continue
        for j in range(GNY):
            cy = (j + 0.5) * GRID
            if z["y"] <= cy <= z["y"] + z["d"]:
                vals.append(grid[i][j])
    return round(sum(vals) / len(vals), 1) if vals else None


# ------------------------------------------------------- §29 neighbour shading

def nw_component(height, n, hour):
    """How far a structure's shadow reaches toward the north-west boundary."""
    alt, az = solar(n, hour)
    L = shadow_length(height, alt)
    if L is None:
        return 0.0
    sv = shadow_vector(alt, az)
    return max(0.0, -sv[0] * height)      # -x is toward the NW boundary


REF_HOUR_FROM, REF_HOUR_TO = 8.0, 16.0


def worst_nw_reach(height, day=80):
    """Worst case is 08:00 at the equinoxes (§29): a 2 m structure reaches 4.5 m.

    Scanned from 08:00, not from sunrise. In the ten minutes after the sun clears
    the horizon everything on earth throws a shadow hundreds of metres long, which
    tells you nothing about whether you are shading the neighbour's seedlings.
    """
    worst, at = 0.0, None
    hour = REF_HOUR_FROM
    while hour <= REF_HOUR_TO:
        r = nw_component(height, day, hour)
        if r > worst:
            worst, at = r, hour
        hour += 0.5
    return round(worst, 1), at


def check_placement(zone):
    """Hard rule: no structure over 1 m high within 6 m of the north-west boundary."""
    h = zone.get("height_m") or 0
    if h <= config.NW_MAX_FREE_HEIGHT_M:
        return None
    if zone["x"] < config.NW_EXCLUSION_M:
        reach, hour = worst_nw_reach(h)
        return ("%s is %.1f m high and %.1f m from the north-west boundary. Nothing over "
                "%.0f m may sit within %.0f m: at %s it would throw %.1f m onto the "
                "neighbouring plot." % (zone.get("name", zone.get("id")), h, zone["x"],
                                        config.NW_MAX_FREE_HEIGHT_M, config.NW_EXCLUSION_M,
                                        _fmt_hour(hour), reach))
    return None


def _fmt_hour(h):
    if h is None:
        return "sunrise"
    return "%02d:%02d" % (int(h), int(round((h - int(h)) * 60)))


def check_all_placements(conn):
    return [m for m in (check_placement(z) for z in zones_from_db(conn)) if m]


# --------------------------------------------------- §24 crop placement checks

def check_crop_placement(conn, month=4):
    """Flag any fruiting crop in a bed with under 4 hours of April sun."""
    d = date(date.today().year, month, 15)
    zones = zones_from_db(conn)
    grid = sun_hours(zones, d)
    out = []
    cache = {}
    for crop in conn.execute("SELECT * FROM crops WHERE fruiting=1").fetchall():
        zid = crop["zone_id"]
        if zid not in cache:
            z = next((z for z in zones if z["id"] == zid), None)
            vals = []
            if z:
                for i in range(GNX):
                    cx = (i + 0.5) * GRID
                    if not (z["x"] <= cx <= z["x"] + z["w"]):
                        continue
                    for j in range(GNY):
                        cy = (j + 0.5) * GRID
                        if z["y"] <= cy <= z["y"] + z["d"]:
                            vals.append(grid[i][j])
            cache[zid] = round(sum(vals) / len(vals), 1) if vals else None
        h = cache[zid]
        if h is not None and h < 4.0:
            out.append("%s is a fruiting crop in %s, which gets only %.1f h of sun in %s"
                       % (crop["name"], zid, h, d.strftime("%B")))
    return out
