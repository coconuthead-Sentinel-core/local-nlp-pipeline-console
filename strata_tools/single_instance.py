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


#: Windows appends this to the title of a window that has stopped
#: pumping messages, and the ghost window carrying it belongs to
#: ``dwm.exe`` rather than to the application at all.
GHOST_SUFFIX = "(Not Responding)"


def choose_raisable(candidates, lock_pid):
    """Which window a standing-down launch should raise, or ``None``.

    **The incident this exists for (2026-11-24).** The owner reported
    that clicking the icon did nothing and the console never opened.
    Reproduced by launching it the way the shortcut does: no window
    appeared at all. The first console had stopped responding under
    memory pressure, its process was still alive, so the lock said
    "already running" -- and the raise step found a window with the
    right title, called ``SetForegroundWindow`` on it, and reported
    **success**. The launch then exited having opened nothing. Every
    later click did the same. The console was not failing to start; it
    was standing down, over and over, in favour of a corpse.

    Two facts were available and unused. Windows knew the window was
    hung -- it had already renamed the ghost "Strata Console -- web
    shell *(Not Responding)*". And that ghost belongs to ``dwm.exe``,
    so a title match alone could pick a window the application does
    not even own.

    ``candidates`` is what the shell gathered, one dict per window with
    ``pid``, ``hung`` and ``title``. Pure: the OS questions are asked
    outside and the choosing is arithmetic over their answers.

    The order is the whole rule:

    1. **Drop ghosts.** A title carrying ``(Not Responding)`` is
       Windows' own stand-in, not the app's window.
    2. **Drop hung windows.** Raising one is precisely what produced
       "nothing happened"; it cannot come to the front.
    3. **Prefer the process the lock names.** That is the instance we
       stood down for. Another process with the same title is not it.
    4. **Nothing left -> ``None``**, which the shell must treat as "no
       window answered" and start normally. An app that will not open is
       the louder defect, and that escape hatch already existed -- it
       was simply never reachable, because "found" was being used where
       "can actually be raised" was meant.
    """
    live = [c for c in (candidates or [])
            if not str(c.get("title", "")).rstrip().endswith(GHOST_SUFFIX)
            and not c.get("hung", False)]
    if not live:
        return None
    if lock_pid is not None:
        for c in live:
            try:
                if int(c.get("pid", -1)) == int(lock_pid):
                    return c
            except (TypeError, ValueError):
                continue
        # The lock's process has no raisable window of its own. Raising
        # some other console's window would move a window the owner did
        # not ask about and still leave this click unexplained.
        return None
    return live[0]


def unresponsive_message(pid):
    """What to say when the instance we stood down for is not answering.

    Says the number, names the state, and states what happens next --
    the three things whose absence made this take a week to see.
    """
    return (f"Strata Console (process {pid}) is running but not "
            f"responding, so its window cannot be brought to the front. "
            f"Starting a fresh console. The stuck one is still using "
            f"memory -- closing it is worth doing.")
