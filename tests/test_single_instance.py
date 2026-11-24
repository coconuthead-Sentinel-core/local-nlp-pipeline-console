"""Tests for the one-console rule.

Written against the real incident: three live pythonw processes, two
holding windows, on a machine with 764 MB free. The decision must be
right in every direction, because both failure modes hurt -- a second
console competes for memory the first one needs, and a stale lock that
bars the door means the app simply will not start.
"""

import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from strata_tools import single_instance as si


DEAD = lambda pid: False
ALIVE = lambda pid: True


class ParseTests(unittest.TestCase):
    def test_a_well_formed_lock_reads_back(self):
        pid, started = si.parse_lock("4321 2026-10-17T04:08:00")
        self.assertEqual(pid, 4321)
        self.assertEqual(started, "2026-10-17T04:08:00")

    def test_a_pid_only_lock_is_accepted(self):
        self.assertEqual(si.parse_lock("4321")[0], 4321)

    def test_the_round_trip_holds(self):
        text = si.render_lock(99, "2026-10-17T04:08:00")
        self.assertEqual(si.parse_lock(text)[0], 99)

    def test_every_malformed_shape_reads_as_no_lock(self):
        # A corrupt lock must never stop the console starting.
        for bad in ("", "   ", None, "not-a-pid", "-5", "0",
                    "\n\n", "abc 123"):
            with self.subTest(text=repr(bad)):
                self.assertEqual(si.parse_lock(bad), (None, None))


class DecideTests(unittest.TestCase):
    def test_no_lock_means_start(self):
        self.assertEqual(si.decide("", 100, DEAD), si.PROCEED)
        self.assertEqual(si.decide(None, 100, ALIVE), si.PROCEED)

    def test_a_live_other_instance_means_defer(self):
        self.assertEqual(
            si.decide(si.render_lock(55, "t"), 100, ALIVE), si.DEFER)

    def test_a_dead_instance_means_start(self):
        """A stale lock is not a running console.

        Refusing to start because of a file left by a process that died
        is worse than starting twice -- it is an app that cannot be
        opened at all, with no way for the owner to see why.
        """
        self.assertEqual(
            si.decide(si.render_lock(55, "t"), 100, DEAD), si.PROCEED)

    def test_our_own_lock_never_locks_us_out(self):
        self.assertEqual(
            si.decide(si.render_lock(100, "t"), 100, ALIVE), si.PROCEED)

    def test_a_corrupt_lock_never_bars_the_door(self):
        self.assertEqual(si.decide("garbage", 100, ALIVE), si.PROCEED)

    def test_an_unanswerable_liveness_check_starts_anyway(self):
        def explode(pid):
            raise OSError("no process table today")
        # A console that will not open is the louder defect.
        self.assertEqual(
            si.decide(si.render_lock(55, "t"), 100, explode), si.PROCEED)

    def test_the_pid_is_compared_as_a_number_not_a_string(self):
        # "100" == 100 is False in Python; getting this wrong would make
        # the app defer to itself and never open.
        self.assertEqual(
            si.decide(si.render_lock(100, "t"), "100", ALIVE), si.PROCEED)


class MessageTests(unittest.TestCase):
    def test_deferring_says_so_and_names_the_instance(self):
        """Silence is what produced three processes.

        The owner clicked, nothing appeared, so he clicked again. A
        second launch that stands down without a word repeats exactly
        that experience.
        """
        msg = si.defer_message(4321)
        self.assertIn("4321", msg)
        self.assertIn("already running", msg)
        self.assertIn("front", msg)

    def test_the_lock_is_human_readable(self):
        # A lock nobody can read is a lock nobody can clear by hand when
        # it goes wrong.
        text = si.render_lock(4321, "2026-10-17T04:08:00")
        self.assertIn("4321", text)
        self.assertTrue(text.endswith("\n"))


class PathTests(unittest.TestCase):
    def test_the_lock_sits_in_the_install(self):
        """Beside the database, not in %TEMP%.

        The owner's own temp sweeps clear %TEMP%; a lock that vanishes
        there would silently stop guarding anything.
        """
        p = si.lock_path(os.path.join("C:", "install"))
        self.assertTrue(p.endswith(si.LOCK_NAME))
        self.assertIn("install", p)
        self.assertNotIn("Temp", p)


TITLE = "Strata Console — web shell"
GHOST = TITLE + " " + si.GHOST_SUFFIX


def win(pid, hung=False, title=TITLE):
    return {"pid": pid, "hung": hung, "title": title}


class ChooseRaisableTests(unittest.TestCase):
    """FB-016 -- the click that deferred to a corpse, every time.

    Reproduced on the owner's machine 2026-11-24: process 13064 alive,
    its window hung, Windows showing a dwm ghost titled "... (Not
    Responding)". Launching the way the shortcut does opened nothing at
    all, and reported nothing either.
    """

    def test_a_healthy_window_of_the_locked_process_is_raised(self):
        chosen = si.choose_raisable([win(13064)], 13064)
        self.assertEqual(chosen["pid"], 13064)

    def test_a_hung_window_is_never_chosen(self):
        # The whole defect in one assertion.
        self.assertIsNone(si.choose_raisable([win(13064, hung=True)], 13064))

    def test_the_dwm_ghost_is_never_chosen(self):
        # Belongs to dwm.exe, matched the old prefix test, and raising it
        # did nothing while reporting success.
        self.assertIsNone(
            si.choose_raisable([win(1880, title=GHOST)], 13064))

    def test_the_real_window_is_preferred_over_its_own_ghost(self):
        chosen = si.choose_raisable(
            [win(1880, hung=True, title=GHOST), win(13064)], 13064)
        self.assertEqual(chosen["pid"], 13064)

    def test_another_process_window_is_not_raised_in_its_place(self):
        # Raising a console the owner did not ask about would move a
        # window AND leave this click unexplained.
        self.assertIsNone(si.choose_raisable([win(999)], 13064))

    def test_a_minimised_but_healthy_window_is_still_raisable(self):
        # FB-014 raised one that was minimised to -18286; being
        # minimised is not being hung.
        chosen = si.choose_raisable([win(23392)], 23392)
        self.assertIsNotNone(chosen)

    def test_no_candidates_at_all_yields_none(self):
        self.assertIsNone(si.choose_raisable([], 13064))
        self.assertIsNone(si.choose_raisable(None, 13064))

    def test_a_corrupt_lock_falls_back_to_any_healthy_window(self):
        # parse_lock returns None for a corrupt lock; a healthy console
        # on screen is still better than claiming none exists.
        chosen = si.choose_raisable([win(4242)], None)
        self.assertEqual(chosen["pid"], 4242)

    def test_a_corrupt_lock_still_refuses_a_hung_window(self):
        self.assertIsNone(si.choose_raisable([win(4242, hung=True)], None))

    def test_an_unparseable_pid_is_skipped_not_raised_on(self):
        self.assertIsNone(si.choose_raisable([win("not-a-pid")], 13064))

    def test_a_string_pid_matching_the_lock_still_matches(self):
        # The integer-versus-string comparison that FB-014's tests call
        # out as the bug that would make the app defer to itself.
        chosen = si.choose_raisable([win("13064")], 13064)
        self.assertIsNotNone(chosen)

    def test_the_unresponsive_message_names_the_pid_and_what_happens(self):
        msg = si.unresponsive_message(13064)
        self.assertIn("13064", msg)
        self.assertIn("not", msg.lower())
        self.assertIn("starting a fresh console", msg.lower())


if __name__ == "__main__":
    unittest.main()
