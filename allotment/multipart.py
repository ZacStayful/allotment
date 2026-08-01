"""Just enough multipart/form-data to accept a photo and the fields beside it.

The standard library used to do this in `cgi`, which was removed in Python 3.13,
and `email` wants to decode everything as text. A file upload is bytes that must
survive untouched, so this works on bytes throughout and only decodes the parts
that are genuinely text.

Deliberately small: no nested multipart, no chunked encoding, no writing to
temporary files. One form, one or two photos, a handful of fields.
"""

import re

BOUNDARY = re.compile(rb'boundary="?([^";,]+)"?', re.I)
DISPOSITION = re.compile(rb'name="([^"]*)"(?:.*?filename="([^"]*)")?', re.I | re.S)
CONTENT_TYPE = re.compile(rb'^content-type:\s*([^\r\n;]+)', re.I | re.M)


class Part:
    """One field. `filename` and `content_type` are set only for uploads."""

    def __init__(self, name, data, filename=None, content_type=None):
        self.name = name
        self.data = data
        self.filename = filename
        self.content_type = content_type

    @property
    def text(self):
        return self.data.decode("utf-8", "replace")

    @property
    def is_file(self):
        return self.filename is not None


def boundary_of(content_type):
    m = BOUNDARY.search((content_type or "").encode("latin-1"))
    return m.group(1) if m else None


def parse(body, content_type):
    """{name: Part}. Later parts of the same name win, except that an empty file
    input never displaces a real one - browsers send an empty part for a file
    field left untouched."""
    bound = boundary_of(content_type)
    if not bound:
        return {}
    sep = b"--" + bound
    out = {}
    for chunk in body.split(sep):
        if chunk in (b"", b"--", b"--\r\n", b"\r\n") or chunk.startswith(b"--"):
            continue
        head, _, data = chunk.partition(b"\r\n\r\n")
        if not _:
            continue
        m = DISPOSITION.search(head)
        if not m:
            continue
        name = m.group(1).decode("utf-8", "replace")
        # `filename=""` is still a file field - it is what a browser sends for an
        # input left alone - so test for the attribute, not for a non-empty value.
        filename = (m.group(2).decode("utf-8", "replace")
                    if m.group(2) is not None else None)
        ctype = CONTENT_TYPE.search(head)
        data = data[:-2] if data.endswith(b"\r\n") else data       # the trailing CRLF
        part = Part(name, data, filename,
                    ctype.group(1).decode("latin-1").strip() if ctype else None)
        if part.is_file and not part.data and name in out:
            continue
        out[name] = part
    return out
