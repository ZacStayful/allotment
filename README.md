# Allotment

Plot 129.8 m², Albert Village Allotment Association. A jobs engine that tells you
what needs doing today, and the ledger that tells you what it really cost.

Python 3.9+. Locally it is standard library only — no pip install, no framework,
no build step, everything in one SQLite file. The hosted copy runs the same code
against Postgres, because a serverless filesystem cannot keep a database file.

```bash
./plot init          # create plot.db, seed the plot, create the login
./plot setup         # part one: build the plot, in order
./plot today         # part two: the daily view
./plot serve         # the web view, on http://127.0.0.1:8765
```

## Two parts, because the plot has two lives

A bare plot and a running plot want different things said to them, and the same
list cannot say both. So the work is in two parts, and `plot today` knows which
one you are in.

**Part one — setting up.** Sixteen numbered steps from a strimmer to a bed you
can sow. `plot setup` prints the sequence with what each step is for, what it is
waiting on, and what to buy first. The numbers are the guide; the dependencies
in the seed data are the enforcement, and a test holds the two together so the
guide can never send you to a step that cannot be done. Step 8 — the beds filled
— is the point food can go in the ground; steps 9 to 16 are the shed and the
tunnel, which are worth having and are not worth waiting for.

**Part two — running it.** Two lists. **Growing** is the food: sowing it,
watering it, netting it, picking it. **Maintenance** is the plot the food lives
on: weeds, paths, compost, shed, tunnel, the Association. Every job carries a
`stream` saying which, and Today prints them under those two headings.

Nothing from part two appears before the part of the plot it needs exists. Every
job that assumes a bed, a tunnel or a cleared plot says so, and stays out of the
way until it is true.

```
SUNDAY 2 AUGUST            Rain 3d: 0mm   Max 21°C   Min 10°C   Soil: workable

SETUP  step 0 of 16 done - 8 more (24h 00m) before anything can be sown
  ->  1. Apply in writing for shed and polytunnel Site       30m
        Ready to do
  ->  2. Clear the plot - strim and remove rubbis Both    4h 00m
        Ready to do
  `plot setup` for the whole sequence

MAINTENANCE
  1. Clean and oil the tools                      Either     40m
     Due today

  Also every visit: log the visit (1m)
  Estimated total: 5h 11m         Planned for August: 29h, logged 0.0h
  Waiting on the build: 9 growing and maintenance jobs. They appear as the steps are ticked off.
  ! Stock              7 things to buy before jobs come due - Hardcore, Slabs, Scaffold boards and 4 more
```

Once the build is finished the setup block goes away and the two lists are the
whole page:

```
SATURDAY 12 JUNE           Rain 3d: 0mm   Max 21°C   Min 10°C   Soil: workable

GROWING
  1. Water the beds and pollinator bed            Either     25m
     Only 0 mm rain in the last 3 days
  2. Pick beans and courgettes                    Either     25m
     Miss this and the plants stop cropping

MAINTENANCE
  1. Clean and oil the tools                      Either     40m
     Due today
  Also every visit: 20 minutes weeding on arrival (20m), log the visit (1m)
```

Three to five jobs, one line each on why. If it printed twenty you would ignore
all of them.

## The log book

`plot logbook`, or **Log book** in the web view. Every other page here
aggregates — Money shows totals by budget line, Report shows the year — which is
the right shape for deciding things and the wrong shape for remembering them.
Enter a shop, a date and a note about which bed it was for, and a page that
answers `growing_media  £412.00  3 items` has not lost the detail so much as
never read it back, which amounts to the same thing.

The log book is one reverse-chronological list of everything entered — spending,
stock movements, visits, finished jobs, harvests, photographs — with nothing
summarised away, and the note you typed in quotation marks underneath it.

```
2027-03-14
  spend    £34.50 Wilko                                   running
           2 m butterfly netting · protection
           "for bed 3, ran short by a metre"
  visit    Visit - 95 minutes                             fine
           Both
           "slugs got the lettuce"
```

`plot logbook --kind spend --since 2027-01-01`, and the same filters as tabs on
the page. Spending records what the thing actually was as well as which budget
line it came out of; a receipt photographed on the Photos page hangs off the
spend it paid for.

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
public. The session cookie is marked `Secure` when the request arrived over
HTTPS and not when it did not, read from `X-Forwarded-Proto`: on the hosted copy
that closes the plain-HTTP leak, and locally it avoids setting a cookie the
browser accepts and then never sends back.

### Making the hosted copy reachable

The app gates itself and nothing else. If the production URL asks for a *Vercel*
login rather than the plot's own, that is **Deployment Protection**, not this
code: Project → Settings → Deployment Protection → Vercel Authentication →
Disabled, or *Only Preview Deployments*. It applies immediately, with no
redeploy. Preview URLs stay protected on the paid plans however that is set, so
share the production URL.

Once it is off, the login is the only thing between the internet and the plot:
PBKDF2-HMAC-SHA256 at 240,000 iterations, server-side sessions, a CSRF token on
every form, and a fifteen-minute lockout after eight bad attempts. `robots.txt`
disallows everything, so the URL is reachable without being indexed — but it is
public, so use a password you would be happy to see brute-forced at leisure.

## Commands

| | |
|---|---|
| `plot setup` | part one: the build sequence, in order |
| `plot today` | part two: the daily view |
| `plot logbook` | everything entered, in full |
| `plot week` | the weekly plan, with reasons and deferrals |
| `plot jobs --days 14` | everything due, with run ids |
| `plot done 14 95` | job run 14 took 95 minutes |
| `plot arrive` / `start 14` / `stop 14` / `leave --mood fine` | timed visit |
| `plot log 90 both fine --notes "slugs got the lettuce"` | retrospective log |
| `plot spend 34.50 Wilko protection --item "2 m netting"` | record spending |
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

Three behaviours worth knowing:

- **A recurring job keeps one open run.** Miss five compost turns and you owe one
  turn, not five.
- **Nothing is generated before the season start.** Take the plot on in August
  and you are not greeted with "plant maincrop potatoes, overdue by 109 days".
- **A one-off is due for as long as its window is open**, not only on the day it
  opens. Both openers of the build sequence used to start on 1 August, so a plot
  taken on on the 2nd generated neither of them — step one never appeared and
  every step behind it read as blocked for ever.

A job also declares what it needs to exist before it makes sense. Watering the
beds waits for the beds; the twenty minutes of weeding waits for the plot to be
cleared, because until then the clearing *is* the weeding. That is the same
dependency machinery as the build sequence, pointed at the running year.

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
  setup.py       part one: the build sequence, its state and its progress
  weather.py     Open-Meteo cache and derived values
  priority.py    scoring, the daily view, the growing/maintenance split
  logbook.py     part two: everything entered, read back in full
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
tests/           105 tests, run against SQLite and Postgres
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

### Which branch is deployed

Vercel builds the **production** URL from `main` and gives every other branch
its own **preview** URL. Code on a branch is not on `main` until it is merged,
so redeploying production while the work sits on a branch rebuilds an empty
repository and serves a 404. Check the branch name on the deployment before
concluding the app is broken.

A deployment also captures the environment variables that existed when it was
built. Adding a variable does not reach a deployment that already exists — that
one has to be rebuilt.

### On Vercel

`api/index.py` is the entry point. **The runtime scans that file for a
top-level `handler`, `app`, or `application`, and it looks for a definition** —
`handler = server.Handler` is an assignment, invisible to that check, and the
build then silently produces no function at all, so every path falls through to
Vercel's own 404 while the deployment still reports READY. Hence the seemingly
redundant subclass:

```python
class handler(server.Handler):
    """The whole app, as the runtime expects to find it."""
```

`vercel.json` then rewrites every route to it. Two environment variables:

| | |
|---|---|
| `DATABASE_URL` | Postgres connection string. Required. |
| `ALLOTMENT_PASSWORD` | Used once, on first boot, to create the login. Delete it afterwards. |

The first request against an empty database creates the schema and seeds the
plot, so there is no migration step to run. Seeding is idempotent, so two cold
starts racing each other is harmless. Without `DATABASE_URL` the site serves a
page telling you what is missing, rather than a 500 or Vercel's own 404.

**Schema changes are self-applying.** `CREATE TABLE IF NOT EXISTS` does nothing
to a table that already exists, so a column added to the schema never reaches a
plot that is already running — and the hosted copy has no shell to run a
migration in. `db.ADDED_COLUMNS` lists them and `db.migrate` adds whichever are
missing on the next start. Creating a column is only half of it: `seed.backfill`
then re-seeds the job metadata, because a column that exists and is empty
everywhere fails silently — the whole setup sequence and both day-to-day lists
would come back blank after a deploy with nothing to say why.

**Why not SQLite on Vercel:** the filesystem is read-only apart from `/tmp`, and
`/tmp` is wiped between cold starts. Marking a job done would appear to work and
then vanish, which is worse than not deploying it at all.

### On Supabase

Four things stood between a correct connection string and a working site, and
each one failed in a way that pointed at a different one. The setup page now
names whichever it is, in words, rather than showing an exception:

1. **The pooler, not the direct host.** `db.<ref>.supabase.co` publishes an AAAA
   record and no A record, and a Vercel function has no IPv6 route. Connect >
   Session pooler gives a `*.pooler.supabase.com` host, which is on IPv4.
2. **The right pooler.** A project sits on one of the region's poolers — `aws-0`,
   `aws-1` — and the others are real hosts that answer `tenant or user not
   found`, which reads exactly like a bad user name. The app tries the siblings
   and logs the one that worked; set `DATABASE_URL` to it to skip the retry.
   The user name needs the project reference on it: `user.projectref`.
3. **No `CREATE` on the database.** Postgres checks that privilege before it
   checks whether the schema exists, so `CREATE SCHEMA IF NOT EXISTS` is refused
   for a role that needs nothing of the sort. The app looks first and creates
   only what is missing, so it can run with no database-level rights.
4. **The app owns its tables.** `CREATE INDEX` requires ownership, so tables
   created by an admin role leave the app failing with `must be owner of table`.
   Create them as the app's role, or hand them over afterwards.

The role wants `USAGE` and `CREATE` on its own schema, and nothing outside it.

## Routes

| | |
|---|---|
| `/` `/setup` `/week` `/map` `/photos` `/stock` `/shop` `/money` `/logbook` `/time` `/report` | the app, behind the login |
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

The same 105 tests run against both backends. Each Postgres run builds and drops
its own schema, so it will not touch anything else in the database.

## Build order

Steps 1–6 of the plan are built: jobs engine and daily view, visit logging,
weather rules, spending, stock with the job-to-stock check, and the crop-linked,
dependency and succession rules. The mapping module, the weekly planner, the
asset register and the reports are built too.

The build sequence, the growing/maintenance split and the log book came out of
using it: the daily view was asking for twenty minutes of weeding on a plot that
had not been cleared, there was no order to start in, and everything typed into
a form came back as a total.

**Step 7, receipts, is deliberately not built.** The tables (`receipts`,
`receipt_lines`) are in the schema and the web form does manual entry in about
thirty seconds. OCR on a folded garden-centre receipt is unreliable, you will
have perhaps fifteen receipts in year one, and the honest assessment in the spec
was that it is the highest-effort, lowest-payoff part. Build it when manual entry
has actually become annoying.

Use the daily view and visit logging for a month before extending anything. You
will redesign half of it once you see what you actually record.
