"""Schema and connection.

SQLite by default - one file, no server, per §1. When DATABASE_URL is set the
same SQL runs against Postgres instead, which is what the hosted copy uses,
because a serverless filesystem cannot keep a database file. The SQL is written
once; a small translation layer handles the handful of places the two dialects
disagree.
"""

import json
import os
import re
import socket
import sqlite3
import sys
import urllib.parse

from . import config

try:                                    # only needed for the Postgres backend
    import psycopg2
    import psycopg2.extras
except ImportError:                     # pragma: no cover - SQLite-only install
    psycopg2 = None

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
PG_SCHEMA = os.environ.get("ALLOTMENT_PG_SCHEMA", "allotment")

# Tables with an id column, so an INSERT can report what it created. Not
# sessions, which is keyed by its token.
ID_TABLES = {
    "users", "zones", "crops", "jobs", "job_runs", "visits", "harvests",
    "plantings", "spend", "stock", "stock_moves", "receipts", "receipt_lines",
    "assets", "asset_events", "weed_observations", "trouble_pins", "photos",
    "site_access", "documents",
}

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT,
  role TEXT NOT NULL DEFAULT 'Both', pw_hash TEXT NOT NULL, pw_salt TEXT NOT NULL,
  iterations INTEGER NOT NULL, created TEXT NOT NULL, last_login TEXT);

CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  csrf TEXT NOT NULL, created TEXT NOT NULL, expires TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS login_attempts (
  email TEXT PRIMARY KEY, failures INTEGER NOT NULL DEFAULT 0, last_failure TEXT);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS zones (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT, area_m2 REAL, notes TEXT,
  x REAL, y REAL, w REAL, d REAL, height_m REAL DEFAULT 0,
  growable INTEGER NOT NULL DEFAULT 1, colour TEXT);

CREATE TABLE IF NOT EXISTS crops (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, zone_id TEXT REFERENCES zones(id),
  family TEXT, sow_from TEXT, sow_to TEXT, sow_indoor_from TEXT, sow_indoor_to TEXT,
  plant_from TEXT, plant_to TEXT, harvest_from TEXT, harvest_to TEXT,
  spacing_cm INTEGER, needs_netting INTEGER DEFAULT 0, needs_support INTEGER DEFAULT 0,
  fruiting INTEGER DEFAULT 0, notes TEXT);

CREATE TABLE IF NOT EXISTS visits (
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, arrive_time TEXT, leave_time TEXT,
  minutes_total INTEGER, who TEXT, weather_snapshot TEXT, mood TEXT, notes TEXT);

CREATE TABLE IF NOT EXISTS overheads (
  visit_id INTEGER PRIMARY KEY REFERENCES visits(id) ON DELETE CASCADE,
  walk_minutes INTEGER DEFAULT 0, setup_minutes INTEGER DEFAULT 0, tidy_minutes INTEGER DEFAULT 0);

CREATE TABLE IF NOT EXISTS stock (
  id INTEGER PRIMARY KEY, item TEXT NOT NULL, category TEXT NOT NULL, unit TEXT,
  qty REAL NOT NULL DEFAULT 0, reorder_at REAL NOT NULL DEFAULT 0,
  location TEXT DEFAULT 'shed', unit_cost REAL, expires TEXT, supplier TEXT,
  organic_certified INTEGER DEFAULT 0, bulk_kg REAL, bulk_m3 REAL, notes TEXT);

CREATE TABLE IF NOT EXISTS plantings (
  id INTEGER PRIMARY KEY, crop_id TEXT REFERENCES crops(id), variety TEXT,
  zone_id TEXT REFERENCES zones(id), position TEXT, qty INTEGER,
  sown_date TEXT, planted_date TEXT, method TEXT,
  expected_first_harvest TEXT, expected_last_harvest TEXT,
  status TEXT NOT NULL DEFAULT 'sown', failure_reason TEXT,
  seed_stock_id INTEGER REFERENCES stock(id), notes TEXT);

CREATE TABLE IF NOT EXISTS harvests (
  id INTEGER PRIMARY KEY, visit_id INTEGER REFERENCES visits(id) ON DELETE CASCADE,
  planting_id INTEGER REFERENCES plantings(id), date TEXT NOT NULL, crop TEXT NOT NULL,
  kg REAL NOT NULL, retail_per_kg REAL, notes TEXT);

CREATE TABLE IF NOT EXISTS receipts (
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, vendor TEXT, total REAL,
  currency TEXT DEFAULT 'GBP', image_path TEXT, status TEXT NOT NULL DEFAULT 'pending',
  raw_json TEXT, confidence REAL, duplicate_of INTEGER REFERENCES receipts(id), notes TEXT);

CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY, item TEXT NOT NULL, category TEXT, purchase_date TEXT,
  purchase_price REAL NOT NULL DEFAULT 0, supplier TEXT, receipt_id INTEGER REFERENCES receipts(id),
  expected_life_years REAL, depreciation TEXT DEFAULT 'straight_line', residual_value REAL DEFAULT 0,
  condition TEXT DEFAULT 'new', location TEXT, serial TEXT, insured INTEGER DEFAULT 0,
  disposal_date TEXT, notes TEXT);

CREATE TABLE IF NOT EXISTS receipt_lines (
  id INTEGER PRIMARY KEY, receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
  description TEXT, qty REAL, unit_price REAL, line_total REAL,
  mapped_category TEXT, mapped_stock_id INTEGER REFERENCES stock(id),
  mapped_asset_id INTEGER REFERENCES assets(id), confirmed INTEGER DEFAULT 0);

CREATE TABLE IF NOT EXISTS asset_events (
  id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  date TEXT NOT NULL, type TEXT NOT NULL, cost REAL DEFAULT 0, notes TEXT);

CREATE TABLE IF NOT EXISTS spend (
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, vendor TEXT, category TEXT,
  amount REAL NOT NULL, budget_line TEXT NOT NULL, receipt_id INTEGER REFERENCES receipts(id),
  setup INTEGER NOT NULL DEFAULT 0, notes TEXT);

CREATE TABLE IF NOT EXISTS stock_moves (
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, stock_id INTEGER NOT NULL REFERENCES stock(id) ON DELETE CASCADE,
  delta REAL NOT NULL, reason TEXT NOT NULL, ref TEXT, visit_id INTEGER REFERENCES visits(id));

CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY, job_key TEXT UNIQUE, title TEXT NOT NULL, category TEXT NOT NULL,
  owner TEXT NOT NULL DEFAULT 'Either', phase TEXT, est_minutes INTEGER NOT NULL DEFAULT 30,
  planned_minutes INTEGER, rule_type TEXT NOT NULL, rule_params TEXT NOT NULL DEFAULT '{}',
  active_from TEXT, active_to TEXT, depends_on TEXT, one_off INTEGER DEFAULT 0,
  zone_id TEXT REFERENCES zones(id), crop_id TEXT REFERENCES crops(id),
  consequence INTEGER NOT NULL DEFAULT 2, stock_needs TEXT, every_visit INTEGER DEFAULT 0,
  needs_permission INTEGER DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, notes TEXT);

CREATE TABLE IF NOT EXISTS job_runs (
  id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  visit_id INTEGER REFERENCES visits(id), due_date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'due', done_date TEXT,
  est_minutes INTEGER, actual_minutes INTEGER, timing_method TEXT,
  done_by TEXT, zone_id TEXT, started_at TEXT, seq INTEGER DEFAULT 0, notes TEXT,
  UNIQUE(job_id, due_date, seq));

CREATE TABLE IF NOT EXISTS weather_cache (
  date TEXT PRIMARY KEY, rain_mm REAL, temp_min REAL, temp_max REAL,
  wind_kph REAL, gust_kph REAL, sunrise TEXT, sunset TEXT,
  source TEXT, fetched TEXT);

CREATE TABLE IF NOT EXISTS weed_observations (
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, zone_id TEXT, x REAL, y REAL,
  observed REAL NOT NULL, minutes INTEGER, notes TEXT);

CREATE TABLE IF NOT EXISTS trouble_pins (
  id INTEGER PRIMARY KEY, x REAL, y REAL, title TEXT NOT NULL, kind TEXT,
  severity TEXT, description TEXT, remedy TEXT, source TEXT DEFAULT 'derived', date TEXT);

CREATE TABLE IF NOT EXISTS rotation (
  year INTEGER NOT NULL, zone_id TEXT NOT NULL, family_group TEXT NOT NULL,
  PRIMARY KEY (year, zone_id));

-- Photos live in the database rather than on disk, because the hosted copy has
-- no disk that survives a request. `subject` is free text - "receipt:12",
-- "job:build-tunnel", "zone:bed-1", "problem" - deliberately not a foreign key,
-- so a photo outlives whatever it was taken of.
CREATE TABLE IF NOT EXISTS photos (
  id INTEGER PRIMARY KEY, taken TEXT NOT NULL, subject TEXT NOT NULL,
  caption TEXT, mime TEXT NOT NULL, bytes BLOB NOT NULL, size INTEGER NOT NULL,
  width INTEGER, height INTEGER);

-- How you get in, and what you sign in with. The values live here and nowhere
-- else: this repository is public, and the Constitution forbids passing padlock
-- codes on without the Committee's written permission, so a code committed to
-- source is both a published code and a breach of the tenancy. `plot access`
-- and the Access page put them in; the seed carries the labels only.
CREATE TABLE IF NOT EXISTS site_access (
  id INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, label TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'code', identity TEXT, secret TEXT, url TEXT,
  notes TEXT, pos INTEGER NOT NULL DEFAULT 0, updated TEXT);

-- The paperwork of the tenancy. `body` is the readable text; `bytes` is the
-- original file where there is one, so a signed copy can be kept exactly as it
-- was signed. Like photos, in the database rather than on disk, because the
-- hosted copy has no disk that survives a request.
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY, doc_key TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'tenancy', dated TEXT, summary TEXT, body TEXT,
  filename TEXT, mime TEXT, bytes BLOB, size INTEGER, added TEXT NOT NULL);

CREATE INDEX IF NOT EXISTS idx_photos_subject ON photos(subject, taken);
CREATE INDEX IF NOT EXISTS idx_runs_due ON job_runs(due_date, status);
CREATE INDEX IF NOT EXISTS idx_moves_stock ON stock_moves(stock_id);
CREATE INDEX IF NOT EXISTS idx_spend_date ON spend(date);
CREATE INDEX IF NOT EXISTS idx_harvest_date ON harvests(date);
"""


# ------------------------------------------------------- dialect translation

INSERT_IGNORE = re.compile(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)", re.I)
INSERT_INTO = re.compile(r"^\s*INSERT\s+INTO\s+(\w+)", re.I)


def to_postgres(sql):
    """Rewrite the SQLite SQL this codebase is written in. Returns (sql, table).

    Four differences, and no more: placeholders, INSERT OR IGNORE, the
    two-argument scalar MAX, and needing RETURNING to learn a new row's id.
    """
    table = None
    m = INSERT_IGNORE.match(sql)
    if m:
        table = m.group(1)
        sql = re.sub(r"^(\s*)INSERT\s+OR\s+IGNORE\s+INTO", r"\1INSERT INTO", sql, count=1,
                     flags=re.I)
        sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    else:
        m = INSERT_INTO.match(sql)
        if m:
            table = m.group(1)
    sql = re.sub(r"\bMAX\(\s*0\s*,", "GREATEST(0,", sql, flags=re.I)
    sql = sql.replace("?", "%s")
    if table in ID_TABLES and " RETURNING " not in sql.upper():
        sql = sql.rstrip().rstrip(";") + " RETURNING id"
        return sql, table
    return sql, None


DDL_PRAGMA = re.compile(r"^\s*PRAGMA[^;]*;", re.I | re.M)
LINE_COMMENT = re.compile(r"--[^\n]*")


def split_statements(script):
    """One statement per semicolon - but not the ones inside a comment.

    SQLite is handed the whole script and parses it itself. Postgres is handed
    one statement at a time, so this does the splitting, and a naive split on
    ";" cuts a `-- comment` in half: the first piece is a statement made
    entirely of comment, which the driver rejects as an empty query, and the
    second leaves the tail of an English sentence sitting in front of the next
    CREATE TABLE. The error then quotes a word from a sentence about padlock
    codes and points nowhere near the problem. Stripping the comments first
    makes the whole class of it impossible.
    """
    return [s.strip() for s in LINE_COMMENT.sub("", script).split(";") if s.strip()]


def schema_for_postgres(schema=None):
    """The tables only. Creating the schema they live in is a separate step,
    because it needs a privilege the rest of this does not - see ensure_schema."""
    sql = DDL_PRAGMA.sub("", SCHEMA)
    sql = sql.replace("id INTEGER PRIMARY KEY,", "id SERIAL PRIMARY KEY,")
    sql = re.sub(r"\bREAL\b", "double precision", sql)
    return re.sub(r"\bBLOB\b", "bytea", sql)


def ensure_schema(conn):
    """Create the schema, but only if it is actually missing.

    CREATE SCHEMA IF NOT EXISTS is not free to attempt: Postgres checks CREATE on
    the *database* before it checks whether the schema is there, so a role that
    owns its schema and needs nothing else still fails with "permission denied
    for database postgres" every time it starts. Asking first means the app can
    run with no database-level rights at all, which is what it should have."""
    seen = conn.execute("SELECT 1 ok FROM information_schema.schemata "
                        "WHERE schema_name=?", (conn.schema,)).fetchone()
    if not seen:
        conn.execute("CREATE SCHEMA IF NOT EXISTS %s" % conn.schema)
        conn.commit()


class PgCursor:
    """The bits of a sqlite3 cursor the rest of the code actually uses."""

    def __init__(self, cur, returning):
        self._cur = cur
        self.rowcount = cur.rowcount
        self.lastrowid = None
        self._rows = None
        if returning:
            row = cur.fetchone()
            self.lastrowid = row["id"] if row else None
            self.rowcount = 1 if row else 0

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self._cur)


POOLER_HOST = re.compile(r"^aws-(\d+)-([a-z0-9-]+)\.pooler\.supabase\.com$", re.I)
POOLER_CLUSTERS = 4
TENANT_MISSING = "not found"

# The URL that actually worked, once one has. A wrong pooler is a real host that
# completes a TCP and TLS handshake before rejecting the tenant, so retrying it
# on every request costs a full transatlantic round trip for a known answer.
_WORKING_URL = None


def sibling_poolers(url):
    """The same connection string on the region's other pooler clusters.

    A Supabase project sits on one of several poolers in its region, numbered
    aws-0, aws-1 and so on, and only the dashboard says which. Point at the wrong
    one and it answers - it is a real host - with "tenant or user not found",
    which reads exactly like a bad user name and sends you to change the one
    thing that was already right.

    Rather than have someone guess, try the siblings. There are a handful, they
    are in the same region, and a wrong one fails immediately.
    """
    bits = urllib.parse.urlsplit(url)
    m = POOLER_HOST.match(bits.hostname or "")
    if not m:
        return []
    here, region = int(m.group(1)), m.group(2)
    out = []
    for n in range(POOLER_CLUSTERS):
        if n == here:
            continue
        host = "aws-%d-%s.pooler.supabase.com" % (n, region)
        netloc = bits.netloc.replace(bits.hostname, host, 1)
        out.append(urllib.parse.urlunsplit(bits._replace(netloc=netloc)))
    return out


class PgConnection:
    """Wraps psycopg2 so it answers to the sqlite3 connection API this code uses."""

    def __init__(self, url, schema=None):
        if psycopg2 is None:
            raise RuntimeError(
                "DATABASE_URL is set but psycopg2 is not installed. "
                "pip install psycopg2-binary, or unset DATABASE_URL to use SQLite.")
        self.schema = schema or PG_SCHEMA
        self._conn = self._open(url)
        self._conn.autocommit = False
        with self._conn.cursor() as c:                # belt and braces: some poolers
            c.execute("SET search_path TO %s, public" % self.schema)   # drop the option
        self._conn.commit()

    def _open(self, url):
        global _WORKING_URL
        try:
            return self._dial(_WORKING_URL or url)
        except psycopg2.OperationalError as first:
            if TENANT_MISSING not in str(first).lower():
                raise
            for other in sibling_poolers(url):
                try:
                    conn = self._dial(other)
                except psycopg2.OperationalError:
                    continue
                host = urllib.parse.urlsplit(other).hostname
                _WORKING_URL = other       # once per process, not once per page
                sys.stderr.write(
                    "DATABASE_URL names a pooler this project is not on. Connected "
                    "via %s instead - set DATABASE_URL to that host to stop paying "
                    "for the retry on every cold start.\n" % host)
                return conn
            raise

    def _dial(self, url):
        return psycopg2.connect(
            url, options="-c search_path=%s,public" % self.schema,
            connect_timeout=int(os.environ.get("ALLOTMENT_PG_TIMEOUT", 10)))

    def execute(self, sql, params=()):
        sql, returning = to_postgres(sql)
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(sql, tuple(params))
        except psycopg2.Error:
            self._conn.rollback()          # never leave the connection poisoned
            raise
        return PgCursor(cur, returning)

    def executescript(self, script):
        for statement in split_statements(script):
            self.execute(statement)
        self.commit()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def redact(text, url=None):
    """The password, wherever it appears, replaced. Postgres error messages do not
    normally quote it, but this is not a thing to leave to normally."""
    url = url or DATABASE_URL or ""
    try:
        pw = urllib.parse.urlsplit(url).password
    except ValueError:
        pw = None
    text = str(text)
    for form in filter(None, (pw, urllib.parse.quote(pw or "", safe=""))):
        text = text.replace(form, "***")
    return text


def diagnose(url=None, exc=None):
    """Why a connection to `url` failed, in words, or None if nothing is obviously
    wrong with it.

    Written for one failure in particular, because it is the one that costs an
    afternoon. Supabase's direct host, db.<ref>.supabase.co, publishes an AAAA
    record and no A record. Vercel's functions have no IPv6 route, so the
    connection cannot be made at all and psycopg2 reports a timeout - which reads
    like a firewall, a wrong password, or a sleeping database, and is none of
    those. The remedy is the pooler host, which is on IPv4.

    Never returns any part of the password: the host and port only.
    """
    url = url or DATABASE_URL
    if not url:
        return None
    try:
        bits = urllib.parse.urlsplit(url)
        host, port = bits.hostname, bits.port or 5432
    except ValueError:
        return "DATABASE_URL is not a URL that can be parsed."
    if not host:
        return "DATABASE_URL has no host in it."
    try:
        families = {i[0] for i in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except socket.gaierror:
        return ("The host %s does not resolve. Check it for a typo, and that the "
                "database has not been paused." % host)
    if socket.AF_INET not in families:
        pooled = "the pooler host" if ".pooler." not in host else "an IPv4 host"
        return ("The host %s has an IPv6 address and no IPv4 one, and this server "
                "can only reach IPv4. Use %s instead: in Supabase, Connect > "
                "Session pooler gives a connection string on a "
                "*.pooler.supabase.com host, which answers on IPv4." % (host, pooled))
    said = redact(exc, url).strip().splitlines()
    said = (" It said: %s" % said[0][:200]) if said and said[0] else ""
    hint = ""
    if ".pooler.supabase.com" in host:
        user = urllib.parse.urlsplit(url).username or ""
        if "." not in user:
            hint = (" Supabase's pooler wants the project reference on the end of "
                    "the user name, as user.projectref - a bare user name is "
                    "rejected as an unknown tenant.")
        elif TENANT_MISSING in redact(exc, url).lower():
            hint = (" The user name looks right, so it is the host: a project is on "
                    "one of the region's poolers and the others answer \"not found\" "
                    "for it. Supabase's Connect panel names the one to use. Every "
                    "sibling of %s was tried before giving up." % host)
    return ("Reached the name %s on port %d, but the database did not accept the "
            "connection.%s That is usually the user name or the password.%s"
            % (host, port, said, hint))


def connect(path=None, url=None):
    """Postgres when a URL is configured, SQLite otherwise.

    An explicit path always means that file - `plot --db x.db` should never
    silently talk to the hosted database."""
    url = url or (DATABASE_URL if path is None else None)
    if url:
        return PgConnection(url)
    path = path or config.DB_PATH
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(path, detect_types=0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def is_postgres(conn):
    return isinstance(conn, PgConnection)


def init(conn):
    if is_postgres(conn):
        ensure_schema(conn)
        conn.executescript(schema_for_postgres(conn.schema))
    else:
        conn.executescript(SCHEMA)
    conn.commit()


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except (ValueError, TypeError):
        return row["value"]


def set_setting(conn, key, value):
    conn.execute("INSERT INTO settings(key,value) VALUES(?,?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, json.dumps(value)))
    conn.commit()


DEFAULT_SETTINGS = {
    "hosepipe_ban": False,
    "structures_permission": False,     # §11 written permission for shed/tunnel
    "tunnel_placement_approved": False,
    "season_start": "2026-08-01",       # year 1 of the plot
    "person_a": "Grower",
    "person_b": "Site",
    "plot_ref": "I",                    # the letter on the tenancy agreement
    "tenancy_start": "2026-08-01",      # the date the plot became ours
}
