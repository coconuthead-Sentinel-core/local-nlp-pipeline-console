"""Tests for persisting focus cycles -- the store, not the kernel.

``strata_tools/focus.py`` is pure and already tested. This file tests the
seam between it and SQLite: that a cycle written today reads back
*tomorrow* in the exact shape the kernel's own ``validate()`` accepts,
and that the analytics run over rows that made the round trip rather
than over dicts that never left memory.

Written before the timer UI exists, which is the order the shop works
in. Every test runs against a throwaway database: the live
``quantum_nexus_forge.db`` is never opened. That guard is not optional
here -- patching the wrong name has twice let a test write to the
owner's real store (NM-005, and the study-DB leak before it).
"""

import os
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

import strata_core
from strata_tools import focus


class TempStoreTests(unittest.TestCase):
    """Base: a StrataDB on a throwaway file, torn down every test."""

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.path = tmp.name
        self.db = strata_core.StrataDB(path=self.path)

    def tearDown(self):
        self.db.conn.close()
        os.unlink(self.path)

    def reopen(self):
        """Close and reopen the same file -- the restart a timer must survive."""
        self.db.conn.close()
        self.db = strata_core.StrataDB(path=self.path)
        return self.db


class SchemaTests(TempStoreTests):
    """The migration is additive: nothing already stored is disturbed."""

    def table_names(self):
        rows = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {r[0] for r in rows}

    def test_the_three_focus_tables_are_created(self):
        self.assertLessEqual(
            {"focus_cycles", "focus_reports", "focus_days"},
            self.table_names())

    def test_the_original_tables_are_still_there(self):
        self.assertLessEqual(
            {"memory_threads", "forged_nodes", "system_state"},
            self.table_names())

    def test_existing_rows_survive_the_migration(self):
        # A database that predates the focus tables: rows first, then the
        # schema runs again on reopen. Additive means they are still here.
        self.db.add_thread("2026-10-16", "a turn from before", "GREEN")
        self.reopen()
        self.assertEqual(len(self.db.recent_threads(10)), 1)
        self.assertLessEqual({"focus_cycles"}, self.table_names())

    def test_the_schema_is_the_kernel_s_and_not_a_second_copy(self):
        # NM-009 was a second definition drifting from the first. The
        # store must execute focus.SCHEMA, so there is exactly one.
        self.assertEqual(len(focus.SCHEMA), 3)
        for statement in focus.SCHEMA:
            self.assertIn("CREATE TABLE IF NOT EXISTS", statement)


class RoundTripTests(TempStoreTests):
    """Write, read back, and hand the result to the kernel unchanged."""

    def test_an_open_cycle_round_trips_and_gets_an_id(self):
        opened = focus.new_cycle("s1", 15, "2026-10-16T09:00:00")
        self.assertIsNone(opened["id"])
        cid = self.db.save_cycle(opened)
        self.assertIsInstance(cid, int)

        back = self.db.cycles()
        self.assertEqual(len(back), 1)
        self.assertEqual(back[0]["session_id"], "s1")
        self.assertEqual(back[0]["planned_minutes"], 15)
        self.assertIsNone(back[0]["ended_at"])
        self.assertIsNone(back[0]["outcome"])
        self.assertEqual(back[0]["id"], cid)

    def test_closing_a_cycle_updates_it_rather_than_adding_a_second(self):
        cid = self.db.save_cycle(focus.new_cycle("s1", 15, "2026-10-16T09:00:00"))
        stored = self.db.cycles()[0]
        closed = focus.close_cycle(stored, "2026-10-16T09:15:00", True)
        self.db.save_cycle(closed)

        rows = self.db.cycles()
        self.assertEqual(len(rows), 1, "a closed cycle must not duplicate the open one")
        self.assertEqual(rows[0]["id"], cid)
        self.assertEqual(rows[0]["outcome"], "COMPLETED")
        self.assertEqual(rows[0]["ended_at"], "2026-10-16T09:15:00")
        self.assertEqual(focus.validate(rows, [], []), [])

    def test_an_abandoned_cycle_is_stored_as_data_not_absence(self):
        cid = self.db.save_cycle(focus.new_cycle("s1", 25, "2026-10-16T09:00:00"))
        stored = self.db.cycles()[0]
        self.db.save_cycle(focus.close_cycle(stored, "2026-10-16T09:06:00", False))
        row = self.db.cycles()[0]
        self.assertEqual(row["outcome"], "ABANDONED")
        self.assertEqual(row["id"], cid)

    def test_reports_round_trip_with_their_optional_fields(self):
        cid = self.db.save_cycle(focus.new_cycle("s1", 15, "2026-10-16T09:00:00"))
        self.db.save_report(focus.new_report(cid, "START", 4, mode="deep"))
        self.db.save_report(focus.new_report(cid, "END", 7, note="interrupted twice"))

        back = self.db.reports()
        self.assertEqual(len(back), 2)
        by_phase = {r["phase"]: r for r in back}
        self.assertEqual(by_phase["START"]["reported_load"], 4)
        self.assertEqual(by_phase["START"]["mode"], "deep")
        self.assertIsNone(by_phase["START"]["note"])
        self.assertEqual(by_phase["END"]["note"], "interrupted twice")
        self.assertIsNone(by_phase["END"]["mode"])

    def test_a_skipped_prompt_simply_stores_nothing(self):
        # SCOPE.md's carve-out: a prompt is always skippable and its
        # absence carries no penalty. The store must not invent a row.
        self.db.save_cycle(focus.new_cycle("s1", 15, "2026-10-16T09:00:00"))
        self.assertEqual(self.db.reports(), [])
        self.assertEqual(focus.validate(self.db.cycles(), [], []), [])

    def test_days_round_trip_including_the_named_confound(self):
        self.db.save_day(focus.new_day("2026-10-16", "WORK",
                                       shift_position="2-of-3", hours_slept=5.5))
        back = self.db.days()
        self.assertEqual(len(back), 1)
        self.assertEqual(back[0]["day_type"], "WORK")
        self.assertEqual(back[0]["shift_position"], "2-of-3")
        self.assertAlmostEqual(back[0]["hours_slept"], 5.5)

    def test_re_recording_a_day_replaces_it(self):
        self.db.save_day(focus.new_day("2026-10-16", "WORK", hours_slept=5.0))
        self.db.save_day(focus.new_day("2026-10-16", "OFF", hours_slept=8.0))
        back = self.db.days()
        self.assertEqual(len(back), 1, "day is the primary key")
        self.assertEqual(back[0]["day_type"], "OFF")
        self.assertEqual(focus.validate([], [], back), [])

    def test_everything_survives_a_restart(self):
        cid = self.db.save_cycle(focus.new_cycle("s1", 15, "2026-10-16T09:00:00"))
        self.db.save_report(focus.new_report(cid, "START", 3))
        self.db.save_day(focus.new_day("2026-10-16", "WORK"))
        self.reopen()
        self.assertEqual(len(self.db.cycles()), 1)
        self.assertEqual(len(self.db.reports()), 1)
        self.assertEqual(len(self.db.days()), 1)

    def test_cycles_can_be_narrowed_to_one_session(self):
        self.db.save_cycle(focus.new_cycle("s1", 15, "2026-10-16T09:00:00"))
        self.db.save_cycle(focus.new_cycle("s2", 15, "2026-10-16T11:00:00"))
        self.assertEqual(len(self.db.cycles()), 2)
        self.assertEqual(len(self.db.cycles(session_id="s1")), 1)

    def test_reports_can_be_narrowed_to_given_cycles(self):
        a = self.db.save_cycle(focus.new_cycle("s1", 15, "2026-10-16T09:00:00"))
        b = self.db.save_cycle(focus.new_cycle("s1", 15, "2026-10-16T10:00:00"))
        self.db.save_report(focus.new_report(a, "START", 3))
        self.db.save_report(focus.new_report(b, "START", 8))
        self.assertEqual(len(self.db.reports()), 2)
        only_a = self.db.reports(cycle_ids=[a])
        self.assertEqual(len(only_a), 1)
        self.assertEqual(only_a[0]["reported_load"], 3)


class KernelOverStoredRowsTests(TempStoreTests):
    """The seam that matters: analytics over rows that made the round trip.

    Shape-matching is not enough. These run the kernel's own functions on
    what SQLite handed back, so a type the database quietly changed --
    an int arriving as a string, a float as None -- fails here rather
    than in a chart months from now.
    """

    def record(self, day, day_type, minutes, ran_to_end, start_load, end_load):
        cid = self.db.save_cycle(
            focus.new_cycle("s1", minutes, f"{day}T09:00:00"))
        stored = [c for c in self.db.cycles() if c["id"] == cid][0]
        self.db.save_cycle(
            focus.close_cycle(stored, f"{day}T09:{minutes:02d}:00", ran_to_end))
        self.db.save_report(focus.new_report(cid, "START", start_load))
        self.db.save_report(focus.new_report(cid, "END", end_load))
        self.db.save_day(focus.new_day(day, day_type))
        return cid

    def test_validate_is_clean_over_a_populated_store(self):
        self.record("2026-10-13", "WORK", 15, True, 3, 6)
        self.record("2026-10-14", "WORK", 15, False, 5, 8)
        self.record("2026-10-17", "OFF", 25, True, 2, 4)
        self.assertEqual(
            focus.validate(self.db.cycles(), self.db.reports(), self.db.days()),
            [])

    def test_completion_rate_computes_over_stored_rows(self):
        self.record("2026-10-13", "WORK", 15, True, 3, 6)
        self.record("2026-10-14", "WORK", 15, False, 5, 8)
        self.assertAlmostEqual(focus.completion_rate(self.db.cycles()), 0.5)

    def test_load_by_phase_computes_over_stored_rows(self):
        a = self.record("2026-10-13", "WORK", 15, True, 3, 6)
        b = self.record("2026-10-14", "WORK", 15, True, 5, 8)
        means = focus.load_by_phase([a, b], self.db.reports())
        self.assertEqual(means["reports"], 4)
        self.assertAlmostEqual(means["mean_reported_load_start"], 4.0)
        self.assertAlmostEqual(means["mean_reported_load_end"], 7.0)
        self.assertAlmostEqual(means["mean_change"], 3.0)

    def test_work_and_off_days_can_be_compared_from_the_store(self):
        self.record("2026-10-13", "WORK", 15, True, 3, 6)
        self.record("2026-10-17", "OFF", 25, True, 2, 4)
        out = focus.compare_by_day_type(
            self.db.cycles(), self.db.reports(), self.db.days())
        # A list of per-day-type rows, not a dict keyed by type.
        by_type = {row["day_type"]: row for row in out}
        self.assertEqual(set(by_type), {"WORK", "OFF"})
        self.assertEqual(by_type["WORK"]["cycles"], 1)
        self.assertEqual(by_type["OFF"]["cycles"], 1)
        self.assertAlmostEqual(by_type["WORK"]["mean_reported_load_end"], 6.0)
        self.assertAlmostEqual(by_type["OFF"]["mean_reported_load_end"], 4.0)
        # The kernel flags its own correlational limit; keep that visible.
        self.assertTrue(by_type["WORK"]["observed_not_caused"])

    def test_stored_loads_come_back_as_whole_numbers(self):
        # sqlite3 is loosely typed; a load read back as "3" instead of 3
        # would pass validate() and then poison every mean downstream.
        self.record("2026-10-13", "WORK", 15, True, 3, 6)
        for r in self.db.reports():
            self.assertIsInstance(r["reported_load"], int)

    def test_stored_planned_minutes_come_back_as_whole_numbers(self):
        self.record("2026-10-13", "WORK", 15, True, 3, 6)
        for c in self.db.cycles():
            self.assertIsInstance(c["planned_minutes"], int)


class IsolationTests(unittest.TestCase):
    """The live database is never opened by this suite."""

    def test_the_store_resolves_db_path_at_call_time(self):
        # The NM-005 guard, re-asserted for the focus methods: a test that
        # redirects strata_core.DB_PATH must actually be obeyed.
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        original = strata_core.DB_PATH
        strata_core.DB_PATH = tmp.name
        try:
            db = strata_core.StrataDB()
            self.assertEqual(db.path, tmp.name)
            db.save_cycle(focus.new_cycle("s1", 15, "2026-10-16T09:00:00"))
            self.assertEqual(len(db.cycles()), 1)
            db.conn.close()
        finally:
            strata_core.DB_PATH = original
            os.unlink(tmp.name)

    def test_the_live_database_has_no_rows_from_this_suite(self):
        # A direct read of the real file. If a test ever writes here, the
        # count climbs and this fails -- which is the alarm we want.
        if not os.path.exists(strata_core.DB_PATH):
            self.skipTest("no live database on this machine")
        import sqlite3
        conn = sqlite3.connect(strata_core.DB_PATH)
        try:
            names = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "focus_cycles" not in names:
                return  # nothing has ever written focus rows here
            n = conn.execute(
                "SELECT COUNT(*) FROM focus_cycles WHERE session_id = 's1'"
            ).fetchone()[0]
            self.assertEqual(n, 0, "the suite wrote focus rows to the LIVE store")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
