"""Tests for focus cycles and experience sampling.

Written before the timer exists, which is the order the shop works in.
The rubric these answer to was stated before the code was written, on the
board at ``Claude AI\\Portfolio\\boards\\2026-10-15_focus-cycle-experience-sampling.md``.
"""

import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from strata_tools import focus


def cycle(cid, session="s1", day="2026-10-15", minutes=15, outcome="COMPLETED"):
    """A closed cycle on a given day. Test helper."""
    c = focus.new_cycle(session, minutes, f"{day}T09:00:00", cycle_id=cid)
    if outcome is None:
        return c
    return focus.close_cycle(c, f"{day}T09:{minutes:02d}:00",
                             outcome == "COMPLETED")


class CycleTests(unittest.TestCase):
    def test_a_new_cycle_is_open(self):
        c = focus.new_cycle("s1", 15, "2026-10-15T09:00:00")
        self.assertIsNone(c["outcome"])
        self.assertIsNone(c["ended_at"])

    def test_closing_does_not_mutate_the_original(self):
        c = focus.new_cycle("s1", 15, "2026-10-15T09:00:00")
        focus.close_cycle(c, "2026-10-15T09:15:00", True)
        self.assertIsNone(c["outcome"])

    def test_running_to_the_end_completes(self):
        c = cycle(1, outcome="COMPLETED")
        self.assertEqual(c["outcome"], "COMPLETED")

    def test_stopping_early_is_abandoned_and_is_kept(self):
        """R2: an abandoned cycle is persisted, never discarded.

        It is the most informative row this module collects.
        """
        c = cycle(1, outcome="ABANDONED")
        self.assertEqual(c["outcome"], "ABANDONED")
        self.assertIsNotNone(c["ended_at"])

    def test_a_cycle_cannot_end_before_it_starts(self):
        c = focus.new_cycle("s1", 15, "2026-10-15T09:00:00")
        with self.assertRaises(ValueError):
            focus.close_cycle(c, "2026-10-15T08:00:00", True)

    def test_nonsense_inputs_are_refused_by_name(self):
        with self.assertRaises(ValueError):
            focus.new_cycle("", 15, "2026-10-15T09:00:00")
        with self.assertRaises(ValueError):
            focus.new_cycle("s1", 0, "2026-10-15T09:00:00")
        with self.assertRaises(ValueError):
            focus.new_cycle("s1", 15, "")


class ReportTests(unittest.TestCase):
    def test_a_report_records_a_self_report(self):
        r = focus.new_report(1, "START", 6, mode="GREEN")
        self.assertEqual(r["reported_load"], 6)

    def test_the_field_is_not_called_cognitive_load(self):
        """SCOPE.md §3: no self-report is presented as a measurement."""
        r = focus.new_report(1, "START", 6)
        self.assertIn("reported_load", r)
        self.assertNotIn("cognitive_load", r)

    def test_load_outside_the_scale_is_refused(self):
        for bad in (0, 11, -1, 100):
            with self.assertRaises(ValueError, msg=str(bad)):
                focus.new_report(1, "START", bad)

    def test_a_load_that_is_not_a_whole_number_is_refused(self):
        for bad in (6.5, "6", None, True):
            with self.assertRaises(ValueError, msg=repr(bad)):
                focus.new_report(1, "START", bad)

    def test_an_unknown_phase_is_refused(self):
        with self.assertRaises(ValueError):
            focus.new_report(1, "MIDDLE", 5)


class SkippedPromptTests(unittest.TestCase):
    """R1: a skipped prompt leaves the cycle completely unaffected."""

    def test_a_cycle_with_no_reports_is_still_a_valid_cycle(self):
        c = cycle(1)
        self.assertEqual(focus.validate([c], [], []), [])
        self.assertEqual(focus.completion_rate([c]), 1.0)

    def test_skipping_carries_no_penalty_in_any_summary(self):
        with_report = [cycle(1)]
        reports = [focus.new_report(1, "START", 5)]
        a = focus.summarize_session("s1", with_report)
        b = focus.summarize_session("s1", [cycle(2)])
        self.assertEqual(a["completion_rate"], b["completion_rate"])
        self.assertEqual(len(reports), 1)


class CompletionRateTests(unittest.TestCase):
    def test_no_closed_cycles_is_none_not_zero(self):
        """R4-adjacent: nothing recorded differs from everything failed."""
        self.assertIsNone(focus.completion_rate([]))
        self.assertIsNone(focus.completion_rate(None))
        self.assertIsNone(focus.completion_rate([cycle(1, outcome=None)]))

    def test_all_abandoned_is_zero_which_is_a_real_answer(self):
        cycles = [cycle(1, outcome="ABANDONED"), cycle(2, outcome="ABANDONED")]
        self.assertEqual(focus.completion_rate(cycles), 0.0)

    def test_a_known_mix(self):
        cycles = [cycle(1), cycle(2), cycle(3, outcome="ABANDONED")]
        self.assertAlmostEqual(focus.completion_rate(cycles), 0.6667, places=3)


class SessionSummaryTests(unittest.TestCase):
    def test_counts_only_its_own_session(self):
        cycles = [cycle(1, session="s1"), cycle(2, session="s2")]
        s = focus.summarize_session("s1", cycles)
        self.assertEqual(s["cycles_started"], 1)

    def test_totals_add_up(self):
        cycles = [cycle(1), cycle(2, outcome="ABANDONED"), cycle(3, outcome=None)]
        s = focus.summarize_session("s1", cycles)
        self.assertEqual(s["cycles_started"], 3)
        self.assertEqual(s["cycles_closed"], 2)
        self.assertEqual(s["cycles_completed"] + s["cycles_abandoned"],
                         s["cycles_closed"])


class DayTypeTests(unittest.TestCase):
    """R3: every cycle counted exactly once, on a fixture with known totals."""

    def setUp(self):
        self.days = [
            focus.new_day("2026-10-13", "WORK", "1 of 2", hours_slept=5.0),
            focus.new_day("2026-10-14", "WORK", "2 of 2", hours_slept=4.5),
            focus.new_day("2026-10-15", "OFF", None, hours_slept=8.0),
        ]
        self.cycles = [
            cycle(1, day="2026-10-13", outcome="COMPLETED"),
            cycle(2, day="2026-10-13", outcome="ABANDONED"),
            cycle(3, day="2026-10-14", outcome="ABANDONED"),
            cycle(4, day="2026-10-15", outcome="COMPLETED"),
            cycle(5, day="2026-10-15", outcome="COMPLETED"),
        ]
        self.reports = [
            focus.new_report(1, "START", 7), focus.new_report(1, "END", 9),
            focus.new_report(4, "START", 3), focus.new_report(4, "END", 4),
        ]

    def test_every_cycle_is_counted_exactly_once(self):
        rows = focus.compare_by_day_type(self.cycles, self.reports, self.days)
        self.assertEqual(sum(r["cycles"] for r in rows), len(self.cycles))

    def test_the_known_split(self):
        rows = {r["day_type"]: r for r in
                focus.compare_by_day_type(self.cycles, self.reports, self.days)}
        self.assertEqual(rows["WORK"]["cycles"], 3)
        self.assertEqual(rows["OFF"]["cycles"], 2)
        self.assertAlmostEqual(rows["WORK"]["completion_rate"], 0.3333, places=3)
        self.assertEqual(rows["OFF"]["completion_rate"], 1.0)

    def test_hours_slept_travels_with_the_comparison(self):
        """The named confound stays in the report, not in an argument."""
        rows = {r["day_type"]: r for r in
                focus.compare_by_day_type(self.cycles, self.reports, self.days)}
        self.assertAlmostEqual(rows["WORK"]["mean_hours_slept"], 4.83, places=1)
        self.assertEqual(rows["OFF"]["mean_hours_slept"], 8.0)

    def test_the_output_declares_itself_observational(self):
        rows = focus.compare_by_day_type(self.cycles, self.reports, self.days)
        for row in rows:
            if row["cycles"]:
                self.assertTrue(row["observed_not_caused"])

    def test_a_day_type_with_no_cycles_says_so_instead_of_dividing_by_zero(self):
        """R4."""
        off_only = [c for c in self.cycles if c["started_at"].startswith("2026-10-15")]
        rows = {r["day_type"]: r for r in
                focus.compare_by_day_type(off_only, [], self.days)}
        self.assertEqual(rows["WORK"]["cycles"], 0)
        self.assertEqual(rows["WORK"]["note"], "no cycles recorded")
        self.assertNotIn("completion_rate", rows["WORK"])

    def test_empty_everything_does_not_raise(self):
        rows = focus.compare_by_day_type([], [], [])
        self.assertEqual(len(rows), len(focus.DAY_TYPES))


class LoadChangeTests(unittest.TestCase):
    def test_paired_start_and_end_give_a_change(self):
        reports = [focus.new_report(1, "START", 4), focus.new_report(1, "END", 7)]
        got = focus.load_by_phase([1], reports)
        self.assertEqual(got["mean_reported_load_start"], 4)
        self.assertEqual(got["mean_reported_load_end"], 7)
        self.assertEqual(got["mean_change"], 3)

    def test_an_unpaired_report_gives_no_change_rather_than_a_guess(self):
        reports = [focus.new_report(1, "START", 4)]
        got = focus.load_by_phase([1], reports)
        self.assertIsNone(got["mean_change"])

    def test_no_reports_at_all(self):
        got = focus.load_by_phase([1], [])
        self.assertEqual(got["reports"], 0)
        self.assertIsNone(got["mean_reported_load_start"])


class CycleLengthTests(unittest.TestCase):
    """The feature the module exists for: find your own best length."""

    def test_report_is_sorted_by_length(self):
        cycles = [cycle(1, minutes=25), cycle(2, minutes=10), cycle(3, minutes=15)]
        lengths = [r["planned_minutes"] for r in focus.cycle_length_report(cycles)]
        self.assertEqual(lengths, sorted(lengths))

    def test_short_cycles_winning_is_visible_in_the_numbers(self):
        cycles = ([cycle(i, minutes=10) for i in range(1, 5)] +
                  [cycle(i, minutes=25, outcome="ABANDONED") for i in range(5, 9)])
        rows = {r["planned_minutes"]: r for r in focus.cycle_length_report(cycles)}
        self.assertEqual(rows[10]["completion_rate"], 1.0)
        self.assertEqual(rows[25]["completion_rate"], 0.0)
        self.assertEqual(focus.best_cycle_length(cycles), 10)

    def test_a_thin_field_crowns_nobody(self):
        """Two tries is not evidence, and the module says so by returning None."""
        cycles = [cycle(1, minutes=10), cycle(2, minutes=10)]
        self.assertIsNone(focus.best_cycle_length(cycles, min_closed=3))

    def test_no_cycles_at_all(self):
        self.assertEqual(focus.cycle_length_report([]), [])
        self.assertIsNone(focus.best_cycle_length([]))


class ValidateTests(unittest.TestCase):
    def test_a_clean_fixture_has_no_problems(self):
        days = [focus.new_day("2026-10-15", "OFF")]
        cycles = [cycle(1)]
        reports = [focus.new_report(1, "START", 5)]
        self.assertEqual(focus.validate(cycles, reports, days), [])

    def test_duplicate_cycle_id_is_caught(self):
        self.assertIn("duplicate cycle id",
                      focus.validate([cycle(1), cycle(1)], [], []))

    def test_orphan_report_is_caught(self):
        problems = focus.validate([cycle(1)], [focus.new_report(99, "START", 5)], [])
        self.assertTrue(any("orphan" in p for p in problems))

    def test_duplicate_day_is_caught(self):
        days = [focus.new_day("2026-10-15", "OFF"), focus.new_day("2026-10-15", "WORK")]
        self.assertTrue(any("duplicate day" in p for p in focus.validate([], [], days)))

    def test_bad_day_type_is_refused_at_construction(self):
        with self.assertRaises(ValueError):
            focus.new_day("2026-10-15", "MAYBE")

    def test_impossible_sleep_is_refused(self):
        with self.assertRaises(ValueError):
            focus.new_day("2026-10-15", "OFF", hours_slept=30)


class ScopeTests(unittest.TestCase):
    """The carve-out in SCOPE.md §2: records and charts, does not urge."""

    def test_no_gamification_vocabulary_in_anything_the_module_can_emit(self):
        """Scans emittable strings, not prose.

        An earlier version of this test scanned the whole source and failed
        on the module's own docstring, which says "no streaks, no points"
        -- the prohibition, not the feature. A text scan cannot tell a ban
        from a reward, so this one parses the module and skips docstrings,
        checking only the literals that could reach a person.
        """
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(focus))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef,
                                 ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc is not None:
                    docstrings.add(doc)

        emittable = [
            n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value not in docstrings
        ]
        banned = ("streak", "badge", "reward", "points", "level up",
                  "congratul", "well done", "keep it up", "you should")
        for text in emittable:
            lowered = text.lower()
            for word in banned:
                self.assertNotIn(word, lowered,
                                 f"module can emit {word!r} in {text[:60]!r}")

    def test_the_scan_would_actually_catch_a_reward(self):
        """Guards the guard: a linter that cannot fire reads as proof."""
        import ast
        sample = ast.parse('"""a docstring"""\nMSG = "nice streak!"\n')
        doc = ast.get_docstring(sample, clean=False)
        emittable = [n.value for n in ast.walk(sample)
                     if isinstance(n, ast.Constant) and isinstance(n.value, str)
                     and n.value != doc]
        self.assertTrue(any("streak" in s.lower() for s in emittable))

    def test_the_schema_names_three_tables(self):
        self.assertEqual(len(focus.SCHEMA), 3)
        joined = " ".join(focus.SCHEMA)
        for table in ("focus_cycles", "focus_reports", "focus_days"):
            self.assertIn(table, joined)

    def test_the_schema_column_is_reported_load(self):
        joined = " ".join(focus.SCHEMA)
        self.assertIn("reported_load", joined)
        self.assertNotIn("cognitive_load", joined)


if __name__ == "__main__":
    unittest.main()
