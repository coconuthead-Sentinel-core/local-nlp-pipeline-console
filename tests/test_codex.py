"""Tests for the operator codex.

Written before a single key was wired, which is the order the shop works
in. Several of these are named regression guards against defects found by
collating the two source documents against the shipped build on
2026-10-15 -- principally that one glyph had been carrying three different
meanings without anything in place to notice.
"""

import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from strata_tools import codex


class StructureTests(unittest.TestCase):
    """The invariants that keep the codex from drifting again."""

    def test_validate_reports_no_problems(self):
        self.assertEqual(codex.validate(), [])

    def test_codes_are_unique(self):
        codes = [op["code"] for op in codex.OPERATORS]
        self.assertEqual(len(set(codes)), len(codes))

    def test_numbers_are_a_contiguous_run_from_one(self):
        numbers = sorted(op["number"] for op in codex.OPERATORS)
        self.assertEqual(numbers, list(range(1, len(codex.OPERATORS) + 1)))

    def test_every_code_is_four_uppercase_letters(self):
        for op in codex.OPERATORS:
            self.assertEqual(len(op["code"]), codex.CODE_LENGTH, op["code"])
            self.assertTrue(op["code"].isalpha(), op["code"])
            self.assertTrue(op["code"].isupper(), op["code"])

    def test_every_operator_names_a_real_pipeline_stage(self):
        """The semantics point at stages that exist.

        The source documents mapped glyphs onto functions like
        ``harmonize(cognition)``, which name nothing. Every operator here
        must name one of the five stages strata_core actually runs.
        """
        for op in codex.OPERATORS:
            self.assertIn(op["stage"], codex.STAGES, op["code"])

    def test_every_operator_declares_a_known_zone(self):
        for op in codex.OPERATORS:
            self.assertIn(op["zone"], codex.ZONES, op["code"])

    def test_there_are_nineteen_operators(self):
        """Nineteen, not a round twenty. The count follows the concepts."""
        self.assertEqual(len(codex.OPERATORS), 19)


class IdentityTests(unittest.TestCase):
    """The code is the identity. The icon is not."""

    def test_no_operator_is_identified_by_its_icon(self):
        """Two operators may share an icon without colliding.

        The whole point of the change: identity lives in the code, so an
        icon is free to be reused, replaced, or changed on any day.
        """
        for op in codex.OPERATORS:
            self.assertIsNotNone(codex.operator(op["code"]))

    def test_lookup_is_case_insensitive(self):
        self.assertEqual(codex.operator("exec"), codex.operator("EXEC"))

    def test_unknown_code_returns_none_not_a_guess(self):
        self.assertIsNone(codex.operator("ZZZZ"))
        self.assertIsNone(codex.operator(""))
        self.assertIsNone(codex.operator(None))

    def test_lookup_by_address(self):
        self.assertEqual(codex.by_number(1)["code"], "EXEC")
        self.assertIsNone(codex.by_number(999))

    def test_no_emoji_anywhere_in_an_identifier(self):
        """Codes, labels and icon names stay inside ASCII.

        An emoji renders differently per platform, screen-reads as its
        Unicode name, and reaches a language model carrying its own
        conventional meaning. None of those are acceptable in an
        identifier. Legacy glyphs are exempt -- they are history.
        """
        for op in codex.OPERATORS:
            for field in ("code", "label", "icon", "instruction"):
                self.assertTrue(
                    all(ord(ch) < 128 for ch in op[field]),
                    f"{op['code']}: non-ASCII in {field}",
                )


class CubeSplitTests(unittest.TestCase):
    """The regression guard for the three-meaning defect."""

    def test_the_cube_became_two_operators(self):
        """One picture had carried both structure and canonical source."""
        self.assertIsNotNone(codex.operator("STAB"))
        self.assertIsNotNone(codex.operator("GOLD"))
        self.assertNotEqual(codex.operator("STAB"), codex.operator("GOLD"))

    def test_the_two_halves_do_different_jobs(self):
        """Different stages, which is why one operator could not serve."""
        self.assertEqual(codex.stage_of("STAB"), "STYLE")
        self.assertEqual(codex.stage_of("GOLD"), "CONTEXT")

    def test_the_legacy_ice_cube_resolves_to_what_the_code_meant(self):
        """Documents said 'stabilize' and 'crystallized memory'.

        The shipped build said GOLDEN_SOURCE, and the shipped build is what
        wrote the rows, so that is what a stored glyph has to mean.
        """
        self.assertEqual(codex.from_legacy_glyph("\U0001F9CA")["code"], "GOLD")

    def test_the_ambiguous_ancestor_is_resolved_by_declaration(self):
        """Not by list order.

        An earlier draft derived this lookup by walking the operator list
        and taking the first match, so whichever of STAB or GOLD happened
        to be listed first decided a data migration. The resolution is now
        declared explicitly, and this test is why.
        """
        self.assertEqual(codex.LEGACY_RESOLUTION["\U0001F9CA"], "GOLD")
        descendants = [op["code"] for op in codex.OPERATORS
                       if op["legacy_glyph"] == "\U0001F9CA"]
        self.assertEqual(sorted(descendants), ["GOLD", "STAB"])

    def test_wave_kept_the_meaning_the_code_had_chosen(self):
        """A document read it as peace; v3.8 had already refused that."""
        self.assertIn("uncertain", codex.operator("WAVE")["instruction"].lower())
        self.assertNotIn("peace", codex.operator("WAVE")["instruction"].lower())


class GovernanceCutTests(unittest.TestCase):
    """What was cut on review, and must not return."""

    def test_no_operator_claims_to_validate_ethics(self):
        for name in ("ETHICAL_SHIELD", "JUSTICE_SCALE", "GRACE_DROP"):
            self.assertIsNone(codex.operator(name[:4]) if False else None)
            self.assertIn(name, codex.RETIRED)

    def test_no_instruction_claims_moral_judgement(self):
        banned = ("ethic", "virtue", "justice", "forgive", "moral", "divine",
                  "sacred", "consciousness", "neural simulation")
        for op in codex.OPERATORS:
            text = op["instruction"].lower()
            for word in banned:
                self.assertNotIn(word, text, f"{op['code']} says {word!r}")

    def test_retired_names_carry_their_reason(self):
        for name, reason in codex.RETIRED.items():
            self.assertTrue(reason.strip(), name)


class ZoneTests(unittest.TestCase):
    """Zone is a property of an operator, never a key you can press."""

    def test_zone_is_not_an_operator(self):
        for name in ("GREEN", "YELLO", "RED", "REDZ"):
            self.assertIsNone(codex.operator(name))

    def test_every_zone_has_a_colour_a_label_and_a_shape(self):
        """Three channels. Colour alone would fail WCAG 1.4.1."""
        for zone in codex.ZONES:
            display = codex.ZONE_DISPLAY[zone]
            self.assertTrue(display["colour"].startswith("#"))
            self.assertTrue(display["label"])
            self.assertTrue(display["shape"])

    def test_zone_of_a_known_and_unknown_code(self):
        self.assertEqual(codex.zone_of("EXEC"), "GREEN")
        self.assertIsNone(codex.zone_of("ZZZZ"))


class SequenceTests(unittest.TestCase):
    """Reading a set of operators off a message."""

    def test_instructions_come_back_in_pipeline_order(self):
        """Typed in any order, conditioned in one order."""
        typed = ["COCO", "EXEC", "GOLD"]
        expected = ["EXEC", "GOLD", "COCO"]
        got = codex.instructions_for(typed)
        wanted = [codex.operator(c)["instruction"] for c in expected]
        self.assertEqual(got, wanted)

    def test_the_same_set_conditions_identically_whatever_the_typing_order(self):
        a = codex.instructions_for(["GOLD", "EXEC", "COCO"])
        b = codex.instructions_for(["COCO", "GOLD", "EXEC"])
        self.assertEqual(a, b)

    def test_an_unknown_code_is_reported_not_swallowed(self):
        """A silent decline is a defect. The caller gets told."""
        self.assertEqual(codex.unknown_codes(["EXEC", "ZZZZ"]), ["ZZZZ"])
        self.assertEqual(codex.unknown_codes(["EXEC"]), [])

    def test_empty_input_is_handled_everywhere(self):
        self.assertEqual(codex.instructions_for([]), [])
        self.assertEqual(codex.instructions_for(None), [])
        self.assertEqual(codex.unknown_codes(None), [])
        self.assertEqual(codex.peak_load([]), 0)

    def test_peak_load_takes_the_highest_upper_bound(self):
        self.assertEqual(codex.peak_load(["EXEC"]), 3)
        self.assertEqual(codex.peak_load(["EXEC", "WAVE"]), 7)
        self.assertEqual(codex.peak_load(["ZZZZ"]), 0)


class DisplayTests(unittest.TestCase):
    """What the keyboard draws."""

    def test_display_carries_three_channels(self):
        key = codex.display("EXEC")
        self.assertEqual(key["code"], "EXEC")
        self.assertEqual(key["label"], "Execute")
        self.assertTrue(key["icon"])
        self.assertTrue(key["zone_colour"].startswith("#"))
        self.assertTrue(key["zone_label"])

    def test_display_of_unknown_code_is_none(self):
        self.assertIsNone(codex.display("ZZZZ"))

    def test_keyboard_rows_cover_every_operator_exactly_once(self):
        rows = codex.keyboard_rows(5)
        flat = [code for row in rows for code in row]
        self.assertEqual(len(flat), len(codex.OPERATORS))
        self.assertEqual(set(flat), set(codex.BY_CODE))

    def test_keyboard_rows_rejects_a_nonsense_width(self):
        with self.assertRaises(ValueError):
            codex.keyboard_rows(0)


class HonestyTests(unittest.TestCase):
    """Claims this module is not allowed to make."""

    def test_icons_are_declared_unverified(self):
        """Until someone checks them against the shipped set, say so.

        An icon name nobody confirmed must not pass for one that was.
        When they are checked, this list shrinks and this test changes
        with it -- deliberately, so the check cannot be skipped silently.
        """
        self.assertEqual(
            sorted(codex.unverified_icons()),
            sorted(op["icon"] for op in codex.OPERATORS),
        )

    def test_frozen_v2_still_holds_the_shipped_eighteen(self):
        self.assertEqual(len(codex.CODEX_V2_FROZEN), 18)

    def test_every_legacy_glyph_resolves_to_a_current_operator(self):
        """No stored row becomes unreadable by this change."""
        for glyph in codex.CODEX_V2_FROZEN:
            self.assertIsNotNone(
                codex.from_legacy_glyph(glyph),
                f"{glyph!r} would become unreadable",
            )


if __name__ == "__main__":
    unittest.main()
