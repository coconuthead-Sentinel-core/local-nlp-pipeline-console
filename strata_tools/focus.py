r"""Focus cycles and experience sampling -- the pure kernel.

**What this is, in standard terms.** A timer fires, and the owner is
offered a two-tap report of how loaded he feels and which mode he is
working in. That is **signal-contingent experience sampling**
(Csikszentmihalyi & Larson, 1987), and the data it produces is
**intensive longitudinal data** supporting an **N-of-1** design.

Experience sampling exists precisely *because* retrospective self-report
is unreliable -- asking at the end of a day produces poor data, and asking
in the moment is the fix. So prompting during the cycle is not a
workaround; it is the method.

**What it records is a SELF-REPORT.** Not cognitive load. Cognitive Load
Theory has its own instruments and a dial is not one of them, and a
control labelled with a state name does not detect that state. The field
is called ``reported_load`` for that reason, and ``SCOPE.md`` §3 makes any
label implying otherwise a defect. The honest framing is what makes the
data admissible, and it costs nothing.

**Scope.** Admitted to ``SCOPE.md`` §1 on 2026-10-15 by owner decision,
under a narrow carve-out in §2: this records and charts, it does not urge.
No streaks, no points, no targets, no encouragement. An abandoned cycle is
**data, not failure**, and nothing here treats it as one.

**Rows, not cells.** A fixed grid cannot model a calendar -- months are
28, 30 or 31 days and the owner's roster is two on, two off, three on. So
``cycles`` is a fact table that grows downward forever and ``days`` is a
small dimension table that stays stable. Every question asked of this
module is a query over those, and no grid is ever resized.

**Pure.** No clock, no database, no threads. The caller supplies every
timestamp, which is what makes the tests deterministic. The timer and the
prompt are UI; this is the part that has to be right first.
"""

PHASES = ("START", "END")
OUTCOMES = ("COMPLETED", "ABANDONED")
DAY_TYPES = ("WORK", "OFF")

LOAD_MIN = 1
LOAD_MAX = 10

# The three tables. Declared here as data so the storage layer has one
# source for them and this module still touches no database.
SCHEMA = (
    """CREATE TABLE IF NOT EXISTS focus_cycles (
        id              INTEGER PRIMARY KEY,
        session_id      TEXT    NOT NULL,
        started_at      TEXT    NOT NULL,
        ended_at        TEXT,
        planned_minutes INTEGER NOT NULL,
        outcome         TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS focus_reports (
        id            INTEGER PRIMARY KEY,
        cycle_id      INTEGER NOT NULL,
        phase         TEXT    NOT NULL,
        reported_load INTEGER NOT NULL,
        mode          TEXT,
        note          TEXT,
        FOREIGN KEY (cycle_id) REFERENCES focus_cycles(id)
    )""",
    """CREATE TABLE IF NOT EXISTS focus_days (
        day            TEXT PRIMARY KEY,
        day_type       TEXT NOT NULL,
        shift_position TEXT,
        hours_slept    REAL
    )""",
)


def new_cycle(session_id, planned_minutes, started_at, cycle_id=None):
    """Open a cycle. Pure -- ``started_at`` comes from the caller."""
    if not session_id:
        raise ValueError("a cycle needs a session_id")
    if planned_minutes < 1:
        raise ValueError(
            f"planned_minutes must be at least 1; got {planned_minutes}"
        )
    if not started_at:
        raise ValueError("a cycle needs a start time")
    return {
        "id": cycle_id,
        "session_id": session_id,
        "started_at": started_at,
        "ended_at": None,
        "planned_minutes": planned_minutes,
        "outcome": None,
    }


def close_cycle(cycle, ended_at, ran_to_end):
    """Close a cycle. Returns a new record; the input is not mutated.

    ``ran_to_end`` false means ABANDONED, which is a *measurement*. A
    cycle cut short is the most informative row this module collects --
    it is how the owner finds the length he can actually finish.
    """
    if not ended_at:
        raise ValueError("closing a cycle needs an end time")
    if ended_at < cycle["started_at"]:
        raise ValueError(
            f"end {ended_at} is before start {cycle['started_at']}"
        )
    closed = dict(cycle)
    closed["ended_at"] = ended_at
    closed["outcome"] = "COMPLETED" if ran_to_end else "ABANDONED"
    return closed


def new_report(cycle_id, phase, reported_load, mode=None, note=None,
               report_id=None):
    """Record one sample. Raises on a load outside the scale.

    A prompt is always skippable, so the absence of a report is normal and
    carries no penalty anywhere in this module. What is *not* allowed is a
    report with a value the scale cannot hold -- that would be a silent
    corruption of the only numbers here.
    """
    if phase not in PHASES:
        raise ValueError(f"phase must be one of {PHASES}; got {phase!r}")
    if not isinstance(reported_load, int) or isinstance(reported_load, bool):
        raise ValueError(
            f"reported_load must be a whole number; got {reported_load!r}"
        )
    if not LOAD_MIN <= reported_load <= LOAD_MAX:
        raise ValueError(
            f"reported_load must be {LOAD_MIN} to {LOAD_MAX}; "
            f"got {reported_load}"
        )
    return {
        "id": report_id,
        "cycle_id": cycle_id,
        "phase": phase,
        "reported_load": reported_load,
        "mode": mode,
        "note": note,
    }


def new_day(day, day_type, shift_position=None, hours_slept=None):
    """One row of the roster. ``hours_slept`` is the named confound.

    Recorded on the owner's instruction so the largest known difference
    between a work day and a rest day stays visible in the data, rather
    than being argued about afterwards.
    """
    if day_type not in DAY_TYPES:
        raise ValueError(f"day_type must be one of {DAY_TYPES}; got {day_type!r}")
    if hours_slept is not None and not 0 <= hours_slept <= 24:
        raise ValueError(f"hours_slept must be 0 to 24; got {hours_slept}")
    return {
        "day": day,
        "day_type": day_type,
        "shift_position": shift_position,
        "hours_slept": hours_slept,
    }


def _day_of(cycle):
    """The calendar day a cycle started on, from an ISO timestamp."""
    return (cycle.get("started_at") or "")[:10]


def completion_rate(cycles):
    """Completed over closed, or None when nothing has closed.

    None rather than zero: a rate of zero means every cycle was abandoned,
    and no data at all means something different. Reporting them the same
    way would be a lie of convenience.
    """
    closed = [c for c in cycles or () if c.get("outcome")]
    if not closed:
        return None
    done = sum(1 for c in closed if c["outcome"] == "COMPLETED")
    return round(done / len(closed), 4)


def summarize_session(session_id, cycles):
    """One session's totals."""
    mine = [c for c in cycles or () if c.get("session_id") == session_id]
    closed = [c for c in mine if c.get("outcome")]
    return {
        "session_id": session_id,
        "cycles_started": len(mine),
        "cycles_closed": len(closed),
        "cycles_completed": sum(1 for c in closed if c["outcome"] == "COMPLETED"),
        "cycles_abandoned": sum(1 for c in closed if c["outcome"] == "ABANDONED"),
        "completion_rate": completion_rate(mine),
        "planned_minutes": sum(c["planned_minutes"] for c in mine),
    }


def _mean(values):
    return round(sum(values) / len(values), 2) if values else None


def load_by_phase(cycle_ids, reports):
    """Mean reported load at start and at end, for a set of cycles."""
    wanted = set(cycle_ids)
    mine = [r for r in reports or () if r.get("cycle_id") in wanted]
    start = [r["reported_load"] for r in mine if r["phase"] == "START"]
    end = [r["reported_load"] for r in mine if r["phase"] == "END"]
    mean_start, mean_end = _mean(start), _mean(end)
    delta = None
    if mean_start is not None and mean_end is not None:
        delta = round(mean_end - mean_start, 2)
    return {
        "reports": len(mine),
        "mean_reported_load_start": mean_start,
        "mean_reported_load_end": mean_end,
        "mean_change": delta,
    }


def compare_by_day_type(cycles, reports, days):
    """One summary row per day type.

    **A difference here is OBSERVED, never CAUSED.** A work day and a rest
    day differ in sleep, food, fatigue, noise and time of day all at once,
    so nothing in this output may be labelled an effect. ``hours_slept`` is
    carried through for exactly that reason -- so the confound is in the
    report rather than in an argument about it afterwards.

    A day type with no cycles is reported as such instead of dividing by
    zero and emitting a plausible nothing.
    """
    day_type_of = {d["day"]: d["day_type"] for d in days or ()}
    slept_on = {d["day"]: d.get("hours_slept") for d in days or ()}

    rows = []
    for day_type in DAY_TYPES:
        mine = [c for c in cycles or ()
                if day_type_of.get(_day_of(c)) == day_type]
        if not mine:
            rows.append({
                "day_type": day_type,
                "cycles": 0,
                "note": "no cycles recorded",
            })
            continue
        slept = [slept_on[_day_of(c)] for c in mine
                 if slept_on.get(_day_of(c)) is not None]
        row = {
            "day_type": day_type,
            "cycles": len(mine),
            "completion_rate": completion_rate(mine),
            "mean_hours_slept": _mean(slept),
            "observed_not_caused": True,
        }
        row.update(load_by_phase([c.get("id") for c in mine], reports))
        rows.append(row)
    return rows


def cycle_length_report(cycles):
    """Completion rate for each planned length the owner has tried.

    This is the point of the whole module. The Pomodoro Technique's
    twenty-five minutes is a popular default, not a validated protocol, so
    there is no standard to deviate from -- and the owner's own data is
    better evidence for his cycle length than any default ever was.

    Sorted by length. A length with nothing closed reports None rather
    than a flattering zero.
    """
    lengths = sorted({c["planned_minutes"] for c in cycles or ()})
    out = []
    for minutes in lengths:
        mine = [c for c in cycles if c["planned_minutes"] == minutes]
        closed = [c for c in mine if c.get("outcome")]
        out.append({
            "planned_minutes": minutes,
            "cycles": len(mine),
            "closed": len(closed),
            "completed": sum(1 for c in closed if c["outcome"] == "COMPLETED"),
            "completion_rate": completion_rate(mine),
        })
    return out


def best_cycle_length(cycles, min_closed=3):
    """The length with the highest completion rate, or None.

    ``min_closed`` guards against crowning a length that was tried twice.
    Returns None when no length has enough closed cycles to say anything,
    which is the honest answer early on and should be shown as such rather
    than filled in with the best of a thin field.
    """
    candidates = [r for r in cycle_length_report(cycles)
                  if r["closed"] >= min_closed and r["completion_rate"] is not None]
    if not candidates:
        return None
    return max(candidates,
               key=lambda r: (r["completion_rate"], r["closed"]))["planned_minutes"]


def validate(cycles, reports, days):
    """Structural problems across the three tables. Empty list is good."""
    problems = []
    ids = [c.get("id") for c in cycles or () if c.get("id") is not None]
    if len(set(ids)) != len(ids):
        problems.append("duplicate cycle id")

    known = set(ids)
    for r in reports or ():
        if r["phase"] not in PHASES:
            problems.append(f"report {r.get('id')}: bad phase {r['phase']!r}")
        if not LOAD_MIN <= r["reported_load"] <= LOAD_MAX:
            problems.append(
                f"report {r.get('id')}: load {r['reported_load']} off scale"
            )
        if known and r.get("cycle_id") not in known:
            problems.append(f"report {r.get('id')}: orphan cycle_id")

    seen_days = set()
    for d in days or ():
        if d["day"] in seen_days:
            problems.append(f"duplicate day {d['day']}")
        seen_days.add(d["day"])
        if d["day_type"] not in DAY_TYPES:
            problems.append(f"day {d['day']}: bad day_type {d['day_type']!r}")

    for c in cycles or ():
        if c.get("outcome") is not None and c["outcome"] not in OUTCOMES:
            problems.append(f"cycle {c.get('id')}: bad outcome {c['outcome']!r}")
        if c.get("ended_at") and c["ended_at"] < c["started_at"]:
            problems.append(f"cycle {c.get('id')}: ends before it starts")
    return problems
