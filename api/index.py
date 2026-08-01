"""Vercel entry point.

Vercel's Python runtime scans this file for a top-level `handler`, `app`, or
`application`. It must be a real class *definition* - an assignment like
`handler = server.Handler` is invisible to that check, and the build then
produces no function at all, so every route falls through to Vercel's own 404.

vercel.json rewrites every path here, so this one function serves the whole app.

The hosted copy must use Postgres. A serverless filesystem is read-only apart
from /tmp, and /tmp is wiped between cold starts, so a SQLite file there would
take a logged visit and quietly lose it.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from allotment import server                                        # noqa: E402

server.DB_PATH = None          # None means "use DATABASE_URL"


class handler(server.Handler):
    """The whole app, as the runtime expects to find it."""
