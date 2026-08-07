"""Seed data: zones, crops, jobs, rotation, trouble spots, opening stock.

Geometry is the single source of truth for both the sun model and the map,
so the drawing and the arithmetic can never disagree.

Bump SEED_VERSION whenever the layout changes. A hosted deployment has no shell
to re-seed from, so the app compares this against what the database was last
seeded with and brings it up to date on the next request - otherwise a plot that
has been re-surveyed keeps serving the layout it was first seeded with.
"""

SEED_VERSION = "2026-08-v2-survey"

# id, name, type, x, y, w, d, height, growable, colour, notes
#
# The V2 survey, in the same frame and the same colours as the drawing at
# /map: x = 0 is the fenced neighbour, y = 0 is the woodland edge, y = PLOT_D
# is the gate. The drawing's "shed & compost block" is an outline around the
# shed and the bays rather than a place of its own, so it is not a zone here.
ZONES = [
    ("bramble", "Bramble cut-back margin", "scrub", 0.0, 0.0, 11.7, 0.7, 0.0, 0, "#7A5A2E",
     "An advancing edge - canes tip-root wherever they touch soil. Cut the face back hard "
     "every winter and keep the 700 mm open. Thorny prunings never go in the bays."),
    ("phacelia", "Green manure strip", "green", 0.6, 0.7, 6.3, 1.4, 0.0, 1, "#6B5B95",
     "Phacelia. Counts as cultivated at inspection and feeds the soil. Dig it in green, "
     "before it sets seed."),
    ("shed",    "Shed",             "structure", 7.35, 0.85, 1.83, 1.22, 2.0, 0, "#2E4A5A",
     "6 x 4 ft, at the site cap. Written committee consent before it goes up. Do not "
     "gutter this roof - 25 mm of rain gives about 55 L."),
    ("compost", "Compost bays",     "compost",   9.4,  0.85, 1.55, 1.22, 1.0, 0, "#2E4A5A",
     "Two bays, built straight after beds 1 and 2 so turf stops being barrowed off site."),
    ("xp1",     "Cross path (upper)", "path",    0.6,  2.1, 10.5,  0.4, 0.0, 0, "#CFC7B4",
     "Every trip to the shed, the bays and the tunnel crosses this. Woodchip it first."),
    ("bedA",    "Bed A",            "bed",       0.6,  2.5,  4.9,  1.2, 0.12, 1, "#7A8B4F",
     "Half-bed above the spine junction. 600 mm reach from either path edge."),
    ("butts",   "Water butts",      "water",     6.3,  2.5,  0.6,  1.4, 1.0, 0, "#237E8C",
     "Two butts fed from the tunnel gutter. The only water November to March."),
    ("tunnel",  "Polytunnel",       "structure", 7.0,  2.5,  4.0,  2.0, 2.2, 1, "#2E4A5A",
     "4 x 2 m maximum on a full plot. Never receives rain. Gutter this roof, not the shed."),
    ("nursery", "Nursery / standing-out", "nursery", 0.6, 3.7, 4.9, 0.8, 0.0, 1, "#B7A98C",
     "Modules and pots. Borage gets one corner - it self-seeds, so thin it annually."),
    ("xp2",     "Cross path (lower)", "path",    0.6,  4.5, 10.5,  0.4, 0.0, 0, "#CFC7B4",
     "400 mm, woodchip. Marigolds along the edges."),
    ("bed1L",   "Bed 1 left",       "bed",       0.6,  4.9,  4.9,  1.2, 0.12, 1, "#7A8B4F",
     "Half-bed. Carries the same rotation group as Bed 1 right."),
    ("bed1R",   "Bed 1 right",      "bed",       6.2,  4.9,  4.9,  1.2, 0.12, 1, "#7A8B4F",
     "Half-bed. Carries the same rotation group as Bed 1 left."),
    ("p1",      "Path (beds 1-2)",  "path",      0.6,  6.1, 10.5,  0.4, 0.0, 0, "#CFC7B4",
     "400 mm, woodchip."),
    ("bed2L",   "Bed 2 left",       "bed",       0.6,  6.5,  4.9,  1.2, 0.12, 1, "#7A8B4F",
     "Half-bed. Carries the same rotation group as Bed 2 right."),
    ("bed2R",   "Bed 2 right",      "bed",       6.2,  6.5,  4.9,  1.2, 0.12, 1, "#7A8B4F",
     "Half-bed. Carries the same rotation group as Bed 2 left."),
    ("p2",      "Path (beds 2-3)",  "path",      0.6,  7.7, 10.5,  0.4, 0.0, 0, "#CFC7B4",
     "400 mm, woodchip."),
    ("bed3L",   "Bed 3 left",       "bed",       0.6,  8.1,  4.9,  1.2, 0.12, 1, "#7A8B4F",
     "Half-bed. Carries the same rotation group as Bed 3 right."),
    ("bed3R",   "Bed 3 right",      "bed",       6.2,  8.1,  4.9,  1.2, 0.12, 1, "#7A8B4F",
     "Half-bed. Carries the same rotation group as Bed 3 left."),
    ("p3",      "Path (bed 3 to headland)", "path", 0.6, 9.3, 10.5, 0.4, 0.0, 0, "#CFC7B4",
     "400 mm, woodchip."),
    ("spine",   "Central spine path", "path",    5.5,  2.1,  0.7,  7.6, 0.0, 0, "#CFC7B4",
     "700 mm barrow route, gate to the woodland end. Chives along the edge beside the "
     "root beds - perennial, plant once, label it so they do not get dug."),
    ("headland", "Gate headland",   "path",      0.0,  9.7, 11.7,  1.0, 0.0, 0, "#CFC7B4",
     "Turning and unloading space inside the gate. Every barrow load starts here."),
]

# id, name, zone, family, si_from, si_to, sd_from, sd_to, po_from, po_to,
# h_from, h_to, spacing, net, support, fruiting, notes
CROPS = [
    ("garlic", "Garlic", "bedA", "allium", None, None, None, None, "10-01", "12-31",
     "06-01", "07-31", 15, 0, 0, 0, "Needs a cold spell. Cloves pointy end up."),
    ("onion", "Onion (sets)", "bedA", "allium", None, None, None, None, "03-01", "04-30",
     "08-01", "09-30", 10, 0, 0, 0, "Autumn sets Sep-Oct also possible."),
    ("broadbean", "Broad beans", "bedA", "legume", None, None, "02-01", "04-30", None, None,
     "06-01", "07-31", 20, 0, 1, 0, "Autumn sowing crops earlier and dodges blackfly."),
    ("beetroot", "Beetroot", "bed3L", "chenopod", None, None, "04-01", "07-31", None, None,
     "06-01", "10-31", 10, 0, 0, 0, "Succession every 3 weeks."),
    ("chard", "Chard", "bed3L", "chenopod", None, None, "04-01", "07-31", None, None,
     "06-01", "04-30", 25, 0, 0, 0, "Overwinters. Cut-and-come-again."),
    ("spinach", "Perpetual spinach", "bed3L", "chenopod", None, None, "04-01", "07-31", None, None,
     "06-01", "04-30", 25, 0, 0, 0, "Same treatment as chard."),
    ("kale", "Kale", "bed2L", "brassica", "04-01", "06-30", None, None, "06-01", "07-31",
     "10-01", "04-30", 45, 1, 0, 0, "Net from planting out. Pigeons strip it."),
    ("turnip", "Turnip", "bed2L", "brassica", None, None, "03-01", "08-31", None, None,
     "05-01", "10-31", 15, 1, 0, 0, "Net. Fast - 6 to 8 weeks."),
    ("radish", "Radish", "bed2L", "brassica", None, None, "03-01", "09-30", None, None,
     "04-01", "10-31", 3, 1, 0, 0, "Succession every 2 weeks. 4 weeks to crop."),
    ("salad", "Salad leaves", "bed1R", "mixed", None, None, "03-01", "09-30", None, None,
     "04-01", "11-30", 10, 0, 0, 0, "Succession every 2-3 weeks. Fleece early and late."),
    ("courgette", "Courgette", "bed1R", "cucurbit", "04-20", "04-30", None, None, "05-25", "06-10",
     "07-01", "09-30", 90, 0, 0, 1, "Pick every 2-3 days or it stops."),
    ("runnerbean", "Runner beans", "bedA", "legume", "05-01", "05-31", "05-20", "06-15",
     "06-01", "06-15", "07-01", "10-31", 20, 0, 1, 1, "Pick every 2-3 days. Wigwam up first."),
    ("frenchbean", "French beans", "bedA", "legume", "05-01", "05-31", "05-20", "06-30",
     "06-01", "06-30", "07-01", "09-30", 15, 0, 1, 1, "As runner beans."),
    ("potato_first", "Potato - first early", "bed1L", "solanum", None, None, None, None,
     "03-20", "04-05", "06-01", "07-31", 30, 0, 0, 0, "Chit Feb. Earth up from 21 days."),
    ("potato_second", "Potato - second early", "bed1L", "solanum", None, None, None, None,
     "04-01", "04-14", "07-01", "08-31", 35, 0, 0, 0, "Chit Feb."),
    ("potato_main", "Potato - maincrop", "bed1L", "solanum", None, None, None, None,
     "04-14", "04-30", "09-01", "09-30", 40, 0, 0, 0, "Cure 2 weeks before storing."),
    ("tomato", "Tomato", "tunnel", "solanum", "02-01", "03-31", None, None, "05-10", "05-25",
     "07-01", "10-31", 45, 0, 1, 1, "Side-shoot weekly. 6-8 plants down one side."),
    ("cucumber", "Cucumber", "tunnel", "cucurbit", "04-01", "04-30", None, None, "05-20", "06-05",
     "07-01", "09-30", 45, 0, 1, 1, "Train up mesh. 4-5 plants."),
    ("chilli", "Pepper / chilli", "tunnel", "solanum", "02-01", "03-31", None, None, "05-10", "05-25",
     "08-01", "10-31", 40, 0, 1, 1, "Needs the warmth - won't crop outdoors here."),
    ("basil", "Basil", "tunnel", "mixed", "03-01", "05-31", None, None, "05-01", "05-31",
     "06-01", "09-30", 20, 0, 0, 0, "Plant among the tomatoes."),
    ("marigold", "French marigold", "tunnel", "flower", "03-01", "04-30", None, None, "05-01", "05-31",
     None, None, 20, 0, 0, 0, "Deters whitefly. Not a crop."),
    ("herbs", "Chives, thyme, oregano", "nursery", "perennial", None, None, None, None, "03-01", "05-31",
     "01-01", "12-31", 25, 0, 0, 0, "Bed ends. Flower well for bees."),
    ("borage", "Borage", "nursery", "flower", None, None, "03-01", "05-31", None, None,
     None, None, 45, 0, 0, 0, "Best single plant for courgettes and beans. Self-seeds."),
    ("phacelia", "Phacelia", "phacelia", "flower", None, None, "03-01", "09-30", None, None,
     None, None, 10, 0, 0, 0, "Pollinators and green manure. Cut before it seeds."),
    ("calendula", "Calendula", "nursery", "flower", None, None, "03-01", "05-31", None, None,
     None, None, 30, 0, 0, 0, "Hoverflies - their larvae eat aphids."),
    ("poachedegg", "Poached egg plant", "nursery", "flower", None, None, "03-01", "04-30", None, None,
     None, None, 20, 0, 0, 0, "Hoverflies. Low, good bed edging."),
    ("nasturtium", "Nasturtium", "bedA", "flower", None, None, "04-01", "05-31", None, None,
     None, None, 30, 0, 0, 0, "Trap crop - blackfly go for it instead of beans."),
    ("cornflower", "Cornflower", "nursery", "flower", None, None, "03-01", "05-31", None, None,
     None, None, 25, 0, 0, 0, "General pollinator draw."),
    ("sunflower", "Sunflower", "nursery", "flower", None, None, "04-01", "05-31", None, None,
     None, None, 45, 0, 1, 0, "Height on the exposed side."),
    ("sweetpea", "Sweet pea", "nursery", "flower", "02-01", "04-30", None, None, "04-15", "05-15",
     None, None, 20, 0, 1, 0, "Cut flowers, pulls pollinators in."),
]


def J(title, category, owner, mins, rule_type, params, **kw):
    d = dict(title=title, category=category, owner=owner, est_minutes=mins,
             rule_type=rule_type, rule_params=params)
    d.update(kw)
    return d


# --- build sequence (§19 jobs 1-21). One-offs, chained by dependency. ---
BUILD = [
    J("Clear the plot - strim and remove rubbish", "build", "Both", 240, "fixed_window",
      {"start_md": "08-01", "end_md": "09-30"}, one_off=1, consequence=4, key="clear_plot"),
    J("Mark out zones with string lines", "build", "Both", 90, "dependency",
      {"depends_on": ["clear_plot"]}, one_off=1, consequence=3, key="mark_out"),
    J("Survey the fall across the plot", "build", "Site", 60, "dependency",
      {"depends_on": ["mark_out"]}, one_off=1, consequence=2, key="survey"),
    J("Woodchip the gate headland", "build", "Site", 240, "dependency",
      {"depends_on": ["survey"]}, one_off=1, consequence=3, zone_id="headland",
      stock_needs=[["Hardcore", 1], ["Slabs", 12]], key="hardstanding"),
    J("Apply in writing for shed and polytunnel permission", "admin", "Site", 30, "fixed_window",
      {"start_md": "08-01", "end_md": "12-31"}, one_off=1, consequence=5, key="permission"),
    J("Confirm tunnel placement approved by Committee", "admin", "Site", 20, "dependency",
      {"depends_on": ["permission"]}, one_off=1, consequence=5, key="tunnel_approved"),
    J("Build the shed base", "build", "Site", 300, "dependency",
      {"depends_on": ["hardstanding", "permission"]}, one_off=1, consequence=3,
      zone_id="shed", needs_permission=1, key="shed_base"),
    J("Erect the shed", "build", "Both", 300, "dependency",
      {"depends_on": ["shed_base"]}, one_off=1, consequence=3, zone_id="shed",
      needs_permission=1, key="shed"),
    J("Fit guttering and connect water butts", "build", "Site", 120, "dependency",
      {"depends_on": ["shed"]}, one_off=1, consequence=4, zone_id="butts", key="butts"),
    J("Level the polytunnel site", "soil", "Both", 180, "dependency",
      {"depends_on": ["tunnel_approved"]}, one_off=1, consequence=3, zone_id="tunnel",
      needs_permission=1, key="tunnel_site"),
    J("Erect the polytunnel frame", "build", "Both", 300, "dependency",
      {"depends_on": ["tunnel_site"]}, one_off=1, consequence=3, zone_id="tunnel",
      needs_permission=1, key="tunnel_frame"),
    J("Fit the tunnel polythene", "build", "Both", 240, "dependency",
      {"depends_on": ["tunnel_frame"]}, one_off=1, consequence=4, zone_id="tunnel",
      needs_permission=1, notes="Hard block over 10 kph wind.", key="tunnel_poly"),
    J("Build the raised beds", "build", "Both", 360, "dependency",
      {"depends_on": ["mark_out"]}, one_off=1, consequence=4,
      stock_needs=[["Scaffold boards", 12]], key="build_beds"),
    J("Fill the beds with compost and topsoil", "soil", "Both", 300, "dependency",
      {"depends_on": ["build_beds"]}, one_off=1, consequence=4,
      stock_needs=[["Multipurpose compost", 400]], key="fill_beds"),
    J("Lay membrane and woodchip on the paths", "build", "Both", 180, "dependency",
      {"depends_on": ["build_beds"]}, one_off=1, consequence=2, zone_id="spine",
      stock_needs=[["Woodchip", 2000]], key="paths"),
    J("Build the compost bays from pallets", "build", "Site", 120, "dependency",
      {"depends_on": ["mark_out"]}, one_off=1, consequence=2, zone_id="compost", key="compost_bays"),
]

# --- the recurring year (§4, §14, §15) ---
JOBS = [
    # every visit
    J("20 minutes weeding on arrival", "tend", "Both", 20, "every_visit", {},
      every_visit=1, consequence=3),
    J("Open the tunnel (before 9am)", "tend", "Either", 2, "every_visit",
      {"from_md": "03-01", "to_md": "10-31"}, every_visit=1, consequence=4, zone_id="tunnel", requires=["tunnel_poly"]),
    J("Shut the tunnel (before dusk)", "tend", "Either", 2, "every_visit",
      {"from_md": "03-01", "to_md": "10-31"}, every_visit=1, consequence=4, zone_id="tunnel", requires=["tunnel_poly"]),
    J("Log the visit", "admin", "Either", 1, "every_visit", {}, every_visit=1, consequence=2),

    # --- admin and compliance (§14) ---
    J("Pay the subscription", "admin", "Site", 15, "fixed_window",
      {"start_md": "01-01", "end_md": "01-31"}, consequence=5),
    J("Tidy sweep and path edges before inspection", "tend", "Both", 45, "inspection_linked",
      {"days_before": 3}, consequence=4),
    J("Plot inspection due", "admin", "Both", 0, "inspection_linked",
      {"days_before": 0}, consequence=5),
    J("Review seed viability, bin what has expired", "admin", "Grower", 30, "fixed_window",
      {"start_md": "01-05", "end_md": "01-25"}, consequence=3),
    J("Order seeds and seed potatoes", "admin", "Grower", 45, "fixed_window",
      {"start_md": "12-01", "end_md": "01-31"}, consequence=4),
    J("Plan next year and propose the rotation", "admin", "Both", 60, "fixed_window",
      {"start_md": "11-01", "end_md": "11-30"}, consequence=3),

    # --- January ---
    J("Turn the compost", "compost", "Either", 30, "recurring",
      {"interval_days": 30}, zone_id="compost", consequence=1, requires=["compost_bays"]),
    J("Empty compost bays onto the beds", "compost", "Both", 120, "fixed_window",
      {"start_md": "01-05", "end_md": "02-15"}, zone_id="compost", consequence=2, requires=["compost_bays"]),
    J("Check shed felt, hinges and padlock", "maintain", "Site", 20, "recurring",
      {"interval_days": 90}, zone_id="shed", consequence=3, requires=["shed"]),
    J("Check tunnel polythene tension, doors and anchoring", "maintain", "Site", 25, "recurring",
      {"interval_days": 90}, zone_id="tunnel", consequence=4, requires=["tunnel_poly"]),
    J("Clean and oil the tools", "maintain", "Either", 40, "recurring",
      {"interval_days": 90}, consequence=2),

    # --- February ---
    J("Rough-dig the potato row", "soil", "Both", 120, "fixed_window",
      {"start_md": "02-01", "end_md": "03-10"}, zone_id="bed1L", consequence=3),
    J("Chit the seed potatoes at home", "sow", "Grower", 20, "fixed_window",
      {"start_md": "02-01", "end_md": "02-20"}, consequence=4,
      stock_needs=[["Seed potatoes", 1]]),
    J("Sow tomatoes indoors", "sow", "Grower", 30, "crop_linked",
      {"crop_id": "tomato", "anchor": "sow_indoor", "offset_days": 0}, consequence=4,
      crop_id="tomato", stock_needs=[["Tomato seed", 1], ["Seed compost", 10]]),
    J("Sow chillies and peppers indoors", "sow", "Grower", 20, "crop_linked",
      {"crop_id": "chilli", "anchor": "sow_indoor", "offset_days": 0}, consequence=3,
      crop_id="chilli", stock_needs=[["Seed compost", 5]]),
    J("Sow cucumbers indoors", "sow", "Grower", 15, "crop_linked",
      {"crop_id": "cucumber", "anchor": "sow_indoor", "offset_days": 0}, consequence=3,
      crop_id="cucumber", stock_needs=[["Seed compost", 5]]),
    J("Sow broad beans direct", "sow", "Grower", 40, "fixed_window",
      {"start_md": "02-15", "end_md": "04-15"}, zone_id="bed3L", consequence=3,
      crop_id="broadbean", stock_needs=[["Broad bean seed", 1]], requires=["fill_beds"]),
    J("Plant garlic if not done in autumn", "plant", "Grower", 30, "fixed_window",
      {"start_md": "02-01", "end_md": "02-28"}, zone_id="bedA", consequence=3, crop_id="garlic", requires=["fill_beds"]),

    # --- March ---
    J("Plant the onion sets", "plant", "Grower", 45, "fixed_window",
      {"start_md": "03-01", "end_md": "04-30"}, zone_id="bedA", consequence=3,
      crop_id="onion", stock_needs=[["Onion sets", 1]], requires=["fill_beds"]),
    J("Sow the green manure strip", "sow", "Either", 30, "fixed_window",
      {"start_md": "03-01", "end_md": "04-30"}, zone_id="phacelia", consequence=2,
      stock_needs=[["Phacelia seed", 1]]),
    J("Sow the nursery companions", "sow", "Grower", 40, "fixed_window",
      {"start_md": "03-15", "end_md": "05-15"}, zone_id="nursery", consequence=2, requires=["fill_beds"]),
    J("First weeding push of the year", "tend", "Both", 90, "fixed_window",
      {"start_md": "03-01", "end_md": "03-31"}, consequence=3),

    # --- succession sowings (§12) ---
    J("Sow radish", "sow", "Grower", 15, "succession",
      {"interval_days": 14, "window_start": "03-01", "window_end": "09-30", "max_sowings": 12},
      zone_id="bed2L", crop_id="radish", consequence=2, stock_needs=[["Radish seed", 1]], requires=["fill_beds"]),
    J("Sow salad leaves", "sow", "Grower", 20, "succession",
      {"interval_days": 18, "window_start": "03-01", "window_end": "09-30", "max_sowings": 11},
      zone_id="bed1R", crop_id="salad", consequence=3, stock_needs=[["Salad seed", 1]], requires=["fill_beds"]),
    J("Sow beetroot", "sow", "Grower", 25, "succession",
      {"interval_days": 21, "window_start": "04-01", "window_end": "07-31", "max_sowings": 6},
      zone_id="bed3L", crop_id="beetroot", consequence=3, stock_needs=[["Beetroot seed", 1]], requires=["fill_beds"]),

    # --- April, peak month ---
    J("Plant the first early potatoes", "plant", "Site", 60, "crop_linked",
      {"crop_id": "potato_first", "anchor": "plant", "offset_days": 0}, zone_id="bed1L",
      crop_id="potato_first", consequence=4),
    J("Plant the second early potatoes", "plant", "Site", 60, "crop_linked",
      {"crop_id": "potato_second", "anchor": "plant", "offset_days": 0}, zone_id="bed1L",
      crop_id="potato_second", consequence=4),
    J("Plant the maincrop potatoes", "plant", "Site", 90, "crop_linked",
      {"crop_id": "potato_main", "anchor": "plant", "offset_days": 0}, zone_id="bed1L",
      crop_id="potato_main", consequence=4),
    J("Earth up the potatoes", "tend", "Site", 40, "crop_linked",
      {"crop_id": "potato_first", "anchor": "plant", "offset_days": 21,
       "repeat_days": 14, "repeat_count": 3}, zone_id="bed1L", crop_id="potato_first",
      consequence=4, requires=["plant_the_first_early_potatoes"]),
    J("Plant beetroot, chard and kale plugs", "plant", "Grower", 45, "fixed_window",
      {"start_md": "04-15", "end_md": "06-15"}, zone_id="bed2L", consequence=3, requires=["fill_beds"]),
    J("Net the brassicas", "tend", "Grower", 25, "crop_linked",
      {"crop_id": "kale", "anchor": "plant", "offset_days": 0}, zone_id="bed2L",
      crop_id="kale", consequence=5, stock_needs=[["Butterfly netting", 1]],
      notes="Net from the day you plant out, not when damage appears.", requires=["fill_beds"]),
    J("Sow beans direct", "sow", "Grower", 40, "fixed_window",
      {"start_md": "05-20", "end_md": "06-15"}, zone_id="bedA", consequence=3),

    # --- May ---
    J("Plant out the tomatoes in the tunnel", "plant", "Grower", 60, "crop_linked",
      {"crop_id": "tomato", "anchor": "plant", "offset_days": 0}, zone_id="tunnel",
      crop_id="tomato", consequence=4, requires=["tunnel_poly"]),
    J("Plant out the cucumbers in the tunnel", "plant", "Grower", 30, "crop_linked",
      {"crop_id": "cucumber", "anchor": "plant", "offset_days": 0}, zone_id="tunnel",
      crop_id="cucumber", consequence=3, requires=["tunnel_poly"]),
    J("Build the bean wigwams", "build", "Site", 60, "fixed_window",
      {"start_md": "05-01", "end_md": "05-25"}, zone_id="bedA", consequence=4,
      stock_needs=[["Bean canes", 20], ["Twine", 1]], requires=["clear_plot"]),
    J("Plant out the courgettes", "plant", "Grower", 30, "crop_linked",
      {"crop_id": "courgette", "anchor": "plant", "offset_days": 0}, zone_id="bed1R",
      crop_id="courgette", consequence=4, requires=["fill_beds"]),
    J("Plant out the beans", "plant", "Grower", 45, "crop_linked",
      {"crop_id": "runnerbean", "anchor": "plant", "offset_days": 0}, zone_id="bedA",
      crop_id="runnerbean", consequence=4, requires=["build_the_bean_wigwams"]),
    J("Plant nasturtiums at the base of the beans", "plant", "Grower", 15, "fixed_window",
      {"start_md": "05-15", "end_md": "06-15"}, zone_id="bedA", consequence=2, requires=["build_the_bean_wigwams"]),

    # --- June onwards ---
    J("Tie in and side-shoot the tomatoes", "tend", "Grower", 20, "recurring",
      {"interval_days": 7, "from_md": "06-01", "to_md": "09-30"}, zone_id="tunnel",
      crop_id="tomato", consequence=4, requires=["tunnel_poly"]),
    J("Check the netting", "tend", "Either", 10, "recurring",
      {"interval_days": 14, "from_md": "05-01", "to_md": "10-31"}, consequence=4, requires=["net_the_brassicas"]),
    J("Pick beans and courgettes", "harvest", "Either", 25, "recurring",
      {"interval_days": 3, "from_md": "07-01", "to_md": "10-15"}, consequence=5,
      notes="Miss this and the plants stop cropping.", requires=["plant_out_the_courgettes", "plant_out_the_beans"]),
    J("Harvest broad beans, salad and garlic", "harvest", "Either", 40, "fixed_window",
      {"start_md": "06-01", "end_md": "07-31", "frequency": "weekly"}, consequence=4, requires=["sow_broad_beans_direct"]),
    J("Harvest tomatoes and cucumbers", "harvest", "Either", 20, "recurring",
      {"interval_days": 4, "from_md": "07-01", "to_md": "10-15"}, zone_id="tunnel", consequence=4, requires=["tunnel_poly"]),
    J("Lift the first early potatoes", "harvest", "Both", 60, "crop_linked",
      {"crop_id": "potato_first", "anchor": "harvest", "offset_days": 0}, zone_id="bed1L",
      crop_id="potato_first", consequence=4, requires=["plant_the_first_early_potatoes"]),
    J("Sow autumn salad", "sow", "Grower", 20, "fixed_window",
      {"start_md": "08-01", "end_md": "09-10"}, zone_id="bed1R", consequence=2, requires=["fill_beds"]),

    # --- September ---
    J("Lift the maincrop potatoes", "harvest", "Both", 120, "crop_linked",
      {"crop_id": "potato_main", "anchor": "harvest", "offset_days": 0}, zone_id="bed1L",
      crop_id="potato_main", consequence=5, requires=["plant_the_maincrop_potatoes"]),
    J("Cure and store the maincrop potatoes", "harvest", "Grower", 45, "crop_linked",
      {"crop_id": "potato_main", "anchor": "harvest", "offset_days": 14}, consequence=4, requires=["lift_the_maincrop_potatoes"]),
    J("Clear the tunnel", "tend", "Both", 90, "fixed_window",
      {"start_md": "09-20", "end_md": "10-31"}, zone_id="tunnel", consequence=3, requires=["tunnel_poly"]),
    J("Dry and store the onions", "harvest", "Grower", 45, "fixed_window",
      {"start_md": "08-15", "end_md": "09-30"}, consequence=4, requires=["plant_the_onion_sets"]),
    J("Sow green manure on cleared ground", "sow", "Either", 30, "fixed_window",
      {"start_md": "09-01", "end_md": "10-15"}, consequence=3),
    J("Collect seed", "admin", "Grower", 30, "fixed_window",
      {"start_md": "08-15", "end_md": "09-30"}, consequence=1),

    # --- October ---
    J("Clear the beds and mulch", "soil", "Both", 150, "fixed_window",
      {"start_md": "10-01", "end_md": "11-15"}, consequence=3,
      stock_needs=[["Multipurpose compost", 200]], requires=["fill_beds"]),
    J("Plant garlic and overwintering onions", "plant", "Grower", 45, "fixed_window",
      {"start_md": "10-01", "end_md": "12-15"}, zone_id="bedA", crop_id="garlic", consequence=4, requires=["fill_beds"]),
    J("Fill every water butt before the tap goes off", "maintain", "Site", 30, "fixed_window",
      {"start_md": "10-01", "end_md": "10-31"}, zone_id="butts", consequence=5,
      notes="The tap is off November to March. This is the last chance.", requires=["butts"]),
    J("Check the tunnel before the winter storms", "maintain", "Site", 30, "fixed_window",
      {"start_md": "10-15", "end_md": "11-15"}, zone_id="tunnel", consequence=4, requires=["tunnel_poly"]),
    J("Top up the path woodchip", "maintain", "Both", 90, "fixed_window",
      {"start_md": "10-01", "end_md": "11-30"}, zone_id="spine", consequence=2,
      stock_needs=[["Woodchip", 1000]], requires=["paths"]),

    # --- November and December ---
    J("Harvest kale", "harvest", "Either", 15, "recurring",
      {"interval_days": 10, "from_md": "10-01", "to_md": "04-30"}, zone_id="bed2L", consequence=3, requires=["fill_beds"]),
    J("Cut down and lay the green manure", "soil", "Both", 60, "fixed_window",
      {"start_md": "02-15", "end_md": "04-10"}, zone_id="phacelia", consequence=3,
      notes="Before it sets seed."),
    J("Top up the bed compost", "soil", "Both", 90, "fixed_window",
      {"start_md": "03-01", "end_md": "04-15"}, consequence=3,
      stock_needs=[["Multipurpose compost", 300]], requires=["fill_beds"]),

    # --- weather-conditional (§3) ---
    J("Water the beds and the nursery", "tend", "Either", 25, "weather_conditional",
      {"condition": "dry_3d", "from_md": "04-01", "to_md": "09-30"}, consequence=4),
    J("Water the polytunnel", "tend", "Either", 10, "weather_conditional",
      {"condition": "always", "from_md": "03-01", "to_md": "10-31"}, zone_id="tunnel",
      consequence=5, notes="The tunnel never gets rain. Catches everyone out.", requires=["tunnel_poly"]),
    J("Slug patrol after dark", "tend", "Either", 20, "weather_conditional",
      {"condition": "slug_night", "from_md": "04-01", "to_md": "06-30"}, consequence=4,
      zone_id="bramble", notes="Start along the bramble margin at the woodland end."),
    J("Ventilate the tunnel - open by 9am, shut by dusk", "tend", "Either", 5,
      "weather_conditional", {"condition": "warm_day", "from_md": "03-01", "to_md": "10-31"},
      zone_id="tunnel", consequence=4, requires=["tunnel_poly"]),
    J("Fleece the tender plants - frost forecast", "tend", "Either", 25, "weather_conditional",
      {"condition": "frost_risk", "from_md": "03-01", "to_md": "05-31"}, consequence=5,
      stock_needs=[["Fleece", 1]]),
    J("Check tunnel anchoring and bean wigwams - gale forecast", "maintain", "Site", 20,
      "weather_conditional", {"condition": "gale_risk", "from_md": "01-01", "to_md": "12-31"},
      consequence=5),
    J("Top up the water butts from the tap", "maintain", "Site", 20, "weather_conditional",
      {"condition": "butts_low", "from_md": "04-01", "to_md": "10-31"}, zone_id="butts",
      consequence=3, requires=["butts"]),

    # --- long cycle (§15) ---
    J("Replace the tunnel polythene", "maintain", "Both", 300, "recurring",
      {"interval_days": 1826, "after_job": "tunnel_poly"}, zone_id="tunnel", consequence=4,
      notes="Budget £120-180. The sinking fund exists for this."),
]

# §13 rotation, four groups moving one bed a year
# Four courses over four bed rows. Both halves of a row always carry the same
# group, and each row moves on one group a year: index = (start + year - 1) % 4
# over [potatoes, legumes_alliums, brassicas, roots]. Bed A starts on legumes,
# row 1 on potatoes, row 2 on brassicas, row 3 on roots. The phacelia strip is
# permanent and sits outside the rotation.
_COURSES = ["potatoes", "legumes_alliums", "brassicas", "roots"]
_ROW_START = {"bedA": 1, "bed1L": 0, "bed1R": 0, "bed2L": 2,
              "bed2R": 2, "bed3L": 3, "bed3R": 3}
ROTATION = {
    year: dict([(bed, _COURSES[(start + year - 1) % 4])
                for bed, start in _ROW_START.items()] + [("phacelia", "green_manure")])
    for year in (1, 2, 3, 4)
}
GROUP_FAMILIES = {
    "potatoes": ["solanum", "cucurbit"],
    "legumes_alliums": ["legume", "allium"],
    "brassicas": ["brassica"],
    "roots": ["umbellifer", "chenopod"],
    "green_manure": [],
}
GROUP_NAMES = {
    "potatoes": "Potatoes (maincrop)", "legumes_alliums": "Legumes & alliums",
    "brassicas": "Brassicas", "roots": "Roots", "green_manure": "Green manure",
}

# §23 the nine derived trouble spots
# Placed in the V2 frame: the woodland and the bramble run along y = 0, the gate
# is at y = PLOT_D, and the fenced neighbour is x = 0.
TROUBLE = [
    (2.0, 0.5, "Slugs", "pest", "High",
     "Damp, shaded and against the bramble - the classic slug reservoir. They shelter in "
     "the cut-back margin and the compost bays by day, then travel up to 10 m at night.",
     "Patrol after rain, April to June, after dark. Keep the 700 mm margin cut short."),
    (10.2, 1.5, "Compost bays", "pest", "Medium",
     "Warm, damp and full of organic matter. Slugs breed here, and anything that goes in "
     "seeding comes back out spread across the beds.",
     "Never compost a plant that has flowered. Turn monthly - heat kills seed."),
    (5.8, 0.35, "Woodland seed rain", "weed", "High",
     "Wind-blown birch and willow seed the length of the front face, plus bramble tip-rooting "
     "wherever a cane touches soil. The highest weed load on the plot and it never stops.",
     "The 700 mm cut-back margin must stay open anyway. Strim it monthly."),
    (5.85, 10.2, "Mud and compaction", "ground", "High",
     "The gate headland takes every barrow load, and with no vehicle access that is every bag "
     "of compost and the shed itself. Clay compacts fast.",
     "Keep woodchip topped up and never wheel across soft ground when wet."),
    (2.5, 9.9, "Wind exposure", "weather", "Medium",
     "Prevailing wind is south-westerly and the gate end takes it - the treeline only shelters "
     "the woodland end. The polytunnel is the most wind-vulnerable thing on the plot.",
     "Anchor the polythene, check tension quarterly, keep repair tape in the shed."),
    (3.0, 7.1, "Pigeons", "bird", "High",
     "The brassica row sits under a clear sightline from the trees. Pigeons can strip kale in "
     "an afternoon.",
     "Net from the day you plant out, not when damage appears."),
    (2.0, 5.5, "Frost pocket", "weather", "Low",
     "Cold air drains downhill and pools at the low point.",
     "Fleece tender plants here first. Nothing tender out before the third week of May."),
    (3.0, 1.4, "Dry shadow", "water", "Medium",
     "Ground within two metres of the treeline is drier all season and full of roots - they "
     "take the water first.",
     "Phacelia and shallow-rooted annuals only. Mulch here in spring."),
    (9.0, 3.5, "Tunnel - never rained on", "water", "Certain",
     "Nothing inside a polytunnel receives rain, ever. The commonest way beginners lose a crop.",
     "Water March to October regardless of the weather. A standing job, not a conditional one."),
]

# Opening stock. Reorder points, not quantities (§32).
STOCK = [
    ("Multipurpose compost", "growing_media", "L", 0, 100, "shed", 0.05, None, 1, 0.4, 0.001),
    ("Seed compost", "growing_media", "L", 0, 20, "home", 0.08, None, 1, 0.4, 0.001),
    ("Woodchip", "growing_media", "L", 0, 500, "shed", 0.01, None, 1, 0.25, 0.001),
    ("Fleece", "protection", "m", 0, 5, "shed", 1.20, None, 1, None, None),
    ("Butterfly netting", "protection", "m", 0, 4, "shed", 2.00, None, 1, None, None),
    ("Bean canes", "support", "each", 0, 10, "shed", 0.80, None, 1, None, None),
    ("Twine", "support", "roll", 0, 1, "shed", 3.00, None, 1, None, None),
    ("Organic slug control", "treatments", "kg", 0, 1, "shed", 9.00, None, 1, None, None),
    ("Pots and labels", "consumables", "each", 0, 20, "shed", 0.15, None, 1, None, None),
    ("Radish seed", "seed", "packet", 0, 1, "home", 1.50, None, 1, None, None),
    ("Salad seed", "seed", "packet", 0, 1, "home", 2.00, None, 1, None, None),
    ("Beetroot seed", "seed", "packet", 0, 1, "home", 1.80, None, 1, None, None),
    ("Broad bean seed", "seed", "packet", 0, 1, "home", 2.50, None, 1, None, None),
    ("Tomato seed", "seed", "packet", 0, 1, "home", 2.50, None, 1, None, None),
    ("Phacelia seed", "seed", "kg", 0, 1, "shed", 12.00, None, 1, None, None),
    ("Onion sets", "plants", "kg", 0, 1, "home", 4.00, None, 1, None, None),
    ("Seed potatoes", "plants", "kg", 0, 3, "home", 3.00, None, 1, 1.0, 0.0015),
    ("Scaffold boards", "build", "each", 0, 2, "home", 22.00, None, 1, 18, 0.02),
    ("Slabs", "build", "each", 0, 2, "home", 4.00, None, 1, 20, 0.01),
    ("Hardcore", "build", "tonne", 0, 1, "shed", 60.00, None, 1, 1000, 0.7),
]

# §34 expected lives
ASSET_LIVES = {
    "Shed": 15, "Shed base": 25, "Polytunnel frame": 12, "Polytunnel polythene": 5,
    "Water butts": 10, "Raised beds": 8, "Hand tools": 10, "Wheelbarrow": 8,
    "Hose and reel": 6, "Netting and fleece": 3, "Compost bays": 5,
}
