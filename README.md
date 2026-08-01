# Allotment

Plot 129.8 m², Albert Village Allotment Association. A jobs engine that tells you
what needs doing today, and the ledger that tells you what it really cost.

Python 3.9+. Locally it is standard library only — no pip install, no framework,
no build step, everything in one SQLite file. The hosted copy runs the same code
against Postgres, because a serverless filesystem cannot keep a database file.

```bash
./plot init          # create plot.db, seed the plot, create the login
./plot today         # the daily view
./plot serve         # the web view, on http://127.0.0.1:8765
```

## The daily view

```
SATURDAY 1 AUGUST          Rain 3d: 0mm   Max 21°C   Min 10°C   Soil: workable
  1. Water the beds and pollinator bed            Either     25m
     Only 0 mm rain in the last 3 days
  2. Apply in writing for shed and polytunnel per Site       30m
     Window closes in 152 days
  3. Clean and oil the tools                      Either     40m
     Due today
  Also every visit: 20 minutes weeding on arrival (20m), log the visit (1m)
  Estimated total: 1h 56m         Planned for August: 29h, logged 5.7h
  Blocked: Water the polytunnel - Blocked until Fit the tunnel polythene is done
  ! Stock              No Radish seed and Sow radish is due 2026-08-02
  Next inspection: 2026-08-03 (2 days)
```

Three to five jobs, one line each on why. If it printed twenty you would ignore
all of them.

## Login

`plot init` creates the account. Change the password straight away:

```bash
./plot passwd                       # prompts, or --password
./plot user --add someone@example.com
./plot user --rename old@example.com --to new@example.com
```

The seeded address is `zac@stayful.co.uk`. If a database was created with a
different one, `plot init` points the single existing account at the configured
address rather than making a second account; the password is unchanged.

**No password lives in this repository.** `plot init` takes one from
`--password`, from `ALLOTMENT_PASSWORD`, or by prompting, and generates a random
one and prints it if it is running unattended. A password committed to a
repository is a published password. Passwords are
stored as PBKDF2-HMAC-SHA256 with 240,000 iterations and a per-user salt, never
in plain text. Sessions are server-side, HttpOnly, and every form carries a CSRF
token; eight bad attempts locks the account for fifteen minutes.

`plot serve` binds to 127.0.0.1 on port 8765, overridable with `--host`,
`--port`, or the `ALLOTMENT_HOST` and `PORT` environment variables. A preview or
container that proxies from outside needs `--host 0.0.0.0`.

It speaks plain HTTP. That is right for a
machine on your own network. **Do not expose it to the internet without a TLS
reverse proxy in front of it** — a password over plain HTTP is a password in
public.

## Commands

| | |
|---|---|
| `plot today` | the daily view |
| `plot week` | the weekly plan, with reasons and deferrals |
| `plot jobs --days 14` | everything due, with run ids |
| `plot done 14 95` | job run 14 took 95 minutes |
| `plot arrive` / `start 14` / `stop 14` / `leave --mood fine` | timed visit |
| `plot log 90 both fine --notes "slugs got the lettuce"` | retrospective log |
| `plot spend 34.50 Wilko protection` | record spending |
| `plot budget` | setup variance, running rate, sinking fund |
| `plot stock` / `plot shop` | stock levels; shopping list with barrow trips |
| `plot harvest courgette 1.4` | log a harvest in kg |
| `plot time` | the calibration report |
| `plot report` | the year in money, time, food, failures and mood |
| `plot sun --date 2027-04-15` | sun hours by zone, placement checks |
| `plot weeds` | weed pressure, and today's 20 minutes split by zone |
| `plot rotation` | next year's bed assignment, validated |
| `plot weather` | refresh the cache and show the derived values |
| `plot permission` | log written permission — unblocks all structure jobs |
| `plot ban` / `plot ban --off` | hosepipe ban on or off |
| `plot serve` | the web view |
| `plot user --rename a@b.c --to d@e.f` | change a login address |

Global flags go before the subcommand: `plot --offline today`,
`plot --db /path/x.db today`.

## The rule engine

Every job resolves to a due date through one of seven rule types.

| Rule | Params | Example |
|---|---|---|
| `fixed_window` | `start_md`, `end_md`, `frequency` | sow tomatoes, 15 Feb – 20 Mar |
| `recurring` | `interval_days`, `from_md`, `to_md`, `after_job` | turn compost every 30 days |
| `weather_conditional` | `condition`, `from_md`, `to_md` | water beds if under 8 mm in 3 days |
| `crop_linked` | `crop_id`, `anchor`, `offset_days`, `repeat_days`, `repeat_count` | earth up, +21 days then every 14, ×3 |
| `dependency` | `depends_on[]` | fill the beds, once they are built |
| `inspection_linked` | `days_before` | tidy sweep, 3 days before inspection |
| `succession` | `interval_days`, `window_start`, `window_end`, `max_sowings` | radish every 14 days, max 12 |

Two behaviours worth knowing:

- **A recurring job keeps one open run.** Miss five compost turns and you owe one
  turn, not five.
- **Nothing is generated before the season start.** Take the plot on in August
  and you are not greeted with "plant maincrop potatoes, overdue by 109 days".

Priority is `urgency + consequence + weather_fit − blocked_penalty`. A blocked job
carries a penalty of 100, so it can never float to the top of the list.

## Hard rules, encoded

These come from the tenancy documents and are not advisory.

- **The clay block.** More than 15 mm of rain in 48 hours moves every soil and
  build job to blocked, with the millimetres shown. An *unknown* forecast never
  blocks — a false block stops you working for no reason.
- **Organic only.** `stock.add` refuses a treatment without recorded
  certification.
- **Structures need written permission.** Every shed and tunnel job is blocked
  until `plot permission` logs it.
- **Neighbour shading.** No structure over 1 m within 6 m of the north-west
  boundary. A 2 m structure throws 6.0 m north-west at 08:00 on the equinoxes,
  which is exactly when a neighbour's seedlings are most vulnerable. The current
  layout passes; `plot sun` re-checks it.
- **One metre fence strip kept clear.** Not a growing zone, and the rotation
  validator refuses to assign it.
- **Water off November to March**, and a hosepipe ban switches watering estimates
  from 5 minutes to 20.
- **Inspection every 28 days from calendar week 4**, with a tidy job three days
  before each.
- **No vehicle access.** The shopping list prices bulk items in barrow trips —
  60 kg or 0.1 m³ a load — and puts the time on the job rather than in a
  footnote. A tonne of hardcore is 17 trips.

## The map

`plot serve`, then open `/map`. Seven layers over one footprint: layout, sun and
shade, weed pressure, trouble spots, watering, rotation, neighbour shading.

The sun layer is real solar geometry for 52.75°N, not a sketch — verified against
60.7° at midsummer noon, 13.8° at midwinter, 36.8° at the equinox. Sun hours are
sampled every 30 minutes over a 19 × 19 grid of 0.6 m cells. The same arithmetic
runs in Python (`allotment/sun.py`) and in the page, and the two agree to the
decimal: bed 1 gets 9.5 hours on 15 April in both.

Zone geometry lives in the database, so the drawing and the model cannot drift
apart. `allotment/static/map.html` also opens straight off disk, falling back to
a built-in copy of the layout.

## What the numbers are for

`plot report` prints money, time, food, failures and mood. Three lines matter:

- **Calibration factor** — actual ÷ estimated. If it settles at 1.6, every hour
  figure in the smallholding plan is 60% light. Timed data is weighted above
  entered, and entered above allocated, so the number is not polluted by
  guesswork.
- **Winter attendance** — planned November–February visits actually made.
- **Mood split** — the share of visits logged as hard going or a chore.

Overheads are tracked separately (`minutes_total − Σ job minutes`). On a
five-minute walk this should settle around 12 minutes a visit. Buried inside job
times it would inflate every estimate and make the calibration factor lie.

After three completed runs a job's estimate becomes an exponential moving average
of what it actually took. The original planned figure is kept in
`jobs.planned_minutes` — the gap between the two is the point of the exercise.

## Layout

```
allotment/
  config.py      site constants, thresholds, budgets, plan hours
  db.py          schema, and the SQLite/Postgres backends
  seeddata.py    zones, crops, 90 jobs, rotation, trouble spots, opening stock
  seed.py        loads it, idempotently
  rules.py       the seven rule types, materialisation, blocking
  weather.py     Open-Meteo cache and derived values
  priority.py    scoring, the daily view, risk flags
  planner.py     the weekly plan
  stock.py       job-to-stock check, shopping list, barrow trips
  ledger.py      visits, timing, calibration
  money.py       spend, budget variance, assets, the year report
  sun.py         solar geometry, sun hours, neighbour shading
  weeds.py       weed pressure, corrected by observation
  rotation.py    four-year cycle and validation
  auth.py        PBKDF2, sessions, CSRF, lockout
  server.py      the web view
  cli.py         `plot`
api/index.py     the Vercel entry point
tests/           67 tests, run against SQLite and Postgres
```

## Deployment

Locally, SQLite. Hosted, Postgres — set `DATABASE_URL` and the same code uses it.
Nothing else changes: one schema, one set of SQL, translated where the two
dialects disagree (placeholders, `INSERT OR IGNORE`, two-argument `MAX`, and
`RETURNING` for a new row's id). Both backends run the full test suite.

```bash
# locally: SQLite, no dependencies
./plot init && ./plot serve

# against Postgres, from your own machine
export DATABASE_URL="postgresql://user:pass@host:5432/postgres"
./plot today
```

### On Vercel

`api/index.py` is the entry point — Vercel's Python runtime wants a
`BaseHTTPRequestHandler` subclass called `handler`, which is what the server
already is, and `vercel.json` rewrites every route to it. Two environment
variables:

| | |
|---|---|
| `DATABASE_URL` | Postgres connection string. Required. |
| `ALLOTMENT_PASSWORD` | Used once, on first boot, to create the login. Delete it afterwards. |

The first request against an empty database creates the schema and seeds the
plot, so there is no migration step to run. Seeding is idempotent, so two cold
starts racing each other is harmless. Without `DATABASE_URL` the site serves a
page telling you what is missing, rather than a 500 or Vercel's own 404.

**Why not SQLite on Vercel:** the filesystem is read-only apart from `/tmp`, and
`/tmp` is wiped between cold starts. Marking a job done would appear to work and
then vanish, which is worse than not deploying it at all.

## Routes

| | |
|---|---|
| `/` `/week` `/map` `/stock` `/shop` `/money` `/time` `/report` | the app, behind the login |
| `/login` `/logout` | session in and out |
| `/favicon.ico` `/robots.txt` `/healthz` | served without a login |
| `/static/<file>` | files from `allotment/static`, and nothing above it |

Anything else returns a 404 page with links back. `/favicon.ico` matters more
than it looks: a browser asks for it on every page load, so without it the
console fills with errors on a site that is working perfectly.

## Tests

```bash
python3 -m unittest discover -s tests -v                    # SQLite
ALLOTMENT_TEST_PG=postgresql://... python3 -m unittest discover -s tests   # Postgres
```

The same 67 tests run against both backends. Each Postgres run builds and drops
its own schema, so it will not touch anything else in the database.

## Build order

Steps 1–6 of the plan are built: jobs engine and daily view, visit logging,
weather rules, spending, stock with the job-to-stock check, and the crop-linked,
dependency and succession rules. The mapping module, the weekly planner, the
asset register and the reports are built too.

**Step 7, receipts, is deliberately not built.** The tables (`receipts`,
`receipt_lines`) are in the schema and the web form does manual entry in about
thirty seconds. OCR on a folded garden-centre receipt is unreliable, you will
have perhaps fifteen receipts in year one, and the honest assessment in the spec
was that it is the highest-effort, lowest-payoff part. Build it when manual entry
has actually become annoying.

Use the daily view and visit logging for a month before extending anything. You
will redesign half of it once you see what you actually record.
