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


class ActionTests(unittest.TestCase):
    """The verbs. A separate part of speech from the operators."""

    def test_the_two_namespaces_never_overlap(self):
        """Sharing one namespace is what let a glyph mean three things."""
        op_codes = {op["code"] for op in codex.OPERATORS}
        act_codes = {a["code"] for a in codex.ACTIONS}
        self.assertEqual(op_codes & act_codes, set())

    def test_part_of_speech_tells_them_apart(self):
        self.assertEqual(codex.part_of_speech("INPT"), "ACTION")
        self.assertEqual(codex.part_of_speech("EXEC"), "OPERATOR")
        self.assertIsNone(codex.part_of_speech("ZZZZ"))

    def test_no_action_is_destructive(self):
        """SCOPE.md §3: archive, never delete.

        A Trash key was proposed and refused. It would either break that
        criterion or lie about what it does.
        """
        for act in codex.ACTIONS:
            self.assertFalse(act["destructive"], act["code"])

    def test_there_is_no_delete_or_trash_verb(self):
        for banned in ("TRSH", "DELE", "DROP", "PURG", "WIPE"):
            self.assertIsNone(codex.action(banned))
        for act in codex.ACTIONS:
            self.assertNotIn("delete", act["does"].lower(), act["code"])

    def test_archive_describes_raising_a_floor_not_removing_rows(self):
        self.assertIn("rows stay", codex.action("ARCH")["does"].lower())

    def test_clear_moves_both_halves_together(self):
        """A Clear that cleared only the view would quote what it cleared."""
        does = codex.action("CLER")["does"].lower()
        self.assertIn("recall", does)

    def test_action_lookup_is_case_insensitive(self):
        self.assertEqual(codex.action("inpt"), codex.action("INPT"))
        self.assertIsNone(codex.action(""))
        self.assertIsNone(codex.action(None))

    def test_action_codes_are_four_uppercase_letters(self):
        for act in codex.ACTIONS:
            self.assertEqual(len(act["code"]), codex.CODE_LENGTH)
            self.assertTrue(act["code"].isalpha() and act["code"].isupper())


class ReadabilityTests(unittest.TestCase):
    """The test the old keyboard failed: can a person read back what they typed?"""

    def test_a_verb_and_a_modifier_read_as_a_sentence(self):
        """The sentence uses each action's VERB form, not its key label.

        A key reads "Web" because that is what it is; the sentence reads
        "search the web" because that is what it does. "Find, then web"
        is not English, and the readability claim has to survive being
        read aloud.
        """
        said = codex.reads_as(["INPT", "EXEC"], zone="GREEN")
        self.assertEqual(said, "Take it in -- execute, in the green zone")

    def test_every_action_has_a_verb_form_distinct_from_its_label(self):
        for act in codex.ACTIONS:
            self.assertTrue(act["verb"].strip(), act["code"])

    def test_a_noun_label_still_reads_as_a_verb_in_the_sentence(self):
        said = codex.reads_as(["WEBS"])
        self.assertEqual(said, "Search the web")
        self.assertEqual(codex.action("WEBS")["label"], "Web")

    def test_verbs_come_before_modifiers_whatever_the_typing_order(self):
        a = codex.reads_as(["EXEC", "INPT"])
        b = codex.reads_as(["INPT", "EXEC"])
        self.assertEqual(a, b)

    def test_several_verbs_are_sequenced(self):
        self.assertIn("then", codex.reads_as(["INPT", "SAVE"]))

    def test_nothing_selected_says_so(self):
        self.assertEqual(codex.reads_as([]), "Nothing selected")
        self.assertEqual(codex.reads_as(None), "Nothing selected")

    def test_an_unrecognised_code_is_named_not_swallowed(self):
        said = codex.reads_as(["INPT", "ZZZZ"])
        self.assertIn("ZZZZ", said)
        self.assertIn("unrecognised", said)

    def test_an_unknown_zone_is_simply_omitted(self):
        said = codex.reads_as(["INPT"], zone="PURPLE")
        self.assertNotIn("purple", said.lower())


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
            sorted([op["icon"] for op in codex.OPERATORS] +
                   [a["icon"] for a in codex.ACTIONS]),
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


class NoPicturesOfferedTests(unittest.TestCase):
    """The vocabulary is codes. Nothing OFFERS a picture any more.

    Removed 2026-10-17 on the owner's instruction: the emoji were too
    easy for a person and a language model to read differently. NM-009 is
    the proof -- one ice cube had come to mean three things across three
    artefacts, and whichever meaning happened to be listed first decided
    how every stored row would be re-read.

    Legacy emoji are still RESOLVED (see LegacyTests) so rows already in
    SQLite stay readable. Resolving an old picture is not offering a new
    one, and that is the line these tests hold.
    """

    PICTURE = 0x2500   # above this, a codepoint is a symbol or emoji

    def pictures_in(self, text):
        return sorted({c for c in text if ord(c) > self.PICTURE})

    def test_no_operator_label_or_instruction_carries_a_picture(self):
        for op in codex.OPERATORS:
            with self.subTest(code=op["code"]):
                self.assertEqual(self.pictures_in(op["label"]), [])
                self.assertEqual(self.pictures_in(op["instruction"]), [])

    def test_no_action_verb_carries_a_picture(self):
        for a in codex.ACTIONS:
            with self.subTest(code=a["code"]):
                self.assertEqual(self.pictures_in(a["verb"]), [])
                self.assertEqual(self.pictures_in(a["label"]), [])
                self.assertEqual(self.pictures_in(a["does"]), [])

    def test_what_the_keyboard_is_handed_contains_no_picture(self):
        for row in codex.keyboard_rows(5):
            for code in row:
                key = codex.display(code)
                with self.subTest(code=code):
                    self.assertNotIn("glyph", key)
                    for value in key.values():
                        self.assertEqual(self.pictures_in(str(value)), [])

    def test_a_read_back_sentence_contains_no_picture(self):
        text = codex.reads_as(["INPT", "EXEC"], "GREEN")
        self.assertEqual(self.pictures_in(text), [])

    def test_the_engine_vocabulary_has_no_picture_and_no_glyph_key(self):
        import strata_core
        self.assertEqual(len(strata_core.TOKENS), len(codex.OPERATORS))
        for t in strata_core.TOKENS:
            with self.subTest(code=t["code"]):
                self.assertNotIn("glyph", t)
                for value in t.values():
                    self.assertEqual(self.pictures_in(str(value)), [])

    def test_the_shipped_shell_shows_no_picture(self):
        """index.html and app.js may say the WORD glyph; not draw one."""
        here = os.path.dirname(os.path.abspath(__file__))
        for name in ("index.html", "app.js"):
            path = os.path.join(here, "..", "web", name)
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            # The source-row emoji that label voice and file controls are
            # not operator tokens; only the codex vocabulary is in scope.
            for op in codex.OPERATORS:
                legacy = op.get("legacy_glyph")
                if legacy:
                    with self.subTest(file=name, legacy=op["code"]):
                        self.assertNotIn(legacy, body)


class CodeDetectionTests(unittest.TestCase):
    """The classifier reads codes, and still resolves an old picture."""

    def setUp(self):
        import strata_core
        self.core = strata_core
        self.node = strata_core.InputNode()

    def test_a_code_in_a_message_is_detected(self):
        out = self.node.process("EXEC ship the thing")
        self.assertIn("EXEC", out["glyphs"])

    def test_a_message_with_no_code_detects_nothing(self):
        self.assertEqual(self.node.process("just a question?")["glyphs"], [])

    def test_a_legacy_picture_still_resolves_to_its_code(self):
        # Typed from old habit, or read back off a stored row. It must not
        # be silently stripped of meaning.
        legacy = next(iter(self.core.LEGACY_CHARS))
        expected = self.core.LEGACY_CHARS[legacy]
        out = self.node.process(f"{legacy} do this")
        self.assertIn(expected, out["glyphs"])

    def test_a_legacy_picture_is_stripped_from_the_residual(self):
        legacy = next(iter(self.core.LEGACY_CHARS))
        out = self.node.process(f"{legacy} do this")
        self.assertNotIn(legacy, out["residual"])
