"""Seed data: zones, crops, jobs, rotation, trouble spots, opening stock.

Geometry is the single source of truth for both the sun model and the map,
so the drawing and the arithmetic can never disagree.
"""

# id, name, type, x, y, w, d, height, growable, colour, notes
ZONES = [
    ("path",   "Main path",        "path",      0.0,  0.0,  1.0, 11.4, 0.0, 0, "#6E6A5A",
     "Woodchip over membrane. Never needs mowing."),
    ("b1",     "Bed 1",            "bed",       1.3,  0.4,  1.2,  2.4, 0.3, 1, "#7BA05B",
     "Raised bed 2.4 x 1.2 m. Never walked on."),
    ("b2",     "Bed 2",            "bed",       3.1,  0.4,  1.2,  2.4, 0.3, 1, "#7BA05B",
     "Raised bed 2.4 x 1.2 m. Never walked on."),
    ("poll",   "Pollinator bed",   "bed",       4.9,  0.4,  1.0,  2.4, 0.6, 1, "#5C7FBF",
     "Borage, phacelia, calendula. Pollination, not decoration."),
    ("b3",     "Bed 3",            "bed",       1.3,  3.2,  1.2,  2.4, 0.3, 1, "#7BA05B",
     "Raised bed 2.4 x 1.2 m. Brassicas year one — net from planting out."),
    ("b4",     "Bed 4",            "bed",       3.1,  3.2,  1.2,  2.4, 0.3, 1, "#7BA05B",
     "Raised bed 2.4 x 1.2 m. Never walked on."),
    ("spud",   "Potato ground",    "open",      1.3,  6.0,  4.6,  3.0, 0.2, 1, "#8B6F9E",
     "Open ground, no bed. Potatoes break the soil up for you."),
    ("green",  "Green manure strip", "green",   1.3,  9.2,  4.6,  1.1, 0.0, 1, "#3E5B3A",
     "Phacelia. Counts as cultivated at inspection and feeds the soil."),
    ("hard",   "Hardstanding",     "hard",      6.2,  0.3,  2.6,  1.6, 0.0, 0, "#565349",
     "Every barrow load lands here. No vehicle access to the plot."),
    ("shed",   "Shed",             "structure", 9.1,  0.3,  1.85, 1.25, 2.1, 0, "#48584F",
     "6 x 4 ft maximum under Association rules. Roof feeds the butts."),
    ("butt",   "Water butts",      "water",     9.1,  1.9,  1.5,  0.9, 1.0, 0, "#3D6B78",
     "Three 210 L. The only water source November to March."),
    ("green2", "Green manure (SE)", "green",    6.2,  2.2,  2.2,  5.0, 0.0, 1, "#3E5B3A",
     "Second green manure area, rotates with the potato ground."),
    ("tun",    "Polytunnel",       "structure", 8.6,  3.2,  2.0,  4.0, 2.0, 1, "#9DBDB8",
     "4 x 2 m maximum on a full plot. Never receives rain."),
    ("bean",   "Beans",            "open",      6.2,  7.6,  2.2,  1.0, 1.8, 1, "#C1443A",
     "Wigwams. Pick every 2-3 days or cropping stops."),
    ("comp",   "Compost bays",     "compost",   8.8,  7.6,  2.2,  1.0, 1.0, 0, "#6B4F3A",
     "Two pallet bays. Turn monthly."),
    ("fruit",  "Soft fruit",       "perennial", 6.2,  9.0,  5.0,  1.3, 1.2, 1, "#A8324A",
     "Rhubarb and currants. Perennial, plant once. No harvest year one."),
    ("clear",  "Keep-clear fence strip", "clear", 0.0, 10.4, 11.4, 1.0, 0.0, 0, "#2A3730",
     "One metre fence break required by the tenancy. NEVER a growing zone."),
]

# id, name, zone, family, si_from, si_to, sd_from, sd_to, po_from, po_to,
# h_from, h_to, spacing, net, support, fruiting, notes
CROPS = [
    ("garlic", "Garlic", "b1", "allium", None, None, None, None, "10-01", "12-31",
     "06-01", "07-31", 15, 0, 0, 0, "Needs a cold spell. Cloves pointy end up."),
    ("onion", "Onion (sets)", "b1", "allium", None, None, None, None, "03-01", "04-30",
     "08-01", "09-30", 10, 0, 0, 0, "Autumn sets Sep-Oct also possible."),
    ("broadbean", "Broad beans", "b2", "legume", None, None, "02-01", "04-30", None, None,
     "06-01", "07-31", 20, 0, 1, 0, "Autumn sowing crops earlier and dodges blackfly."),
    ("beetroot", "Beetroot", "b2", "chenopod", None, None, "04-01", "07-31", None, None,
     "06-01", "10-31", 10, 0, 0, 0, "Succession every 3 weeks."),
    ("chard", "Chard", "b2", "chenopod", None, None, "04-01", "07-31", None, None,
     "06-01", "04-30", 25, 0, 0, 0, "Overwinters. Cut-and-come-again."),
    ("spinach", "Perpetual spinach", "b2", "chenopod", None, None, "04-01", "07-31", None, None,
     "06-01", "04-30", 25, 0, 0, 0, "Same treatment as chard."),
    ("kale", "Kale", "b3", "brassica", "04-01", "06-30", None, None, "06-01", "07-31",
     "10-01", "04-30", 45, 1, 0, 0, "Net from planting out. Pigeons strip it."),
    ("turnip", "Turnip", "b3", "brassica", None, None, "03-01", "08-31", None, None,
     "05-01", "10-31", 15, 1, 0, 0, "Net. Fast - 6 to 8 weeks."),
    ("radish", "Radish", "b3", "brassica", None, None, "03-01", "09-30", None, None,
     "04-01", "10-31", 3, 1, 0, 0, "Succession every 2 weeks. 4 weeks to crop."),
    ("salad", "Salad leaves", "b4", "mixed", None, None, "03-01", "09-30", None, None,
     "04-01", "11-30", 10, 0, 0, 0, "Succession every 2-3 weeks. Fleece early and late."),
    ("courgette", "Courgette", "b4", "cucurbit", "04-20", "04-30", None, None, "05-25", "06-10",
     "07-01", "09-30", 90, 0, 0, 1, "Pick every 2-3 days or it stops."),
    ("runnerbean", "Runner beans", "bean", "legume", "05-01", "05-31", "05-20", "06-15",
     "06-01", "06-15", "07-01", "10-31", 20, 0, 1, 1, "Pick every 2-3 days. Wigwam up first."),
    ("frenchbean", "French beans", "bean", "legume", "05-01", "05-31", "05-20", "06-30",
     "06-01", "06-30", "07-01", "09-30", 15, 0, 1, 1, "As runner beans."),
    ("potato_first", "Potato - first early", "spud", "solanum", None, None, None, None,
     "03-20", "04-05", "06-01", "07-31", 30, 0, 0, 0, "Chit Feb. Earth up from 21 days."),
    ("potato_second", "Potato - second early", "spud", "solanum", None, None, None, None,
     "04-01", "04-14", "07-01", "08-31", 35, 0, 0, 0, "Chit Feb."),
    ("potato_main", "Potato - maincrop", "spud", "solanum", None, None, None, None,
     "04-14", "04-30", "09-01", "09-30", 40, 0, 0, 0, "Cure 2 weeks before storing."),
    ("tomato", "Tomato", "tun", "solanum", "02-01", "03-31", None, None, "05-10", "05-25",
     "07-01", "10-31", 45, 0, 1, 1, "Side-shoot weekly. 6-8 plants down one side."),
    ("cucumber", "Cucumber", "tun", "cucurbit", "04-01", "04-30", None, None, "05-20", "06-05",
     "07-01", "09-30", 45, 0, 1, 1, "Train up mesh. 4-5 plants."),
    ("chilli", "Pepper / chilli", "tun", "solanum", "02-01", "03-31", None, None, "05-10", "05-25",
     "08-01", "10-31", 40, 0, 1, 1, "Needs the warmth - won't crop outdoors here."),
    ("basil", "Basil", "tun", "mixed", "03-01", "05-31", None, None, "05-01", "05-31",
     "06-01", "09-30", 20, 0, 0, 0, "Plant among the tomatoes."),
    ("marigold", "French marigold", "tun", "flower", "03-01", "04-30", None, None, "05-01", "05-31",
     None, None, 20, 0, 0, 0, "Deters whitefly. Not a crop."),
    ("rhubarb", "Rhubarb", "fruit", "perennial", None, None, None, None, "11-01", "03-31",
     "04-01", "06-30", 90, 0, 0, 0, "DO NOT harvest in year one. Let it establish."),
    ("blackcurrant", "Blackcurrant", "fruit", "perennial", None, None, None, None, "11-01", "03-31",
     "07-01", "07-31", 150, 1, 0, 1, "Prune a third of old wood each winter."),
    ("redcurrant", "Redcurrant", "fruit", "perennial", None, None, None, None, "11-01", "03-31",
     "07-01", "07-31", 150, 1, 0, 1, "Net against birds from June."),
    ("herbs", "Chives, thyme, oregano", "poll", "perennial", None, None, None, None, "03-01", "05-31",
     "01-01", "12-31", 25, 0, 0, 0, "Bed ends. Flower well for bees."),
    ("borage", "Borage", "poll", "flower", None, None, "03-01", "05-31", None, None,
     None, None, 45, 0, 0, 0, "Best single plant for courgettes and beans. Self-seeds."),
    ("phacelia", "Phacelia", "green", "flower", None, None, "03-01", "09-30", None, None,
     None, None, 10, 0, 0, 0, "Pollinators and green manure. Cut before it seeds."),
    ("calendula", "Calendula", "poll", "flower", None, None, "03-01", "05-31", None, None,
     None, None, 30, 0, 0, 0, "Hoverflies - their larvae eat aphids."),
    ("poachedegg", "Poached egg plant", "poll", "flower", None, None, "03-01", "04-30", None, None,
     None, None, 20, 0, 0, 0, "Hoverflies. Low, good bed edging."),
    ("nasturtium", "Nasturtium", "bean", "flower", None, None, "04-01", "05-31", None, None,
     None, None, 30, 0, 0, 0, "Trap crop - blackfly go for it instead of beans."),
    ("cornflower", "Cornflower", "poll", "flower", None, None, "03-01", "05-31", None, None,
     None, None, 25, 0, 0, 0, "General pollinator draw."),
    ("sunflower", "Sunflower", "poll", "flower", None, None, "04-01", "05-31", None, None,
     None, None, 45, 0, 1, 0, "Height on the exposed side."),
    ("sweetpea", "Sweet pea", "poll", "flower", "02-01", "04-30", None, None, "04-15", "05-15",
     None, None, 20, 0, 1, 0, "Cut flowers, pulls pollinators in."),
]


# Which of the two day-to-day lists a job belongs on, by category. Growing is
# the food: sowing it, keeping it alive, picking it. Maintenance is the plot and
# its structures: weeds, paths, compost, shed, tunnel, the Association. A job
# passes stream= to override the default where the category is a poor guide.
DEFAULT_STREAM = {
    "build": "setup", "soil": "growing", "sow": "growing", "plant": "growing",
    "tend": "growing", "harvest": "growing",
    "compost": "maintenance", "maintain": "maintenance", "admin": "maintenance",
}
STREAMS = ("setup", "growing", "maintenance")


def J(title, category, owner, mins, rule_type, params, **kw):
    d = dict(title=title, category=category, owner=owner, est_minutes=mins,
             rule_type=rule_type, rule_params=params)
    d.update(kw)
    d.setdefault("stream", DEFAULT_STREAM.get(category, "maintenance"))
    return d


# --- Part one: getting the plot ready to grow food (§19 jobs 1-21).
#
# One-offs, chained by dependency, and numbered in the order they are actually
# done. `step` is the guide; the dependencies are the enforcement, and the two
# must agree - a step may only depend on a lower-numbered one. GROWING_READY
# below marks the point where food can go in the ground; everything after it is
# the shed and the tunnel, which are worth having and are not worth waiting for.
#
# `notes` on a setup job is what the step is for, in a sentence. It is the line
# the guide prints under the title, so it says why rather than restating what.
BUILD = [
    J("Apply in writing for shed and polytunnel permission", "admin", "Site", 30,
      "dependency", {}, one_off=1, consequence=5, step=1, stream="setup",
      key="permission",
      notes="First, because the Committee takes weeks and half the build waits on it. "
            "Nothing else here depends on the answer, so post it and carry on."),
    J("Clear the plot - strim and remove rubbish", "build", "Both", 240, "dependency",
      {}, one_off=1, consequence=4, step=2, stream="setup", key="clear_plot",
      notes="Everything else needs to be able to see the ground. This is also the "
            "only weeding that matters until there is something to weed around."),
    J("Mark out zones with string lines", "build", "Both", 90, "dependency",
      {"depends_on": ["clear_plot"]}, one_off=1, consequence=3, step=3, stream="setup",
      key="mark_out",
      notes="Beds, paths and the one metre fence strip, pegged out before anything "
            "is built. Moving a string line costs nothing; moving a bed costs a day."),
    J("Survey the fall across the plot", "build", "Site", 60, "dependency",
      {"depends_on": ["mark_out"]}, one_off=1, consequence=2, step=4, stream="setup",
      key="survey",
      notes="Where the water goes. Clay plus an unnoticed fall is how a path becomes "
            "a stream and a bed becomes a puddle."),
    J("Lay the hardstanding", "build", "Site", 240, "dependency",
      {"depends_on": ["survey"]}, one_off=1, consequence=3, step=5, stream="setup",
      zone_id="hard", stock_needs=[["Hardcore", 1], ["Slabs", 12]], key="hardstanding",
      notes="Every barrow load lands here, and there is no vehicle access. Build it "
            "before the deliveries, not after."),
    J("Build the compost bays from pallets", "build", "Site", 120, "dependency",
      {"depends_on": ["mark_out"]}, one_off=1, consequence=2, step=6, stream="setup",
      zone_id="comp", key="compost_bays",
      notes="Somewhere for the clearance waste to go, so it is not still in a heap "
            "at the first inspection."),
    J("Build the raised beds", "build", "Both", 360, "dependency",
      {"depends_on": ["mark_out"]}, one_off=1, consequence=4, step=7, stream="setup",
      stock_needs=[["Scaffold boards", 12]], key="build_beds",
      notes="Four beds, 2.4 x 1.2 m. Raised beds are how you grow on clay without "
            "waiting for the clay to agree."),
    J("Fill the beds with compost and topsoil", "soil", "Both", 300, "dependency",
      {"depends_on": ["build_beds"]}, one_off=1, consequence=4, step=8, stream="setup",
      stock_needs=[["Multipurpose compost", 400]], key="fill_beds",
      notes="The last step before food. Once the beds are full the plot can be sown, "
            "and the growing list starts appearing on its own."),
    J("Lay membrane and woodchip on the paths", "build", "Both", 180, "dependency",
      {"depends_on": ["build_beds"]}, one_off=1, consequence=2, step=9, stream="setup",
      zone_id="path", stock_needs=[["Woodchip", 2000]], key="paths",
      notes="Clay paths in winter are the reason people stop visiting in winter."),
    J("Confirm tunnel placement approved by Committee", "admin", "Site", 20, "dependency",
      {"depends_on": ["permission"]}, one_off=1, consequence=5, step=10, stream="setup",
      key="tunnel_approved",
      notes="Placement is approved separately from permission. Check it before "
            "levelling ground you may have to un-level."),
    J("Build the shed base", "build", "Site", 300, "dependency",
      {"depends_on": ["hardstanding", "permission"]}, one_off=1, consequence=3,
      step=11, stream="setup", zone_id="shed", needs_permission=1, key="shed_base",
      notes="Level and free-draining. A shed on a bad base is a shed with a bad door."),
    J("Erect the shed", "build", "Both", 300, "dependency",
      {"depends_on": ["shed_base"]}, one_off=1, consequence=3, step=12, stream="setup",
      zone_id="shed", needs_permission=1, key="shed",
      notes="6 x 4 ft maximum under Association rules. Tools stop living in the car."),
    J("Fit guttering and connect water butts", "build", "Site", 120, "dependency",
      {"depends_on": ["shed"]}, one_off=1, consequence=4, step=13, stream="setup",
      zone_id="butt", key="butts",
      notes="The tap is off November to March. Three 210 L butts off the shed roof "
            "are the only water on the plot for five months of the year."),
    J("Level the polytunnel site", "soil", "Both", 180, "dependency",
      {"depends_on": ["tunnel_approved"]}, one_off=1, consequence=3, step=14,
      stream="setup", zone_id="tun", needs_permission=1, key="tunnel_site",
      notes="Flat within a few centimetres, or the frame will not square up."),
    J("Erect the polytunnel frame", "build", "Both", 300, "dependency",
      {"depends_on": ["tunnel_site"]}, one_off=1, consequence=3, step=15, stream="setup",
      zone_id="tun", needs_permission=1, key="tunnel_frame",
      notes="4 x 2 m maximum on a full plot."),
    J("Fit the tunnel polythene", "build", "Both", 240, "dependency",
      {"depends_on": ["tunnel_frame"]}, one_off=1, consequence=4, step=16, stream="setup",
      zone_id="tun", needs_permission=1, key="tunnel_poly",
      notes="Hard block over 10 kph wind - two people and a sheet of polythene in a "
            "breeze is how polythene ends up in the hedge. Tomatoes and cucumbers "
            "start appearing on the growing list once this is done."),
]

# The step at which the plot can grow food. Steps after it are the shed and the
# tunnel: real improvements, but nothing is waiting on them to be sown.
GROWING_READY = 8

# --- Part two: the day-to-day year, once the plot is set up (§4, §14, §15).
#
# Every job here that assumes something exists says so with requires=[...]. A
# plot with nothing on it should not be asked for twenty minutes of weeding, or
# told to water beds that have not been built - the setup guide is the whole of
# the work until the ground is ready, and a list of jobs for an imaginary plot
# is how a system gets ignored.
JOBS = [
    # every visit
    J("20 minutes weeding on arrival", "tend", "Both", 20, "every_visit", {},
      every_visit=1, consequence=3, stream="maintenance", requires=["clear_plot"]),
    J("Open the tunnel (before 9am)", "tend", "Either", 2, "every_visit",
      {"from_md": "03-01", "to_md": "10-31"}, every_visit=1, consequence=4, zone_id="tun", requires=["tunnel_poly"]),
    J("Shut the tunnel (before dusk)", "tend", "Either", 2, "every_visit",
      {"from_md": "03-01", "to_md": "10-31"}, every_visit=1, consequence=4, zone_id="tun", requires=["tunnel_poly"]),
    J("Log the visit", "admin", "Either", 1, "every_visit", {}, every_visit=1, consequence=2),

    # --- admin and compliance (§14) ---
    J("Pay the subscription", "admin", "Site", 15, "fixed_window",
      {"start_md": "01-01", "end_md": "01-31"}, consequence=5),
    J("Tidy sweep and path edges before inspection", "tend", "Both", 45, "inspection_linked",
      {"days_before": 3}, consequence=4, stream="maintenance", requires=["clear_plot"]),
    J("Plot inspection due", "admin", "Both", 0, "inspection_linked",
      {"days_before": 0}, consequence=5),
    J("Review seed viability, bin what has expired", "admin", "Grower", 30, "fixed_window",
      {"start_md": "01-05", "end_md": "01-25"}, consequence=3, stream="growing"),
    J("Order seeds and seed potatoes", "admin", "Grower", 45, "fixed_window",
      {"start_md": "12-01", "end_md": "01-31"}, consequence=4, stream="growing"),
    J("Plan next year and propose the rotation", "admin", "Both", 60, "fixed_window",
      {"start_md": "11-01", "end_md": "11-30"}, consequence=3, stream="growing"),

    # --- January ---
    J("Turn the compost", "compost", "Either", 30, "recurring",
      {"interval_days": 30}, zone_id="comp", consequence=1, requires=["compost_bays"]),
    J("Empty compost bays onto the beds", "compost", "Both", 120, "fixed_window",
      {"start_md": "01-05", "end_md": "02-15"}, zone_id="comp", consequence=2,
      requires=["compost_bays", "fill_beds"]),
    J("Check shed felt, hinges and padlock", "maintain", "Site", 20, "recurring",
      {"interval_days": 90}, zone_id="shed", consequence=3, requires=["shed"]),
    J("Check tunnel polythene tension, doors and anchoring", "maintain", "Site", 25, "recurring",
      {"interval_days": 90}, zone_id="tun", consequence=4, requires=["tunnel_poly"]),
    J("Clean and oil the tools", "maintain", "Either", 40, "recurring",
      {"interval_days": 90}, consequence=2),

    # --- February ---
    J("Rough-dig the potato ground", "soil", "Both", 120, "fixed_window",
      {"start_md": "02-01", "end_md": "03-10"}, zone_id="spud", consequence=3,
      requires=["clear_plot"]),
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
      {"start_md": "02-15", "end_md": "04-15"}, zone_id="b2", consequence=3,
      crop_id="broadbean", stock_needs=[["Broad bean seed", 1]], requires=["fill_beds"]),
    J("Plant garlic if not done in autumn", "plant", "Grower", 30, "fixed_window",
      {"start_md": "02-01", "end_md": "02-28"}, zone_id="b1", consequence=3, crop_id="garlic", requires=["fill_beds"]),

    # --- March ---
    J("Plant the onion sets", "plant", "Grower", 45, "fixed_window",
      {"start_md": "03-01", "end_md": "04-30"}, zone_id="b1", consequence=3,
      crop_id="onion", stock_needs=[["Onion sets", 1]], requires=["fill_beds"]),
    J("Sow the green manure strip", "sow", "Either", 30, "fixed_window",
      {"start_md": "03-01", "end_md": "04-30"}, zone_id="green", consequence=2,
      stock_needs=[["Phacelia seed", 1]], requires=["clear_plot"]),
    J("Sow the pollinator bed", "sow", "Grower", 40, "fixed_window",
      {"start_md": "03-15", "end_md": "05-15"}, zone_id="poll", consequence=2, requires=["fill_beds"]),
    J("First weeding push of the year", "tend", "Both", 90, "fixed_window",
      {"start_md": "03-01", "end_md": "03-31"}, consequence=3, stream="maintenance",
      requires=["clear_plot"]),

    # --- succession sowings (§12) ---
    J("Sow radish", "sow", "Grower", 15, "succession",
      {"interval_days": 14, "window_start": "03-01", "window_end": "09-30", "max_sowings": 12},
      zone_id="b3", crop_id="radish", consequence=2, stock_needs=[["Radish seed", 1]], requires=["fill_beds"]),
    J("Sow salad leaves", "sow", "Grower", 20, "succession",
      {"interval_days": 18, "window_start": "03-01", "window_end": "09-30", "max_sowings": 11},
      zone_id="b4", crop_id="salad", consequence=3, stock_needs=[["Salad seed", 1]], requires=["fill_beds"]),
    J("Sow beetroot", "sow", "Grower", 25, "succession",
      {"interval_days": 21, "window_start": "04-01", "window_end": "07-31", "max_sowings": 6},
      zone_id="b2", crop_id="beetroot", consequence=3, stock_needs=[["Beetroot seed", 1]], requires=["fill_beds"]),

    # --- April, peak month ---
    J("Plant the first early potatoes", "plant", "Site", 60, "crop_linked",
      {"crop_id": "potato_first", "anchor": "plant", "offset_days": 0}, zone_id="spud",
      crop_id="potato_first", consequence=4, requires=["clear_plot"]),
    J("Plant the second early potatoes", "plant", "Site", 60, "crop_linked",
      {"crop_id": "potato_second", "anchor": "plant", "offset_days": 0}, zone_id="spud",
      crop_id="potato_second", consequence=4, requires=["clear_plot"]),
    J("Plant the maincrop potatoes", "plant", "Site", 90, "crop_linked",
      {"crop_id": "potato_main", "anchor": "plant", "offset_days": 0}, zone_id="spud",
      crop_id="potato_main", consequence=4, requires=["clear_plot"]),
    J("Earth up the potatoes", "tend", "Site", 40, "crop_linked",
      {"crop_id": "potato_first", "anchor": "plant", "offset_days": 21,
       "repeat_days": 14, "repeat_count": 3}, zone_id="spud", crop_id="potato_first",
      consequence=4, requires=["plant_the_first_early_potatoes"]),
    J("Plant beetroot, chard and kale plugs", "plant", "Grower", 45, "fixed_window",
      {"start_md": "04-15", "end_md": "06-15"}, zone_id="b3", consequence=3, requires=["fill_beds"]),
    J("Net the brassicas", "tend", "Grower", 25, "crop_linked",
      {"crop_id": "kale", "anchor": "plant", "offset_days": 0}, zone_id="b3",
      crop_id="kale", consequence=5, stock_needs=[["Butterfly netting", 1]],
      notes="Net from the day you plant out, not when damage appears.", requires=["fill_beds"]),
    J("Sow beans direct", "sow", "Grower", 40, "fixed_window",
      {"start_md": "05-20", "end_md": "06-15"}, zone_id="bean", consequence=3,
      requires=["clear_plot"]),

    # --- May ---
    J("Plant out the tomatoes in the tunnel", "plant", "Grower", 60, "crop_linked",
      {"crop_id": "tomato", "anchor": "plant", "offset_days": 0}, zone_id="tun",
      crop_id="tomato", consequence=4, requires=["tunnel_poly"]),
    J("Plant out the cucumbers in the tunnel", "plant", "Grower", 30, "crop_linked",
      {"crop_id": "cucumber", "anchor": "plant", "offset_days": 0}, zone_id="tun",
      crop_id="cucumber", consequence=3, requires=["tunnel_poly"]),
    J("Build the bean wigwams", "build", "Site", 60, "fixed_window",
      {"start_md": "05-01", "end_md": "05-25"}, zone_id="bean", consequence=4,
      stream="growing", stock_needs=[["Bean canes", 20], ["Twine", 1]],
      requires=["clear_plot"]),
    J("Plant out the courgettes", "plant", "Grower", 30, "crop_linked",
      {"crop_id": "courgette", "anchor": "plant", "offset_days": 0}, zone_id="b4",
      crop_id="courgette", consequence=4, requires=["fill_beds"]),
    J("Plant out the beans", "plant", "Grower", 45, "crop_linked",
      {"crop_id": "runnerbean", "anchor": "plant", "offset_days": 0}, zone_id="bean",
      crop_id="runnerbean", consequence=4, requires=["build_the_bean_wigwams"]),
    J("Plant nasturtiums at the base of the beans", "plant", "Grower", 15, "fixed_window",
      {"start_md": "05-15", "end_md": "06-15"}, zone_id="bean", consequence=2, requires=["build_the_bean_wigwams"]),

    # --- June onwards ---
    J("Tie in and side-shoot the tomatoes", "tend", "Grower", 20, "recurring",
      {"interval_days": 7, "from_md": "06-01", "to_md": "09-30"}, zone_id="tun",
      crop_id="tomato", consequence=4, requires=["tunnel_poly"]),
    J("Check the netting", "tend", "Either", 10, "recurring",
      {"interval_days": 14, "from_md": "05-01", "to_md": "10-31"}, consequence=4, requires=["net_the_brassicas"]),
    J("Pick beans and courgettes", "harvest", "Either", 25, "recurring",
      {"interval_days": 3, "from_md": "07-01", "to_md": "10-15"}, consequence=5,
      notes="Miss this and the plants stop cropping.", requires=["plant_out_the_courgettes", "plant_out_the_beans"]),
    J("Harvest broad beans, salad and garlic", "harvest", "Either", 40, "fixed_window",
      {"start_md": "06-01", "end_md": "07-31", "frequency": "weekly"}, consequence=4, requires=["sow_broad_beans_direct"]),
    J("Harvest tomatoes and cucumbers", "harvest", "Either", 20, "recurring",
      {"interval_days": 4, "from_md": "07-01", "to_md": "10-15"}, zone_id="tun", consequence=4, requires=["tunnel_poly"]),
    J("Lift the first early potatoes", "harvest", "Both", 60, "crop_linked",
      {"crop_id": "potato_first", "anchor": "harvest", "offset_days": 0}, zone_id="spud",
      crop_id="potato_first", consequence=4, requires=["plant_the_first_early_potatoes"]),
    J("Plant the rhubarb crowns and currant bushes", "plant", "Both", 120, "fixed_window",
      {"start_md": "11-01", "end_md": "03-15"}, zone_id="fruit", consequence=3, one_off=1,
      key="plant_fruit", requires=["clear_plot"],
      notes="Bare root and crowns only. No harvest from the rhubarb in year one."),
    J("Summer prune the currants", "tend", "Grower", 30, "fixed_window",
      {"start_md": "07-01", "end_md": "08-15"}, zone_id="fruit", consequence=2, requires=["plant_fruit"]),
    J("Sow autumn salad", "sow", "Grower", 20, "fixed_window",
      {"start_md": "08-01", "end_md": "09-10"}, zone_id="b4", consequence=2, requires=["fill_beds"]),

    # --- September ---
    J("Lift the maincrop potatoes", "harvest", "Both", 120, "crop_linked",
      {"crop_id": "potato_main", "anchor": "harvest", "offset_days": 0}, zone_id="spud",
      crop_id="potato_main", consequence=5, requires=["plant_the_maincrop_potatoes"]),
    J("Cure and store the maincrop potatoes", "harvest", "Grower", 45, "crop_linked",
      {"crop_id": "potato_main", "anchor": "harvest", "offset_days": 14}, consequence=4, requires=["lift_the_maincrop_potatoes"]),
    J("Clear the tunnel", "tend", "Both", 90, "fixed_window",
      {"start_md": "09-20", "end_md": "10-31"}, zone_id="tun", consequence=3, requires=["tunnel_poly"]),
    J("Dry and store the onions", "harvest", "Grower", 45, "fixed_window",
      {"start_md": "08-15", "end_md": "09-30"}, consequence=4, requires=["plant_the_onion_sets"]),
    J("Sow green manure on cleared ground", "sow", "Either", 30, "fixed_window",
      {"start_md": "09-01", "end_md": "10-15"}, consequence=3, requires=["clear_plot"]),
    J("Collect seed", "admin", "Grower", 30, "fixed_window",
      {"start_md": "08-15", "end_md": "09-30"}, consequence=1, stream="growing"),

    # --- October ---
    J("Clear the beds and mulch", "soil", "Both", 150, "fixed_window",
      {"start_md": "10-01", "end_md": "11-15"}, consequence=3,
      stock_needs=[["Multipurpose compost", 200]], requires=["fill_beds"]),
    J("Plant garlic and overwintering onions", "plant", "Grower", 45, "fixed_window",
      {"start_md": "10-01", "end_md": "12-15"}, zone_id="b1", crop_id="garlic", consequence=4, requires=["fill_beds"]),
    J("Fill every water butt before the tap goes off", "maintain", "Site", 30, "fixed_window",
      {"start_md": "10-01", "end_md": "10-31"}, zone_id="butt", consequence=5,
      notes="The tap is off November to March. This is the last chance.", requires=["butts"]),
    J("Check the tunnel before the winter storms", "maintain", "Site", 30, "fixed_window",
      {"start_md": "10-15", "end_md": "11-15"}, zone_id="tun", consequence=4, requires=["tunnel_poly"]),
    J("Top up the path woodchip", "maintain", "Both", 90, "fixed_window",
      {"start_md": "10-01", "end_md": "11-30"}, zone_id="path", consequence=2,
      stock_needs=[["Woodchip", 1000]], requires=["paths"]),

    # --- November and December ---
    J("Harvest kale", "harvest", "Either", 15, "recurring",
      {"interval_days": 10, "from_md": "10-01", "to_md": "04-30"}, zone_id="b3", consequence=3, requires=["fill_beds"]),
    J("Winter prune the currants", "tend", "Grower", 45, "fixed_window",
      {"start_md": "12-01", "end_md": "02-28"}, zone_id="fruit", consequence=2, requires=["plant_fruit"]),
    J("Cut down and lay the green manure", "soil", "Both", 60, "fixed_window",
      {"start_md": "02-15", "end_md": "04-10"}, zone_id="green", consequence=3,
      requires=["sow_the_green_manure_strip"], notes="Before it sets seed."),
    J("Top up the bed compost", "soil", "Both", 90, "fixed_window",
      {"start_md": "03-01", "end_md": "04-15"}, consequence=3,
      stock_needs=[["Multipurpose compost", 300]], requires=["fill_beds"]),

    # --- weather-conditional (§3) ---
    J("Water the beds and pollinator bed", "tend", "Either", 25, "weather_conditional",
      {"condition": "dry_3d", "from_md": "04-01", "to_md": "09-30"}, consequence=4,
      requires=["fill_beds"]),
    J("Water the polytunnel", "tend", "Either", 10, "weather_conditional",
      {"condition": "always", "from_md": "03-01", "to_md": "10-31"}, zone_id="tun",
      consequence=5, notes="The tunnel never gets rain. Catches everyone out.", requires=["tunnel_poly"]),
    J("Slug patrol after dark", "tend", "Either", 20, "weather_conditional",
      {"condition": "slug_night", "from_md": "04-01", "to_md": "06-30"}, consequence=4,
      zone_id="clear", requires=["fill_beds"],
      notes="Start in the damp shaded SE corner."),
    J("Ventilate the tunnel - open by 9am, shut by dusk", "tend", "Either", 5,
      "weather_conditional", {"condition": "warm_day", "from_md": "03-01", "to_md": "10-31"},
      zone_id="tun", consequence=4, requires=["tunnel_poly"]),
    J("Fleece the tender plants - frost forecast", "tend", "Either", 25, "weather_conditional",
      {"condition": "frost_risk", "from_md": "03-01", "to_md": "05-31"}, consequence=5,
      stock_needs=[["Fleece", 1]], requires=["fill_beds"]),
    J("Check tunnel anchoring and bean wigwams - gale forecast", "maintain", "Site", 20,
      "weather_conditional", {"condition": "gale_risk", "from_md": "01-01", "to_md": "12-31"},
      consequence=5, requires=["tunnel_frame"]),
    J("Top up the water butts from the tap", "maintain", "Site", 20, "weather_conditional",
      {"condition": "butts_low", "from_md": "04-01", "to_md": "10-31"}, zone_id="butt",
      consequence=3, requires=["butts"]),

    # --- long cycle (§15) ---
    J("Replace the tunnel polythene", "maintain", "Both", 300, "recurring",
      {"interval_days": 1826, "after_job": "tunnel_poly"}, zone_id="tun", consequence=4,
      notes="Budget £120-180. The sinking fund exists for this."),
]

# §13 rotation, four groups moving one bed a year
ROTATION = {
    1: {"b1": "alliums", "b2": "roots_leaves", "b3": "brassicas", "b4": "cucurbits_salad",
        "spud": "potatoes", "green": "green_manure", "green2": "green_manure"},
    2: {"b1": "cucurbits_salad", "b2": "alliums", "b3": "roots_leaves", "b4": "brassicas",
        "spud": "green_manure", "green": "potatoes", "green2": "potatoes"},
    3: {"b1": "brassicas", "b2": "cucurbits_salad", "b3": "alliums", "b4": "roots_leaves",
        "spud": "potatoes", "green": "green_manure", "green2": "green_manure"},
    4: {"b1": "roots_leaves", "b2": "brassicas", "b3": "cucurbits_salad", "b4": "alliums",
        "spud": "green_manure", "green": "potatoes", "green2": "potatoes"},
}
GROUP_FAMILIES = {
    "alliums": ["allium"], "roots_leaves": ["chenopod"], "brassicas": ["brassica"],
    "cucurbits_salad": ["cucurbit", "mixed"], "potatoes": ["solanum"], "green_manure": [],
}
GROUP_NAMES = {
    "alliums": "Onion & garlic", "roots_leaves": "Beetroot & chard",
    "brassicas": "Kale & turnip", "cucurbits_salad": "Courgettes & salad",
    "potatoes": "Potatoes", "green_manure": "Green manure",
}

# §23 the nine derived trouble spots
TROUBLE = [
    (1.9, 10.0, "Slugs", "pest", "High",
     "Damp, shaded and against the scrub - the classic slug reservoir. They shelter in "
     "long grass and the compost bays by day, then travel up to 10 m at night.",
     "Patrol after rain, April to June, after dark. Keep the fence strip cut short."),
    (5.7, 9.85, "Compost bays", "pest", "Medium",
     "Warm, damp and full of organic matter. Slugs breed here, and anything that goes in "
     "seeding comes back out spread across the beds.",
     "Never compost a plant that has flowered. Turn monthly - heat kills seed."),
    (9.0, 10.6, "Woodland seed rain", "weed", "High",
     "Wind-blown birch and willow seed, plus bramble suckering under the fence. The highest "
     "weed load on the plot and it never stops.",
     "The one-metre fence strip must stay clear anyway. Strim it monthly."),
    (1.6, 2.4, "Mud and compaction", "ground", "High",
     "The gateway and hardstanding take every barrow load, and with no vehicle access that is "
     "every bag of compost and the shed itself. Clay compacts fast.",
     "Keep woodchip topped up and never wheel across soft ground when wet."),
    (3.3, 7.2, "Wind exposure", "weather", "Medium",
     "Prevailing wind is south-westerly and the open side takes it. The polytunnel is the most "
     "wind-vulnerable thing on the plot.",
     "Anchor the polythene, check tension quarterly, keep repair tape in the shed."),
    (8.2, 4.6, "Pigeons", "bird", "High",
     "The brassica bed sits under a clear sightline from the trees. Pigeons can strip kale in "
     "an afternoon.",
     "Net from the day you plant out, not when damage appears."),
    (2.0, 5.0, "Frost pocket", "weather", "Low",
     "Cold air drains downhill and pools at the low point.",
     "Fleece tender plants here first. Nothing tender out before the third week of May."),
    (10.2, 9.0, "Dry shadow", "water", "Medium",
     "Ground within two metres of mature trees is drier all season - the roots take the water "
     "first.",
     "Soft fruit copes; annuals do not. Mulch here in spring."),
    (9.6, 5.2, "Tunnel - never rained on", "water", "Certain",
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
