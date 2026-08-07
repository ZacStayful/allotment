"""Fixed constants for the plot. Part D §26 — these are constants, not lookups."""

import os

SITE_NAME = "Albert Village Allotment Association"
LAT = 52.7596
LON = -1.5535
ELEVATION_M = 110
# The V2 survey. x runs across the plot from the fenced neighbour (x = 0) to the
# unconfirmed right-hand boundary; y runs from the woodland edge (y = 0) down to
# the gate (y = PLOT_D). Up the plot — decreasing y — is the 070° bearing.
PLOT_W = 11.7          # metres, across the plot
PLOT_D = 10.7          # metres, woodland edge to gate
PLOT_AREA = 125.2
BEARING = 70           # up the plot is east-north-east
CANOPY_M = 8.0         # woodland canopy height — assumed, never measured
SOIL = "clay"
SUBSCRIPTION = 46.00   # £/year, renews 1 January
TAP_OFF_MONTHS = (11, 12, 1, 2, 3)   # water off November to March

# §6 budget lines
BUDGET_LINES = [
    "clearance", "tools", "shed", "water", "polytunnel", "beds",
    "growing_media", "paths", "seeds_plants", "protection", "rent",
    "consumables", "contingency",
]
SETUP_BUDGET = (2150.0, 2600.0)
RUNNING_BUDGET = (25.0, 32.0)
CONTINGENCY_PCT = 0.10

# §16 hours tracking
PLAN_HOURS = {8: 29, 9: 18, 10: 22, 11: 16, 12: 9, 1: 6,
              2: 10, 3: 18, 4: 20, 5: 18, 6: 14, 7: 16}   # 196 total
TARGET_CURVE = {1: 196, 2: 122, 3: 110, 4: 100, 5: 90}

# §3 weather thresholds
RAIN_3D_DRY_MM = 8.0        # under this, outdoor beds need water
CLAY_BLOCK_MM = 15.0        # over this in 48h, all soil jobs blocked
FROST_MIN_C = 2.0
GALE_GUST_KPH = 45.0
POLYTHENE_MAX_WIND_KPH = 10.0
STRUCTURE_MAX_WIND_KPH = 20.0
VENTILATE_MAX_C = 20.0
GDD_BASE = 6.0

# §11 / §29 hard rules
NW_EXCLUSION_M = 6.0        # no structure over 1 m within 6 m of the NW boundary
NW_MAX_FREE_HEIGHT_M = 1.0
FENCE_STRIP_M = 1.0         # keep-clear strip, never a growing job
INSPECTION_INTERVAL_DAYS = 28
INSPECTION_START_WEEK = 4
TIDY_DAYS_BEFORE = 3

# §17 barrowing
BARROW_KG = 60.0
BARROW_M3 = 0.1
BARROW_MINUTES = 8          # per trip, car park to plot and back

# §28 weekly time budget, minutes
DAY_BUDGET = {5: 240, 6: 180}       # Sat=5, Sun=6 (Monday=0)
MIDWEEK_BUDGET = 30

# Watering time multiplier when a hosepipe ban is in force (§11)
HOSE_MINUTES = 5
BAN_MINUTES = 20

CATEGORIES = ["build", "soil", "sow", "plant", "tend", "harvest",
              "compost", "maintain", "admin"]
OWNERS = ["Grower", "Site", "Both", "Either"]

# Job categories that the clay rule blocks outright
SOIL_CATEGORIES = {"soil", "build"}

DB_PATH = os.environ.get(
    "ALLOTMENT_DB", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plot.db"))

# The seed login address. No password lives in this file: `plot init` takes one
# from --password, from ALLOTMENT_PASSWORD, or by prompting, and generates a
# random one if it is running unattended. A password committed to a repository
# is a published password.
DEFAULT_EMAIL = os.environ.get("ALLOTMENT_EMAIL", "zac@stayful.co.uk")
MIN_PASSWORD = 10

SESSION_HOURS = 24 * 14
MAX_FAILED_LOGINS = 8
LOCKOUT_MINUTES = 15
