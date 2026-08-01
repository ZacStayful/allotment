"""Photographs, stored in the database.

Not on disk: the hosted copy runs on a filesystem that is read-only apart from
/tmp, and /tmp is wiped between requests, so a photo written there would be
accepted and then quietly lost - the worst of both.

They are shrunk in the browser before they are sent, which matters more than it
sounds. A phone camera produces four to twelve megabytes a shot; the hosting
refuses a request body over about four and a half, so a straight upload from a
phone fails on the good photos and works on the bad ones. Shrinking first also
means the plot record stays small enough to be worth keeping.
"""

from datetime import datetime

MAX_BYTES = 3 * 1024 * 1024        # after the browser has shrunk it
TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
         "image/heic": ".heic", "image/heif": ".heif"}

# What a photo can be of. The value is the prefix stored in photos.subject.
SUBJECTS = {
    "receipt": "a till receipt",
    "job": "a job, before or after",
    "zone": "a bed or area of the plot",
    "problem": "something wrong - a pest, a disease, a broken thing",
    "visit": "a visit",
}


def subject(kind, ref=None):
    """"receipt", 12 -> "receipt:12". A kind on its own is allowed: not every
    photo is of something the database has a row for."""
    if kind not in SUBJECTS:
        raise ValueError("unknown photo subject: %s" % kind)
    return "%s:%s" % (kind, ref) if ref not in (None, "") else kind


def add(conn, kind, ref, data, mime, caption=None, taken=None):
    """Store one photo. Returns its id.

    Refuses anything that is not an image and anything oversized, because the
    alternative is a database row holding whatever was posted at it.
    """
    if mime not in TYPES:
        raise ValueError("%s is not an image this understands. JPEG, PNG or WebP."
                         % (mime or "that file"))
    if not data:
        raise ValueError("that photo arrived empty")
    if len(data) > MAX_BYTES:
        raise ValueError("that photo is %.1f MB, over the %.0f MB limit"
                         % (len(data) / 1048576.0, MAX_BYTES / 1048576.0))
    cur = conn.execute(
        "INSERT INTO photos(taken,subject,caption,mime,bytes,size) VALUES(?,?,?,?,?,?)",
        (taken or datetime.now().isoformat(timespec="seconds"),
         subject(kind, ref), caption or None, mime, data, len(data)))
    conn.commit()
    return cur.lastrowid


def get(conn, photo_id):
    row = conn.execute("SELECT * FROM photos WHERE id=?", (photo_id,)).fetchone()
    if row is None:
        return None
    out = dict(row)
    out["bytes"] = bytes(out["bytes"])       # psycopg2 hands back a memoryview
    return out


def of(conn, kind, ref=None, limit=60):
    """Every photo of one thing, newest first, without the image data."""
    return conn.execute(
        "SELECT id,taken,subject,caption,mime,size FROM photos WHERE subject=? "
        "ORDER BY taken DESC, id DESC LIMIT ?", (subject(kind, ref), limit)).fetchall()


def recent(conn, limit=40):
    return conn.execute(
        "SELECT id,taken,subject,caption,mime,size FROM photos "
        "ORDER BY taken DESC, id DESC LIMIT ?", (limit,)).fetchall()


def counts(conn):
    """How many photos of each kind, for a page that wants to say so."""
    out = {}
    for row in conn.execute("SELECT subject, COUNT(*) c FROM photos GROUP BY subject"):
        out[row["subject"].split(":")[0]] = out.get(row["subject"].split(":")[0], 0) + row["c"]
    return out


def delete(conn, photo_id):
    cur = conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))
    conn.commit()
    return cur.rowcount
