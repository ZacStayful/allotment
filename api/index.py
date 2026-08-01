"""Vercel entry point.

Vercel's Python runtime wants a BaseHTTPRequestHandler subclass called
`handler`, which is exactly what the server already is. vercel.json rewrites
every route here, so this one function serves the whole app.

The hosted copy must use Postgres. A serverless filesystem is read-only apart
from /tmp, and /tmp is wiped between cold starts, so a SQLite file there would
take your visit log and quietly lose it.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from allotment import server                                        # noqa: E402

server.DB_PATH = None          # None means "use DATABASE_URL"

handler = server.Handler
