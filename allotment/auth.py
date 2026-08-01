"""Login. PBKDF2-HMAC-SHA256, server-side sessions, CSRF tokens and a lockout.

Passwords are never stored, only a salted hash. Everything here is constant-time
where it needs to be.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from . import config

ITERATIONS = 240_000


def hash_password(password, salt=None, iterations=ITERATIONS):
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                             bytes.fromhex(salt), iterations)
    return dk.hex(), salt, iterations


def normalise(email):
    return (email or "").strip().lower()


def create_user(conn, email, password, name=None, role="Both"):
    pw, salt, iters = hash_password(password)
    cur = conn.execute(
        "INSERT INTO users(email,name,role,pw_hash,pw_salt,iterations,created) "
        "VALUES(?,?,?,?,?,?,?)",
        (normalise(email), name, role, pw, salt, iters,
         datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    return cur.lastrowid


def set_password(conn, email, password):
    pw, salt, iters = hash_password(password)
    cur = conn.execute(
        "UPDATE users SET pw_hash=?, pw_salt=?, iterations=? WHERE email=?",
        (pw, salt, iters, normalise(email)))
    conn.commit()
    return cur.rowcount


def get_user(conn, email):
    return conn.execute("SELECT * FROM users WHERE email=?", (normalise(email),)).fetchone()


def locked_out(conn, email):
    row = conn.execute("SELECT * FROM login_attempts WHERE email=?",
                       (normalise(email),)).fetchone()
    if row is None or row["failures"] < config.MAX_FAILED_LOGINS:
        return 0
    last = datetime.fromisoformat(row["last_failure"])
    until = last + timedelta(minutes=config.LOCKOUT_MINUTES)
    left = (until - datetime.now()).total_seconds()
    return max(0, int(left / 60) + 1)


def _record_failure(conn, email):
    conn.execute(
        "INSERT INTO login_attempts(email,failures,last_failure) VALUES(?,1,?) "
        "ON CONFLICT(email) DO UPDATE SET failures=failures+1, last_failure=excluded.last_failure",
        (normalise(email), datetime.now().isoformat(timespec="seconds")))
    conn.commit()


def _clear_failures(conn, email):
    conn.execute("DELETE FROM login_attempts WHERE email=?", (normalise(email),))
    conn.commit()


def verify(conn, email, password):
    """Returns the user row, or None. Same cost whether or not the user exists."""
    email = normalise(email)
    user = get_user(conn, email)
    if user is None:
        hash_password(password or "", secrets.token_hex(16))     # equalise timing
        return None
    if locked_out(conn, email):
        return None
    dk, _, _ = hash_password(password or "", user["pw_salt"], user["iterations"])
    if not hmac.compare_digest(dk, user["pw_hash"]):
        _record_failure(conn, email)
        return None
    _clear_failures(conn, email)
    conn.execute("UPDATE users SET last_login=? WHERE id=?",
                 (datetime.now().isoformat(timespec="seconds"), user["id"]))
    conn.commit()
    return user


# ---------------------------------------------------------------- sessions

def create_session(conn, user_id, hours=None):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    now = datetime.now()
    exp = now + timedelta(hours=hours or config.SESSION_HOURS)
    conn.execute("INSERT INTO sessions(token,user_id,csrf,created,expires) VALUES(?,?,?,?,?)",
                 (token, user_id, csrf, now.isoformat(timespec="seconds"),
                  exp.isoformat(timespec="seconds")))
    conn.commit()
    return token, csrf


def session(conn, token):
    if not token:
        return None
    row = conn.execute(
        "SELECT s.token, s.csrf, s.expires, u.id user_id, u.email, u.name, u.role "
        "FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?", (token,)).fetchone()
    if row is None:
        return None
    if datetime.fromisoformat(row["expires"]) < datetime.now():
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
        return None
    return row


def end_session(conn, token):
    conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()


def purge(conn):
    conn.execute("DELETE FROM sessions WHERE expires < ?",
                 (datetime.now().isoformat(timespec="seconds"),))
    conn.commit()


def check_csrf(sess, token):
    return bool(sess) and bool(token) and hmac.compare_digest(sess["csrf"], token)
