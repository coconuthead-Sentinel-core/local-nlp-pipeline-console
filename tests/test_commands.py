"""Tests for the slash-command grammar.

Written before the web shell gained slash commands, and before the Tk
shell was retired. The order matters: the Tk console could do this and
the web shell could not, so the behaviour was pinned here first and the
console was only deleted once these passed against the web shell.
"""

import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from strata_core import ALL_GLYPHS
from strata_tools import commands


class ParseTests(unittest.TestCase):
    def test_ordinary_text_is_not_a_command(self):
        """None, not a dict -- the caller must be able to tell an
        ordinary message from a command it does not recognise."""
        for text in ("hello", "what is 2/3 of six", "  spaced  ", ""):
            with self.subTest(text=text):
                self.assertIsNone(commands.parse(text))

    def test_none_does_not_raise(self):
        self.assertIsNone(commands.parse(None))

    def test_every_documented_command_parses(self):
        for name in commands.COMMANDS:
            with self.subTest(name=name):
                got = commands.parse("/" + name)
                self.assertTrue(got["known"])
                self.assertEqual(got["name"], name)

    def test_casing_and_padding_do_not_matter(self):
        got = commands.parse("   /STATUS   ")
        self.assertTrue(got["known"])
        self.assertEqual(got["name"], "status")

    def test_the_mode_argument_survives(self):
        got = commands.parse("/mode yellow")
        self.assertEqual(got["name"], "mode")
        self.assertEqual(got["argument"], "yellow")

    def test_zone_is_still_accepted_for_mode(self):
        """Older spelling. Dropping it breaks muscle memory for no gain."""
        got = commands.parse("/zone red")
        self.assertEqual(got["name"], "mode")
        self.assertEqual(got["argument"], "red")

    def test_new_is_still_accepted_for_clear(self):
        self.assertEqual(commands.parse("/new")["name"], "clear")

    def test_every_alias_points_at_a_real_command(self):
        """An alias for a command that no longer exists is a dead end."""
        for alias, target in commands.ALIASES.items():
            with self.subTest(alias=alias):
                self.assertIn(target, commands.COMMANDS)

    def test_an_unknown_command_is_flagged_not_swallowed(self):
        got = commands.parse("/frobnicate")
        self.assertIsNotNone(got)
        self.assertFalse(got["known"])

    def test_a_bare_slash_is_an_unknown_command(self):
        """Not an ordinary message -- it must not reach the model."""
        got = commands.parse("/")
        self.assertIsNotNone(got)
        self.assertFalse(got["known"])

    def test_the_unknown_message_points_somewhere_useful(self):
        msg = commands.unknown_message("/frobnicate")
        self.assertIn("/frobnicate", msg)
        self.assertIn("/help", msg)


class LexiconTests(unittest.TestCase):
    def test_every_token_is_listed_by_its_code(self):
        text = commands.lexicon_text(ALL_GLYPHS)
        for t in ALL_GLYPHS:
            with self.subTest(token=t["code"]):
                self.assertIn(t["code"], text)
                self.assertIn(t["name"], text)
                self.assertIn(t["function"], text)

    def test_the_lexicon_prints_no_pictures(self):
        """The emoji vocabulary was removed on 2026-10-17.

        One picture had come to mean three different things across three
        artefacts (NM-009), which is the ambiguity a four-letter code
        cannot have. If an emoji ever reappears in the lexicon, this
        fails -- the vocabulary is codes now, and a picture offered
        beside a code invites the same drift back in.
        """
        text = commands.lexicon_text(ALL_GLYPHS)
        offenders = [c for c in text if ord(c) > 0x2500]
        self.assertEqual(offenders, [], f"pictures in the lexicon: {offenders}")

    def test_an_empty_lexicon_says_so_rather_than_rendering_blank(self):
        self.assertIn("No tokens", commands.lexicon_text([]))

    def test_none_does_not_raise(self):
        self.assertIn("No tokens", commands.lexicon_text(None))


class HelpTests(unittest.TestCase):
    def test_every_command_appears_in_help(self):
        """Help is generated from the table, so a new command cannot
        ship undocumented."""
        text = commands.help_text()
        for name in commands.COMMANDS:
            with self.subTest(name=name):
                self.assertIn("/" + name, text)

    def test_every_alias_appears_in_help(self):
        text = commands.help_text()
        for alias in commands.ALIASES:
            with self.subTest(alias=alias):
                self.assertIn("/" + alias, text)


if __name__ == "__main__":
    unittest.main()
