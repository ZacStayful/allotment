"""The paperwork: how you get in, and what you signed up to.

Two things live here, because they arrived in the same envelope and are wanted
in the same moment - standing at a locked gate, or arguing with yourself about
whether a polytunnel is allowed.

**No code, password or account number is in this file.** The repository is
public, and section 6.2 of the Constitution says members may not pass on padlock
codes without the Committee's written permission - so a gate code committed to
source is a published gate code and a breach of the tenancy in one line. The
seed carries the labels, the notes and the addresses; the values go into the
database through `plot access` or the Access page, and stay there, behind the
login, in a private database.

The documents themselves are the opposite: they are given to every member, they
say what the plot may and may not be, and half the rule engine is an encoding of
them. They ship as text in `allotment/docs/` and are seeded into the database so
the phone in the shed has them without a signal.
"""

import html as html_
import io
import os
import re
import zipfile
from datetime import date, datetime

from . import config

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
MAX_BYTES = 3 * 1024 * 1024
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
FILE_TYPES = {
    "application/pdf": ".pdf",
    DOCX: ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}
KINDS = ("tenancy", "association", "correspondence", "permission", "other")

# What can be recorded, and what it is for. Values deliberately absent.
ACCESS = [
    dict(key="main_gate", label="Main gate", kind="code", pos=10,
         notes="Lock the gate and turn the code on the way in and on the way out. "
               "The Committee change it from time to time and give notice first. "
               "Not to be passed outside the family - Constitution 6.2."),
    dict(key="car_park", label="Car park gate", kind="code", pos=20,
         notes="No vehicle access beyond the car park: everything comes down by barrow."),
    dict(key="nsalg", label="National Allotment Society", kind="login", pos=30,
         url="https://www.nsalg.org.uk",
         notes="Membership comes with the plot. The membership number is the user name."),
    dict(key="facebook", label="Plot holders' Facebook group", kind="group", pos=40,
         url="https://www.facebook.com/search/top?q=Albert%20Village%20Allotments",
         notes="Private group. Search Albert Village Allotments, ask to join, answer "
               "the questions and the Committee approve it."),
    dict(key="committee", label="Committee", kind="contact", pos=50,
         notes="Email, the Facebook group, or a chat at the plots."),
    dict(key="subscription", label="Subscription payment", kind="payment", pos=60,
         notes="Bank transfer. Reference is your name and plot letter."),
]

DOCUMENTS = [
    dict(doc_key="tenancy_agreement", file="tenancy-agreement.txt", kind="tenancy",
         title="Tenancy Agreement", dated="2024-01-24",
         summary="What the plot is let on. Rent on 1 January, cultivation, structures, "
                 "sprays, inspections, and how either side ends it."),
    dict(doc_key="rules", file="rules.txt", kind="association",
         title="Rules of the Association", dated="2024-01-24",
         summary="Site conduct and the hard limits: organic only, locked gates, "
                 "structure dimensions, bonfires, no vehicle access."),
    dict(doc_key="constitution", file="constitution.txt", kind="association",
         title="Constitution", dated="2024-01-24",
         summary="How the Association is run: membership, subscriptions and their "
                 "proration, the AGM, the Committee, finance, dissolution."),
]

# The clauses that cost money or the plot if they are forgotten, and where each
# one is. The ones marked encoded are already enforced by the jobs engine - the
# rest are here because no software can enforce them for you.
OBLIGATIONS = [
    ("Rent on 1 January", "Tenancy Agreement 2",
     "£%.2f a year, in advance. In arrears past 31 January and membership is held "
     "to have ceased. A first part-year is prorated by quarter: 100%% to March, 75%% "
     "to June, 50%% to September, 25%% to December." % config.SUBSCRIPTION, True),
    ("Organic only", "Rules 8, Tenancy Agreement 3.13",
     "Certified organic or Soil Association approved. Non-organic weedkiller or "
     "pesticide is prohibited outright.", True),
    ("Nothing built without written permission", "Rules 18, Tenancy Agreement 3.10",
     "No shed, tunnel, greenhouse or fruit cage until the Committee say so in "
     "writing. No glass, no bricks and mortar. Full plot maximum 4 m x 2 m; "
     "polytunnel placement is approved separately so it does not shade a neighbour.",
     True),
    ("The metre by the fence stays clear", "Tenancy Agreement 3.9",
     "One metre between the boundary fence and the plot, kept clear by the tenant. "
     "Not a growing zone, and the rotation validator refuses to assign it.", True),
    ("Water off November to March", "Rules 11",
     "The Committee can extend either end, and can impose a hosepipe ban at any "
     "time. Interfering with the supply ends the membership.", True),
    ("Inspections every four weeks from week 4", "Tenancy Agreement 3.16",
     "And at any other time. A plot below standard gets a warning in writing; no "
     "significant improvement by the next inspection can end the agreement.", True),
    ("No vehicle access", "Rules 20",
     "Driving across the footpaths can end the tenancy with immediate effect. Bulk "
     "deliveries come down by barrow.", True),
    ("Cultivated, tidy, reasonably weed free", "Rules 7",
     "Four weeks' written notice to improve, or an explanation, then notice to quit.",
     False),
    ("Gates locked every time", "Rules 10",
     "Even for a few minutes. The code is not to be shared outside the family.", False),
    ("Garden waste off site", "Rules 12",
     "Anything not composted goes home. Soil may not be removed from the site.", False),
    ("No subletting or transfer", "Rules 3, Tenancy Agreement 3.6",
     "Neither the plot nor any part of it, without the Committee's written "
     "permission. Moving plots is an application in writing.", False),
    ("Bonfires need permission in writing", "Rules 13",
     "Dry garden waste from the allotments only, never plastics, never unattended, "
     "out before you leave.", False),
    ("No trees but dwarf fruit, no living hedges", "Rules 9, Tenancy Agreement 3.3",
     "And dwarf varieties still need written permission.", False),
    ("Tell the Secretary within 28 days", "Tenancy Agreement 3.15",
     "Any change of name, address, email or phone number.", False),
    ("Notice to leave is fourteen days", "Tenancy Agreement 4.2",
     "In writing, expiring on any day. The Association's notice to you is one "
     "month. No refunds once the agreement is signed.", False),
]


def now():
    return datetime.now().isoformat(timespec="seconds")


# ------------------------------------------------------------------- access

def all_access(conn):
    return conn.execute("SELECT * FROM site_access ORDER BY pos, id").fetchall()


def get_access(conn, key):
    return conn.execute("SELECT * FROM site_access WHERE key=?", (key,)).fetchone()


def set_access(conn, key, secret=None, identity=None, notes=None, url=None, label=None):
    """Record a code, a login or a set of bank details. Returns the row.

    Only the fields given are touched, so changing the gate code does not wipe
    the note that says it changes. An empty box means "leave it alone" and not
    "delete it": the form that sets a new gate code is the same form that shows
    the old one, and submitting it with the password field untouched must not
    lose the code. `clear_access` is how something is deliberately removed.
    """
    row = get_access(conn, key)
    if row is None:
        raise KeyError("no such access entry: %s. Known: %s"
                       % (key, ", ".join(a["key"] for a in ACCESS)))
    fields, params = [], []
    for name, value in (("secret", secret), ("identity", identity),
                        ("notes", notes), ("url", url), ("label", label)):
        if value is not None and value.strip():
            fields.append("%s=?" % name)
            params.append(value.strip())
    if not fields:
        return row
    fields.append("updated=?")
    params.extend([now(), key])
    conn.execute("UPDATE site_access SET %s WHERE key=?" % ",".join(fields), params)
    conn.commit()
    return get_access(conn, key)


def clear_access(conn, key):
    conn.execute("UPDATE site_access SET secret=NULL,identity=NULL,updated=? WHERE key=?",
                 (now(), key))
    conn.commit()


def mask(secret):
    """Enough to tell two codes apart, not enough to open the gate with."""
    if not secret:
        return "not recorded"
    if len(secret) <= 6:            # a gate code is short enough to guess from a hint
        return "•" * len(secret)
    return "•" * (len(secret) - 2) + secret[-2:]


def missing(conn):
    """Entries that have a place but no value yet - the Access page says so
    rather than showing an empty box and leaving you to wonder."""
    return [r["label"] for r in all_access(conn)
            if r["kind"] in ("code", "login") and not r["secret"]]


# ---------------------------------------------------------------- documents

def all_documents(conn, with_body=False):
    cols = ("id,doc_key,title,kind,dated,summary,filename,mime,size,added"
            + (",body" if with_body else ""))
    return conn.execute("SELECT %s FROM documents ORDER BY kind, title" % cols).fetchall()


def get_document(conn, ident):
    """By id or by key, whichever was asked for."""
    try:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (int(ident),)).fetchone()
    except (TypeError, ValueError):
        row = None
    if row is None:
        row = conn.execute("SELECT * FROM documents WHERE doc_key=?", (str(ident),)).fetchone()
    if row is None:
        return None
    out = dict(row)
    if out.get("bytes") is not None:
        out["bytes"] = bytes(out["bytes"])      # psycopg2 hands back a memoryview
    return out


def docx_text(data):
    """The readable text of a .docx, with the standard library and nothing else.

    A .docx is a zip with an XML document in it; paragraphs are <w:p> and the
    words are the text inside. Numbering and styling are lost, which is the right
    trade: what is wanted is the sentence you are trying to remember, searchable,
    on a phone, not a facsimile.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", "replace")
    except (zipfile.BadZipFile, KeyError):
        return None
    xml = re.sub(r"<w:tab[^>]*/>", "    ", xml)
    xml = re.sub(r"</w:p>", "\n", xml)
    text = html_.unescape(re.sub(r"<[^>]+>", "", xml))
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip() or None


def add_document(conn, title, data=None, mime=None, filename=None, body=None,
                 kind="tenancy", dated=None, summary=None, doc_key=None):
    """Keep a document. Either a file, or text, or both. Returns its id."""
    if data is not None:
        if mime not in FILE_TYPES:
            raise ValueError("%s is not a document this understands. PDF, Word, "
                             "text, JPEG or PNG." % (mime or "that file"))
        if not data:
            raise ValueError("that document arrived empty")
        if len(data) > MAX_BYTES:
            raise ValueError("that document is %.1f MB, over the %.0f MB limit"
                             % (len(data) / 1048576.0, MAX_BYTES / 1048576.0))
        if body is None and mime == DOCX:
            body = docx_text(data)
        if body is None and mime == "text/plain":
            body = data.decode("utf-8", "replace")
    if data is None and not body:
        raise ValueError("a document needs a file or some text")
    if kind not in KINDS:
        kind = "other"
    # A seeded document updates in place; anything added by hand gets its own
    # row even if it is called the same as one already there. Two documents with
    # the same title is a filing problem. Losing one is a worse one.
    key = doc_key or free_key(conn, slugify(title))
    cur = conn.execute(
        "INSERT INTO documents(doc_key,title,kind,dated,summary,body,filename,mime,"
        "bytes,size,added) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(doc_key) DO UPDATE SET "
        "title=excluded.title,kind=excluded.kind,dated=excluded.dated,"
        "summary=excluded.summary,body=excluded.body,filename=excluded.filename,"
        "mime=excluded.mime,bytes=excluded.bytes,size=excluded.size",
        (key, title, kind, dated or date.today().isoformat(), summary, body,
         filename, mime, data, len(data) if data else None, now()))
    conn.commit()
    return cur.lastrowid or get_document(conn, key)["id"]


def delete_document(conn, doc_id):
    cur = conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    return cur.rowcount


def free_key(conn, base):
    key, n = base, 1
    while conn.execute("SELECT 1 FROM documents WHERE doc_key=?", (key,)).fetchone():
        n += 1
        key = "%s_%d" % (base, n)
    return key


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")[:48] or "document"


def search(conn, term, limit=20):
    """Where a phrase appears, and the line it appears on. The point of holding
    the documents at all: 'what did it say about bonfires' answered at the plot."""
    term = (term or "").strip()
    if len(term) < 3:
        return []
    hits = []
    for doc in all_documents(conn, with_body=True):
        for n, line in enumerate((doc["body"] or "").split("\n"), 1):
            if term.lower() in line.lower():
                hits.append({"id": doc["id"], "title": doc["title"], "line": n,
                             "text": line})
                if len(hits) >= limit:
                    return hits
    return hits


# --------------------------------------------------------------------- seed

def seed(conn):
    """Labels, notes and the documents. Never a code or a password."""
    for a in ACCESS:
        conn.execute(
            "INSERT INTO site_access(key,label,kind,url,notes,pos) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET label=excluded.label,kind=excluded.kind,"
            "pos=excluded.pos",
            (a["key"], a["label"], a["kind"], a.get("url"), a.get("notes"), a["pos"]))
        # notes and url are seeded once and then left alone: an edit made on the
        # Access page is a deliberate one and re-seeding must not undo it.
        conn.execute("UPDATE site_access SET notes=COALESCE(notes,?), url=COALESCE(url,?) "
                     "WHERE key=?", (a.get("notes"), a.get("url"), a["key"]))
    for d in DOCUMENTS:
        path = os.path.join(DOCS, d["file"])
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        conn.execute(
            "INSERT INTO documents(doc_key,title,kind,dated,summary,body,added) "
            "VALUES(?,?,?,?,?,?,?) ON CONFLICT(doc_key) DO UPDATE SET "
            "title=excluded.title,kind=excluded.kind,dated=excluded.dated,"
            "summary=excluded.summary,body=excluded.body",
            (d["doc_key"], d["title"], d["kind"], d["dated"], d["summary"], body, now()))
    conn.commit()
    return {"access": len(ACCESS), "documents": len(DOCUMENTS)}
