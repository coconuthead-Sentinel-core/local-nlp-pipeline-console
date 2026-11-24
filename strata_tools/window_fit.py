r"""Where the window may sit -- the pure decision, restored.

**Why this file exists twice.** It existed once as the guard for FB-001,
where a size multiplied by CustomTkinter's 1.75 scaling put the send
button below the bottom of a 1097x617 display. It was deleted on
2026-09-01 with the Tk shell it guarded, and FORMER_BUGS.md says so
plainly: "What is *not* claimed: that those guards still run. They do
not."

Three weeks later the web shell asked WebView2 for a 1000x680 window on
the same laptop, whose work area is 1097x529. Measured on the owner's
screen: the window opened at (50, 90) sized 1000x633, so its bottom edge
landed at 723 against a work area ending at 569 -- **154 pixels of the
application, the message box and Send among them, below the screen.**
The owner reported it as "it does not open", which is the correct reading
of a window whose only usable half is not on the display.

FB-001 did not come back because the lesson was forgotten. It came back
because the guard was removed and nothing replaced it. The comment above
the offending call even claimed the opposite -- "sized as a fraction of
the screen rather than a fixed pixel count ... there is no reason to
import that mistake into a new shell" -- sitting directly on top of
``width=1000, height=680``. A promise in a comment is not a guard.

**The rule, in one sentence.** The window must open entirely inside the
usable area of the display, so every control is reachable without the
owner moving or resizing anything.

**Pseudocode (the design, before the code).**

    AXIS(work, margin, floor):
        inset <- work - 2*margin
        if inset >= floor:  return inset       # margin honoured
        return min(work, floor)                # margin yields to floor,
                                               # floor yields to screen
    FIT(desired, work):
        return min(desired, AXIS(work, ...))   # never larger than usable
    ORIGIN(size, work):
        centre it, then clamp into the work rectangle
    PLAN(desired, work):
        size   <- FIT(desired, work)
        origin <- ORIGIN(size, work)
        return (x, y, w, h)

**Order of yielding matters.** On a work area smaller than the floor the
floor loses. A window smaller than we would like is a window the owner
can use; a window that honours a minimum by hanging off the screen is
FB-001 again. ``MIN_W``/``MIN_H`` are a *resize* floor handed to
pywebview, never a promise about the opening size.

**No guard that cannot fail (NM-003).** The old ``fits_on_screen()`` was
a runtime check the caps made impossible to fail -- "a comment that costs
a function call". So the invariant here is proved by the sweep in
``tests/test_window_fit.py``, not re-asserted at runtime. The one
predicate that *can* fail, ``overflow()``, is for MEASURED numbers: the
real window rectangle read back off the real screen, where reality is
free to disagree with the arithmetic.

Pure: plain integers in, plain integers out. No ctypes, no pywebview, no
I/O. The shell gathers the work area and performs the effects.
"""

#: Breathing room left on each edge of the work area. Not cosmetic: it
#: keeps the window clear of the taskbar's hit zone, which on this laptop
#: occupies the strip the work area already excludes.
MARGIN = 24

#: The resize floor handed to pywebview's ``min_size``. See the module
#: docstring: a work area smaller than this wins against it.
MIN_W = 640
MIN_H = 460

#: What the shell asks for when the screen is big enough to grant it.
DESIRED_W = 1000
DESIRED_H = 680


def _axis(work, margin, floor):
    """The usable extent along one axis. Never exceeds ``work``.

    Pure arithmetic over one dimension, so the two-dimensional cases are
    just this function twice and there is no second code path to get
    wrong.
    """
    work = max(1, int(work))
    margin = max(0, int(margin))
    floor = max(1, int(floor))
    inset = work - 2 * margin
    if inset >= floor:
        return inset
    return min(work, floor)


def usable_box(work_w, work_h, margin=MARGIN):
    """``(max_w, max_h)`` a window may occupy inside a work area."""
    return (_axis(work_w, margin, MIN_W), _axis(work_h, margin, MIN_H))


def fit(desired_w, desired_h, work_w, work_h, margin=MARGIN):
    """``(w, h)`` -- the desired size, capped to what the screen allows."""
    max_w, max_h = usable_box(work_w, work_h, margin)
    return (max(1, min(int(desired_w), max_w)),
            max(1, min(int(desired_h), max_h)))


def origin(w, h, work_x, work_y, work_w, work_h):
    """``(x, y)`` centring a ``w`` x ``h`` window in the work area.

    Clamped into the rectangle afterwards, which matters when the window
    is wider or taller than the area despite ``fit`` -- a caller may pass
    a size this module did not choose, and a negative origin puts the
    title bar above the top edge where it cannot be grabbed.
    """
    work_x, work_y = int(work_x), int(work_y)
    slack_x = max(0, int(work_w) - int(w))
    slack_y = max(0, int(work_h) - int(h))
    return (work_x + min(slack_x, max(0, slack_x // 2)),
            work_y + min(slack_y, max(0, slack_y // 2)))


def plan(desired_w, desired_h, work, margin=MARGIN):
    """``(x, y, w, h)`` for a window, given ``work`` = (x, y, w, h).

    The one function the shell calls. Everything above it is the working
    that makes this line provable.
    """
    work_x, work_y, work_w, work_h = (int(v) for v in work)
    w, h = fit(desired_w, desired_h, work_w, work_h, margin)
    x, y = origin(w, h, work_x, work_y, work_w, work_h)
    return (x, y, w, h)


def overflow(rect, work):
    """How far a MEASURED window escapes the work area, per edge.

    ``rect`` and ``work`` are both (x, y, w, h). Returns a dict of
    ``left/top/right/bottom`` pixel overruns; all zeros means the window
    is fully on screen.

    This is the predicate that is allowed to fail, because its inputs are
    read off the real screen rather than computed here. FB-001 was found
    by measuring, not by reasoning, and NM-005 records the catalog
    reasoning from a contract while the bench measured the owner's
    display and disagreed.
    """
    rx, ry, rw, rh = (int(v) for v in rect)
    wx, wy, ww, wh = (int(v) for v in work)
    return {
        "left": max(0, wx - rx),
        "top": max(0, wy - ry),
        "right": max(0, (rx + rw) - (wx + ww)),
        "bottom": max(0, (ry + rh) - (wy + wh)),
    }


def describe(rect, work):
    """One line naming a measured window's fit. For the bench and the log.

    Silence is what made FB-001 take weeks: the window was wrong on
    screen and nothing in the application ever said a number out loud.
    """
    over = overflow(rect, work)
    escaped = {k: v for k, v in over.items() if v}
    shape = f"{int(rect[2])}x{int(rect[3])} at ({int(rect[0])}, {int(rect[1])})"
    area = f"{int(work[2])}x{int(work[3])} at ({int(work[0])}, {int(work[1])})"
    if not escaped:
        return f"window {shape} fits the work area {area}"
    edges = ", ".join(f"{k} by {v}px" for k, v in sorted(escaped.items()))
    return f"window {shape} escapes the work area {area}: {edges}"
