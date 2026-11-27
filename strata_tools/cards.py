r"""Note cards on a coordinate grid -- the pure kernel.

**What this is.** A card is a short note with an ADDRESS: ``H5``, ``A1``,
``Z999``. The address is the point. A title can be forgotten and a search
can miss, but a coordinate can be said out loud, written on paper, and
typed the same way twice. That is what makes the grid worth having for an
owner who works by voice and comes back to things days later.

**Where it comes from.** The browser build of Strata Console has had this
since 2026-09-19 and the laptop never got it: the feature was written in
the published page, and the only thing that reached the repository was a
*snapshot of that page*, which is a record, not code. This module is the
port, in the laptop's own idiom -- pure, standard-library only, tested
headlessly before any UI is wired.

**Two traversal orders, because reading order changes what you notice.**
``ROW_MAJOR`` walks A1, B1, C1 … then the next row. ``COLUMN_MAJOR``
walks A1, A2, A3 … then the next column. The same cards in a different
order surface different neighbours, which is the whole value of putting
notes on a grid instead of in a list. Neither order is more correct; the
owner picks.

**What this module deliberately does NOT do.** It does not store, and it
does not decide what the assistant may read. Storage belongs to
``StrataDB``; what reaches the model belongs to ``context_sources.py``.
Keeping the rules here and the effects there is what let the focus kernel
be tested without a database, and the same applies now.
"""

import re

#: A cell address: one letter, then one to three digits. The browser build
#: has used exactly this since the feature was written, and a stored card
#: must keep reading after the port -- so the rule is copied, not improved.
CELL_PATTERN = re.compile(r"^([A-Z])([0-9]{1,3})$")

#: Zones, shared with the operating modes and the focus kernel. One
#: vocabulary across the app: a card's zone means what a mode means.
ZONES = ("GREEN", "YELLOW", "RED")

#: Cognitive load, the same 1-10 scale the focus report uses. It records
#: what the owner REPORTS about a card, never a measurement of him.
LOAD_MIN = 1
LOAD_MAX = 10

#: Traversal orders. Row-major reads across, then down; column-major reads
#: down, then across.
ROW_MAJOR = "ROW_MAJOR"
COLUMN_MAJOR = "COLUMN_MAJOR"
ORDERS = (ROW_MAJOR, COLUMN_MAJOR)

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS cards (
        id        INTEGER PRIMARY KEY,
        cell      TEXT    NOT NULL UNIQUE,
        title     TEXT    NOT NULL,
        body      TEXT    NOT NULL,
        zone      TEXT    NOT NULL,
        load      INTEGER,
        created   TEXT    NOT NULL,
        updated   TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS card_links (
        id       INTEGER PRIMARY KEY,
        src      TEXT NOT NULL,
        dst      TEXT NOT NULL,
        relation TEXT NOT NULL,
        FOREIGN KEY (src) REFERENCES cards(cell),
        FOREIGN KEY (dst) REFERENCES cards(cell)
    )""",
)

#: How one card may relate to another. Deliberately small: a vocabulary
#: nobody can remember is a vocabulary nobody uses.
RELATIONS = ("relates to", "depends on", "blocks", "child of", "references")


def parse_cell(text):
    """``("H", 5)`` from ``"H5"``, or ``None``.

    Case-insensitive on the way in, because the owner dictates and a
    speech engine capitalises inconsistently. Everything downstream sees
    the canonical upper-case form.
    """
    if not text:
        return None
    m = CELL_PATTERN.match(str(text).strip().upper())
    if not m:
        return None
    row = int(m.group(2))
    if row < 1:
        return None                 # H0 is not a cell; rows start at one
    return (m.group(1), row)


def format_cell(column, row):
    """``"H5"`` from ``("H", 5)``. Raises on anything the grid cannot hold."""
    col = str(column).strip().upper()
    if len(col) != 1 or not col.isalpha():
        raise ValueError(f"a column is one letter A-Z; got {column!r}")
    row = int(row)
    if not 1 <= row <= 999:
        raise ValueError(f"a row is 1 to 999; got {row}")
    return f"{col}{row}"


def is_cell(text):
    """Does this look like an address rather than a search phrase?

    The search box takes both, so this is the fork: ``H5`` jumps, and
    ``box model`` searches. A phrase that happens to look like a cell is
    treated as a cell, which is why the pattern is anchored and narrow.
    """
    return parse_cell(text) is not None


def new_card(cell, title, body, created_at, zone="GREEN", load=None):
    """One card. Pure -- ``created_at`` comes from the caller.

    Validation is strict on the way in because a card is meant to outlive
    the session that wrote it: a bad zone or an off-scale load stored
    today is a silent corruption of the only structured fields here.
    """
    parsed = parse_cell(cell)
    if parsed is None:
        raise ValueError(
            f"a cell is a letter and 1-3 digits, like H5; got {cell!r}")
    # `str(None)` is the four-character string "None", which is truthy --
    # so a missing title would have been filed as a card literally named
    # None. Check the value before stringifying it.
    if title is None or not str(title).strip():
        raise ValueError("a card needs a title")
    if zone not in ZONES:
        raise ValueError(f"zone must be one of {ZONES}; got {zone!r}")
    if load is not None:
        if not isinstance(load, int) or isinstance(load, bool):
            raise ValueError(f"load must be a whole number; got {load!r}")
        if not LOAD_MIN <= load <= LOAD_MAX:
            raise ValueError(
                f"load must be {LOAD_MIN} to {LOAD_MAX}; got {load}")
    if not created_at:
        raise ValueError("a card needs a creation time")
    return {
        "cell": format_cell(*parsed),
        "title": str(title).strip(),
        "body": str(body or ""),
        "zone": zone,
        "load": load,
        "created": created_at,
        "updated": None,
    }


def new_link(src, dst, relation):
    """One edge between two cards.

    A card may not link to itself: a self-edge adds nothing a reader can
    follow and makes every traversal that walks links a potential loop.
    """
    a, b = parse_cell(src), parse_cell(dst)
    if a is None or b is None:
        raise ValueError(f"both ends must be cells; got {src!r} and {dst!r}")
    if a == b:
        raise ValueError(f"a card cannot link to itself ({src})")
    if relation not in RELATIONS:
        raise ValueError(f"relation must be one of {RELATIONS}; got {relation!r}")
    return {"src": format_cell(*a), "dst": format_cell(*b),
            "relation": relation}


def sort_key(card, order=ROW_MAJOR):
    """Where a card falls in a traversal.

    Row-major reads across a row then drops down -- A1, B1, C1, then A2.
    Column-major reads down a column then moves right -- A1, A2, A3, then
    B1. The same cards in a different order put different neighbours side
    by side, which is the reason to use a grid rather than a list.
    """
    if order not in ORDERS:
        raise ValueError(f"order must be one of {ORDERS}; got {order!r}")
    parsed = parse_cell(card.get("cell"))
    if parsed is None:
        # An unreadable address sorts last rather than raising: one bad
        # row must not make the whole grid unwalkable.
        return (1, "", 0)
    column, row = parsed
    if order == ROW_MAJOR:
        return (0, row, column)
    return (0, column, row)


def walk(cards, order=ROW_MAJOR):
    """Every card in the chosen reading order.

    The order is checked HERE rather than left to ``sort_key``: on an
    empty grid ``sorted`` never calls the key function, so a misspelled
    order would pass silently and only fail once the owner had cards --
    which is the worst possible moment to find out.
    """
    if order not in ORDERS:
        raise ValueError(f"order must be one of {ORDERS}; got {order!r}")
    return sorted(cards or (), key=lambda c: sort_key(c, order))


def neighbours(cards, cell):
    """The four cards adjacent to a cell: up, down, left, right.

    Returned as a dict so a caller can say which direction was empty.
    Adjacency is what a grid buys over a list, and it is only useful if
    the gaps are visible too.
    """
    parsed = parse_cell(cell)
    if parsed is None:
        raise ValueError(f"not a cell: {cell!r}")
    column, row = parsed
    at = {}
    for card in cards or ():
        p = parse_cell(card.get("cell"))
        if p is not None:
            at[p] = card
    left = chr(ord(column) - 1) if column > "A" else None
    right = chr(ord(column) + 1) if column < "Z" else None
    return {
        "up": at.get((column, row - 1)) if row > 1 else None,
        "down": at.get((column, row + 1)) if row < 999 else None,
        "left": at.get((left, row)) if left else None,
        "right": at.get((right, row)) if right else None,
    }


def occupied(cards):
    """Every address in use, as a set of ``(column, row)`` pairs."""
    out = set()
    for card in cards or ():
        p = parse_cell(card.get("cell"))
        if p is not None:
            out.add(p)
    return out


def next_free(cards, order=ROW_MAJOR, start_column="A", start_row=1):
    """The first empty address in the chosen reading order, or None.

    So a card can be filed without the owner having to remember what is
    already taken -- which is the difference between a grid he uses and a
    grid he has to maintain.
    """
    taken = occupied(cards)
    columns = [chr(c) for c in range(ord(start_column.upper()), ord("Z") + 1)]
    rows = range(start_row, 1000)
    if order == COLUMN_MAJOR:
        pairs = ((col, row) for col in columns for row in rows)
    elif order == ROW_MAJOR:
        pairs = ((col, row) for row in rows for col in columns)
    else:
        raise ValueError(f"order must be one of {ORDERS}; got {order!r}")
    for col, row in pairs:
        if (col, row) not in taken:
            return format_cell(col, row)
    return None                                   # pragma: no cover


def find(cards, query, order=ROW_MAJOR):
    """Cards matching a query: an exact cell, or words in title and body.

    One entry point for both, because the owner types into one box. A
    query shaped like an address is treated as one -- a jump, not a
    search -- and anything else is matched on words, so ``box model``
    finds a card titled "The box model" whichever way round he says it.
    """
    text = str(query or "").strip()
    if not text:
        return []
    if is_cell(text):
        want = format_cell(*parse_cell(text))
        return [c for c in cards or () if c.get("cell") == want]
    words = [w for w in re.split(r"\W+", text.lower()) if w]
    if not words:
        return []
    hits = []
    for card in cards or ():
        hay = f"{card.get('title', '')} {card.get('body', '')}".lower()
        score = sum(1 for w in words if w in hay)
        if score:
            hits.append((score, card))
    hits.sort(key=lambda pair: (-pair[0], sort_key(pair[1], order)))
    return [card for _score, card in hits]


def describe(card):
    """One line naming a card, for a transcript or a spoken reply."""
    cell = card.get("cell", "?")
    title = card.get("title", "(untitled)")
    zone = card.get("zone", "")
    load = card.get("load")
    bits = [f"{cell} — {title}"]
    if zone:
        bits.append(zone.lower())
    if load is not None:
        bits.append(f"load {load}")
    return " · ".join(bits)


def validate(cards, links):
    """Structural problems across the grid. Empty list is good."""
    problems = []
    seen = set()
    for card in cards or ():
        cell = card.get("cell")
        if parse_cell(cell) is None:
            problems.append(f"card {cell!r}: not a valid cell address")
            continue
        if cell in seen:
            problems.append(f"duplicate card at {cell}")
        seen.add(cell)
        if card.get("zone") not in ZONES:
            problems.append(f"card {cell}: bad zone {card.get('zone')!r}")
        load = card.get("load")
        if load is not None and not LOAD_MIN <= load <= LOAD_MAX:
            problems.append(f"card {cell}: load {load} off scale")
    for link in links or ():
        for end in ("src", "dst"):
            if link.get(end) not in seen and seen:
                problems.append(
                    f"link {link.get('src')}->{link.get('dst')}: "
                    f"{end} names no card")
        if link.get("relation") not in RELATIONS:
            problems.append(
                f"link {link.get('src')}->{link.get('dst')}: "
                f"bad relation {link.get('relation')!r}")
    return problems
