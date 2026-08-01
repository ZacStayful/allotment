"""SQLite schema and connection. One file, no server, per §1."""

import json
import os
import sqlite3

from . import config

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

CREATE TABLE IF NOT EXISTS visits (
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, arrive_time TEXT, leave_time TEXT,
  minutes_total INTEGER, who TEXT, weather_snapshot TEXT, mood TEXT, notes TEXT);

CREATE TABLE IF NOT EXISTS overheads (
  visit_id INTEGER PRIMARY KEY REFERENCES visits(id) ON DELETE CASCADE,
  walk_minutes INTEGER DEFAULT 0, setup_minutes INTEGER DEFAULT 0, tidy_minutes INTEGER DEFAULT 0);

CREATE TABLE IF NOT EXISTS harvests (
  id INTEGER PRIMARY KEY, visit_id INTEGER REFERENCES visits(id) ON DELETE CASCADE,
  planting_id INTEGER REFERENCES plantings(id), date TEXT NOT NULL, crop TEXT NOT NULL,
  kg REAL NOT NULL, retail_per_kg REAL, notes TEXT);

CREATE TABLE IF NOT EXISTS plantings (
  id INTEGER PRIMARY KEY, crop_id TEXT REFERENCES crops(id), variety TEXT,
  zone_id TEXT REFERENCES zones(id), position TEXT, qty INTEGER,
  sown_date TEXT, planted_date TEXT, method TEXT,
  expected_first_harvest TEXT, expected_last_harvest TEXT,
  status TEXT NOT NULL DEFAULT 'sown', failure_reason TEXT,
  seed_stock_id INTEGER REFERENCES stock(id), notes TEXT);

CREATE TABLE IF NOT EXISTS spend (
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, vendor TEXT, category TEXT,
  amount REAL NOT NULL, budget_line TEXT NOT NULL, receipt_id INTEGER REFERENCES receipts(id),
  setup INTEGER NOT NULL DEFAULT 0, notes TEXT);

CREATE TABLE IF NOT EXISTS stock (
  id INTEGER PRIMARY KEY, item TEXT NOT NULL, category TEXT NOT NULL, unit TEXT,
  qty REAL NOT NULL DEFAULT 0, reorder_at REAL NOT NULL DEFAULT 0,
  location TEXT DEFAULT 'shed', unit_cost REAL, expires TEXT, supplier TEXT,
  organic_certified INTEGER DEFAULT 0, bulk_kg REAL, bulk_m3 REAL, notes TEXT);

CREATE TABLE IF NOT EXISTS stock_moves (
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, stock_id INTEGER NOT NULL REFERENCES stock(id) ON DELETE CASCADE,
  delta REAL NOT NULL, reason TEXT NOT NULL, ref TEXT, visit_id INTEGER REFERENCES visits(id));

CREATE TABLE IF NOT EXISTS receipts (
  id INTEGER PRIMARY KEY, date TEXT NOT NULL, vendor TEXT, total REAL,
  currency TEXT DEFAULT 'GBP', image_path TEXT, status TEXT NOT NULL DEFAULT 'pending',
  raw_json TEXT, confidence REAL, duplicate_of INTEGER REFERENCES receipts(id), notes TEXT);

CREATE TABLE IF NOT EXISTS receipt_lines (
  id INTEGER PRIMARY KEY, receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
  description TEXT, qty REAL, unit_price REAL, line_total REAL,
  mapped_category TEXT, mapped_stock_id INTEGER REFERENCES stock(id),
  mapped_asset_id INTEGER REFERENCES assets(id), confirmed INTEGER DEFAULT 0);

CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY, item TEXT NOT NULL, category TEXT, purchase_date TEXT,
  purchase_price REAL NOT NULL DEFAULT 0, supplier TEXT, receipt_id INTEGER REFERENCES receipts(id),
  expected_life_years REAL, depreciation TEXT DEFAULT 'straight_line', residual_value REAL DEFAULT 0,
  condition TEXT DEFAULT 'new', location TEXT, serial TEXT, insured INTEGER DEFAULT 0,
  disposal_date TEXT, notes TEXT);

CREATE TABLE IF NOT EXISTS asset_events (
  id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  date TEXT NOT NULL, type TEXT NOT NULL, cost REAL DEFAULT 0, notes TEXT);

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

CREATE INDEX IF NOT EXISTS idx_runs_due ON job_runs(due_date, status);
CREATE INDEX IF NOT EXISTS idx_moves_stock ON stock_moves(stock_id);
CREATE INDEX IF NOT EXISTS idx_spend_date ON spend(date);
CREATE INDEX IF NOT EXISTS idx_harvest_date ON harvests(date);
"""


def connect(path=None):
    path = path or config.DB_PATH
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(path, detect_types=0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init(conn):
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
}
