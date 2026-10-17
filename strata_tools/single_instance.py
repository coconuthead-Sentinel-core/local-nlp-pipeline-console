r"""One console, not three -- the pure decision.

**The incident this exists for (2026-10-17).** The owner double-clicked
the desktop icon, nothing appeared, so he clicked again. And again.
Three ``pythonw`` processes were found running, two holding real windows
titled "Strata Console -- web shell": one on screen at 1111x543, one
minimized to -18286, and a third with no window at all.

Nothing was wrong with the launcher or the code. The machine had **764 MB
free of 7,878**, Windows was compressing 534 MB of pages to cope, and
WebView2 could not paint the first window fast enough to look like
anything had happened. So the app's own answer to being slow under memory
pressure was to let the owner start two more copies of itself, each one
taking memory from the copy that was already struggling.

That is this module's whole point: **the second click must help, not
compete.** A console already running is raised; a new one is not started.

**Pure by design.** Deciding is separated from doing because the doing is
all platform: a lock file, an OS process table, a window handle. The
decision -- proceed, or defer to the instance already there -- is
arithmetic over facts the shell gathers, and it is the part that must be
right. ``strata_web.py`` performs the effects.

**A stale lock must never bar the door.** If the recorded process is gone
-- a crash, a kill, a power cut -- the lock is meaningless and the new
instance proceeds. An app that refuses to start because of a file left by
a process that died a week ago is worse than an app that starts twice.
"""

import os

#: The lock file's name. It lives beside the database rather than in a
#: temp directory, so it travels with the install and cannot be silently
#: cleared by a cleanup job (see the owner's %TEMP% sweep).
LOCK_NAME = "strata_console.lock"

#: What the shell should do with this launch.
PROCEED = "PROCEED"      # no live instance; start normally
DEFER = "DEFER"          # one is already running; raise it and exit


def lock_path(install_dir):
    """Where the lock lives for a given install."""
    return os.path.join(install_dir, LOCK_NAME)


def render_lock(pid, started_at):
    """The lock file's contents. One line, human-readable on purpose.

    A lock nobody can read is a lock nobody can clear when it goes wrong.
    """
    return f"{int(pid)} {started_at}\n"


def parse_lock(text):
    """``(pid, started_at)`` from a lock file, or ``(None, None)``.

    Every malformed shape returns the empty answer rather than raising:
    a corrupt lock must read as "no lock", so a bad file can never stop
    the console starting.
    """
    if not text:
        return (None, None)
    line = str(text).strip().splitlines()[0] if str(text).strip() else ""
    if not line:
        return (None, None)
    parts = line.split(None, 1)
    try:
        pid = int(parts[0])
    except (ValueError, IndexError):
        return (None, None)
    if pid <= 0:
        return (None, None)
    return (pid, parts[1].strip() if len(parts) > 1 else "")


def decide(lock_text, this_pid, is_alive):
    """Proceed, or defer to the instance already running?

    ``is_alive`` is a callable the shell supplies -- it is the OS question,
    and keeping it out of here is what makes this testable without
    starting real processes.

    Four cases, and the order matters:

    1. No lock, or an unreadable one  -> PROCEED.
    2. The lock names THIS process    -> PROCEED. Re-reading our own lock
       must never lock us out of our own window.
    3. The lock names a dead process  -> PROCEED. A stale lock is not a
       running console, and refusing to start because of a file left by a
       process that died is worse than starting twice.
    4. The lock names a live process  -> DEFER.
    """
    pid, _started = parse_lock(lock_text)
    if pid is None:
        return PROCEED
    if pid == int(this_pid):
        return PROCEED
    try:
        alive = bool(is_alive(pid))
    except Exception:
        # The question could not be answered. Starting is the safer
        # failure: a console that will not open is the louder defect.
        return PROCEED
    return DEFER if alive else PROCEED


def defer_message(pid):
    """What to say when a second launch stands down.

    Named, not silent. "Nothing happened" is the experience that produced
    three processes in the first place.
    """
    return (f"Strata Console is already running (process {pid}). "
            f"Bringing that window to the front instead of starting a "
            f"second one.")
