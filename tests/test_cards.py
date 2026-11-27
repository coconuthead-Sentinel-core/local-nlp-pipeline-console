"""Tests for the note-card grid.

The feature lived only in the published browser page; this is the port,
and the port's first obligation is that a card written there still reads
here. So the address rule is tested against the browser build's own
pattern rather than an improved one.
"""

import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from strata_tools import cards


def card(cell, title="t", body="", zone="GREEN", load=None):
    return cards.new_card(cell, title, body, "2026-11-27T09:00:00",
                          zone=zone, load=load)


class AddressTests(unittest.TestCase):
    def test_a_plain_address_parses(self):
        self.assertEqual(cards.parse_cell("H5"), ("H", 5))
        self.assertEqual(cards.parse_cell("A1"), ("A", 1))
        self.assertEqual(cards.parse_cell("Z999"), ("Z", 999))

    def test_dictation_capitalisation_does_not_matter(self):
        # The owner dictates; a speech engine capitalises inconsistently.
        self.assertEqual(cards.parse_cell("h5"), ("H", 5))
        self.assertEqual(cards.parse_cell("  h5  "), ("H", 5))

    def test_what_is_not_an_address(self):
        for bad in ("", None, "H", "5", "H0", "AA1", "H1000", "H-1",
                    "box model", "H5x", "5H"):
            with self.subTest(text=repr(bad)):
                self.assertIsNone(cards.parse_cell(bad))

    def test_row_zero_is_refused(self):
        # The grid starts at 1. H0 reads like an address and is not one.
        self.assertIsNone(cards.parse_cell("H0"))

    def test_formatting_round_trips(self):
        self.assertEqual(cards.format_cell("h", 5), "H5")
        self.assertEqual(cards.parse_cell(cards.format_cell("Q", 42)),
                         ("Q", 42))

    def test_formatting_refuses_what_the_grid_cannot_hold(self):
        for col, row in (("AA", 1), ("1", 1), ("A", 0), ("A", 1000)):
            with self.subTest(column=col, row=row):
                with self.assertRaises(ValueError):
                    cards.format_cell(col, row)

    def test_is_cell_forks_the_search_box(self):
        self.assertTrue(cards.is_cell("H5"))
        self.assertFalse(cards.is_cell("box model"))


class CardTests(unittest.TestCase):
    def test_a_card_round_trips_its_fields(self):
        c = card("H5", "The box model", "padding, border, margin",
                 zone="YELLOW", load=6)
        self.assertEqual(c["cell"], "H5")
        self.assertEqual(c["title"], "The box model")
        self.assertEqual(c["zone"], "YELLOW")
        self.assertEqual(c["load"], 6)
        self.assertIsNone(c["updated"])

    def test_the_address_is_stored_canonically(self):
        self.assertEqual(card("h5")["cell"], "H5")

    def test_a_card_without_a_title_is_refused(self):
        # A card is found by address OR by name; one without a name is
        # findable only one way.
        for bad in ("", "   ", None):
            with self.subTest(title=repr(bad)):
                with self.assertRaises(ValueError):
                    card("H5", title=bad)

    def test_a_bad_zone_or_load_is_refused_at_the_door(self):
        with self.assertRaises(ValueError):
            card("H5", zone="BLUE")
        for bad in (0, 11, "6", True):
            with self.subTest(load=repr(bad)):
                with self.assertRaises(ValueError):
                    card("H5", load=bad)

    def test_an_empty_body_is_allowed(self):
        # A title and an address are enough to file a thought.
        self.assertEqual(card("H5", "just a title")["body"], "")


class LinkTests(unittest.TestCase):
    def test_a_link_round_trips(self):
        link = cards.new_link("h5", "a1", "depends on")
        self.assertEqual(link["src"], "H5")
        self.assertEqual(link["dst"], "A1")

    def test_a_card_cannot_link_to_itself(self):
        # A self-edge adds nothing to follow and makes any link-walking
        # traversal a potential loop.
        with self.assertRaises(ValueError):
            cards.new_link("H5", "h5", "relates to")

    def test_an_unknown_relation_is_refused(self):
        with self.assertRaises(ValueError):
            cards.new_link("H5", "A1", "vibes with")


class TraversalTests(unittest.TestCase):
    """The owner's two reading directions."""

    def setUp(self):
        self.grid = [card("A1"), card("B1"), card("A2"), card("B2")]

    def test_row_major_reads_across_then_down(self):
        order = [c["cell"] for c in cards.walk(self.grid, cards.ROW_MAJOR)]
        self.assertEqual(order, ["A1", "B1", "A2", "B2"])

    def test_column_major_reads_down_then_across(self):
        order = [c["cell"] for c in cards.walk(self.grid, cards.COLUMN_MAJOR)]
        self.assertEqual(order, ["A1", "A2", "B1", "B2"])

    def test_the_two_orders_really_differ(self):
        # If they ever agree on a non-trivial grid, one of them is wrong
        # and the feature is pointless.
        a = [c["cell"] for c in cards.walk(self.grid, cards.ROW_MAJOR)]
        b = [c["cell"] for c in cards.walk(self.grid, cards.COLUMN_MAJOR)]
        self.assertNotEqual(a, b)
        self.assertEqual(sorted(a), sorted(b))   # same cards, both ways

    def test_rows_sort_numerically_not_as_text(self):
        # "10" sorts before "9" as text. A grid that puts row 10 above
        # row 9 is wrong in a way that is easy to miss by eye.
        grid = [card("A10"), card("A9"), card("A2")]
        order = [c["cell"] for c in cards.walk(grid, cards.COLUMN_MAJOR)]
        self.assertEqual(order, ["A2", "A9", "A10"])

    def test_an_unknown_order_is_refused(self):
        with self.assertRaises(ValueError):
            cards.walk([], "DIAGONAL")

    def test_one_unreadable_address_does_not_break_the_walk(self):
        grid = [card("B1"), {"cell": "nonsense"}, card("A1")]
        order = [c.get("cell") for c in cards.walk(grid)]
        self.assertEqual(order[:2], ["A1", "B1"])
        self.assertEqual(order[-1], "nonsense")   # sorts last, not raises


class NeighbourTests(unittest.TestCase):
    def test_the_four_neighbours_are_found(self):
        grid = [card("B2"), card("B1"), card("B3"), card("A2"), card("C2")]
        n = cards.neighbours(grid, "B2")
        self.assertEqual(n["up"]["cell"], "B1")
        self.assertEqual(n["down"]["cell"], "B3")
        self.assertEqual(n["left"]["cell"], "A2")
        self.assertEqual(n["right"]["cell"], "C2")

    def test_an_empty_direction_reports_none_rather_than_being_absent(self):
        # The gaps are the useful part: a caller can say "nothing above".
        n = cards.neighbours([card("A1")], "A1")
        self.assertEqual(set(n), {"up", "down", "left", "right"})
        self.assertIsNone(n["up"])
        self.assertIsNone(n["left"])

    def test_the_edges_of_the_grid_do_not_wrap(self):
        n = cards.neighbours([card("A1"), card("Z1")], "A1")
        self.assertIsNone(n["left"])     # A has no column to its left
        self.assertIsNone(n["up"])       # row 1 has no row above


class NextFreeTests(unittest.TestCase):
    def test_an_empty_grid_starts_at_a1(self):
        self.assertEqual(cards.next_free([]), "A1")

    def test_row_major_fills_across_first(self):
        self.assertEqual(cards.next_free([card("A1")], cards.ROW_MAJOR), "B1")

    def test_column_major_fills_down_first(self):
        self.assertEqual(
            cards.next_free([card("A1")], cards.COLUMN_MAJOR), "A2")

    def test_a_gap_is_filled_before_the_end(self):
        grid = [card("A1"), card("C1")]
        self.assertEqual(cards.next_free(grid, cards.ROW_MAJOR), "B1")


class FindTests(unittest.TestCase):
    def setUp(self):
        self.grid = [
            card("H5", "The box model", "padding border margin"),
            card("A1", "Flexbox", "a box that flexes"),
            card("B2", "Grid areas", "named template areas"),
        ]

    def test_an_address_jumps_straight_to_one_card(self):
        hits = cards.find(self.grid, "h5")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["title"], "The box model")

    def test_words_search_title_and_body(self):
        self.assertEqual(len(cards.find(self.grid, "box")), 2)

    def test_word_order_does_not_matter(self):
        a = [c["cell"] for c in cards.find(self.grid, "box model")]
        b = [c["cell"] for c in cards.find(self.grid, "model box")]
        self.assertEqual(a, b)

    def test_more_matching_words_ranks_higher(self):
        hits = cards.find(self.grid, "box model")
        self.assertEqual(hits[0]["cell"], "H5")

    def test_an_address_with_no_card_finds_nothing_rather_than_guessing(self):
        self.assertEqual(cards.find(self.grid, "Q9"), [])

    def test_an_empty_query_finds_nothing(self):
        for q in ("", "   ", None, "!!!"):
            with self.subTest(query=repr(q)):
                self.assertEqual(cards.find(self.grid, q), [])


class DescribeTests(unittest.TestCase):
    def test_a_card_describes_itself_by_address_first(self):
        line = cards.describe(card("H5", "The box model", zone="YELLOW",
                                   load=6))
        self.assertTrue(line.startswith("H5"))
        self.assertIn("The box model", line)
        self.assertIn("yellow", line)
        self.assertIn("load 6", line)

    def test_a_sparse_card_still_describes_cleanly(self):
        line = cards.describe({"cell": "A1", "title": "x"})
        self.assertIn("A1", line)
        self.assertNotIn("load", line)


class ValidateTests(unittest.TestCase):
    def test_a_clean_grid_reports_nothing(self):
        grid = [card("A1"), card("B2")]
        links = [cards.new_link("A1", "B2", "relates to")]
        self.assertEqual(cards.validate(grid, links), [])

    def test_a_duplicate_address_is_reported(self):
        problems = cards.validate([card("A1"), card("A1")], [])
        self.assertTrue(any("duplicate" in p for p in problems))

    def test_a_link_to_nowhere_is_reported(self):
        problems = cards.validate(
            [card("A1")], [{"src": "A1", "dst": "Q9",
                            "relation": "relates to"}])
        self.assertTrue(any("names no card" in p for p in problems))

    def test_a_corrupt_row_is_reported_not_raised(self):
        problems = cards.validate([{"cell": "nonsense", "zone": "GREEN"}], [])
        self.assertTrue(any("not a valid cell" in p for p in problems))


class SchemaTests(unittest.TestCase):
    def test_the_schema_is_declared_here_and_only_here(self):
        # NM-009's lesson: a second copy of a definition drifts from the
        # first. The store executes this, it does not retype it.
        self.assertEqual(len(cards.SCHEMA), 2)
        for statement in cards.SCHEMA:
            self.assertIn("CREATE TABLE IF NOT EXISTS", statement)

    def test_the_address_is_unique_in_the_schema(self):
        # Two cards at H5 would make "go to H5" ambiguous, which defeats
        # the entire point of an address.
        self.assertIn("UNIQUE", cards.SCHEMA[0])


if __name__ == "__main__":
    unittest.main()


class StoreTests(unittest.TestCase):
    """The seam between the kernel and SQLite, on a throwaway database."""

    def setUp(self):
        import tempfile
        import strata_core
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.path = tmp.name
        self.db = strata_core.StrataDB(path=self.path)

    def tearDown(self):
        self.db.conn.close()
        os.unlink(self.path)

    def reopen(self):
        import strata_core
        self.db.conn.close()
        self.db = strata_core.StrataDB(path=self.path)
        return self.db

    def test_the_card_tables_are_created(self):
        names = {r[0] for r in self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        self.assertLessEqual({"cards", "card_links"}, names)

    def test_the_migration_is_additive(self):
        self.db.add_thread("2026-11-27", "a turn from before", "GREEN")
        self.reopen()
        self.assertEqual(len(self.db.recent_threads(10)), 1)

    def test_a_card_round_trips(self):
        self.db.save_card(card("H5", "The box model", "padding", load=6))
        back = self.db.cards()
        self.assertEqual(len(back), 1)
        self.assertEqual(back[0]["cell"], "H5")
        self.assertEqual(back[0]["title"], "The box model")
        self.assertEqual(back[0]["load"], 6)

    def test_everything_survives_a_restart(self):
        self.db.save_card(card("H5", "The box model"))
        self.db.save_card_link(cards.new_link("H5", "A1", "relates to"))
        self.reopen()
        self.assertEqual(len(self.db.cards()), 1)
        self.assertEqual(len(self.db.card_links()), 1)

    def test_saving_the_same_address_twice_updates_rather_than_duplicates(self):
        """The address IS the identity.

        Two cards at H5 would make "go to H5" ambiguous, which defeats
        the point of having addresses at all.
        """
        self.db.save_card(card("H5", "First try"))
        self.db.save_card(card("H5", "Better title", "with a body"))
        rows = self.db.cards()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Better title")
        self.assertEqual(rows[0]["body"], "with a body")

    def test_a_card_is_fetched_by_address_case_insensitively(self):
        self.db.save_card(card("H5", "The box model"))
        self.assertEqual(self.db.card_at("h5")["title"], "The box model")
        self.assertIsNone(self.db.card_at("Q9"))

    def test_there_is_no_delete_and_the_refusal_says_why(self):
        with self.assertRaises(NotImplementedError) as caught:
            self.db.delete_card("H5")
        self.assertIn("RED", str(caught.exception))

    def test_links_can_be_narrowed_to_one_card(self):
        for c in ("A1", "B2", "C3"):
            self.db.save_card(card(c))
        self.db.save_card_link(cards.new_link("A1", "B2", "relates to"))
        self.db.save_card_link(cards.new_link("B2", "C3", "depends on"))
        self.assertEqual(len(self.db.card_links()), 2)
        self.assertEqual(len(self.db.card_links("A1")), 1)
        self.assertEqual(len(self.db.card_links("B2")), 2)

    def test_the_kernel_reads_stored_rows_unchanged(self):
        """The seam that matters: analysis over rows that made the trip."""
        for c, t in (("A1", "Flexbox"), ("B1", "Grid"), ("A2", "Box model")):
            self.db.save_card(card(c, t))
        stored = self.db.cards()
        self.assertEqual(cards.validate(stored, self.db.card_links()), [])
        order = [c["cell"] for c in cards.walk(stored, cards.ROW_MAJOR)]
        self.assertEqual(order, ["A1", "B1", "A2"])
        order = [c["cell"] for c in cards.walk(stored, cards.COLUMN_MAJOR)]
        self.assertEqual(order, ["A1", "A2", "B1"])

    def test_find_works_over_stored_rows(self):
        self.db.save_card(card("H5", "The box model", "padding border"))
        self.db.save_card(card("A1", "Flexbox", "a box that flexes"))
        stored = self.db.cards()
        self.assertEqual(len(cards.find(stored, "box")), 2)
        self.assertEqual(cards.find(stored, "H5")[0]["title"], "The box model")

    def test_a_stored_load_comes_back_a_whole_number(self):
        # sqlite3 is loosely typed; "6" would pass validate and poison
        # every comparison downstream.
        self.db.save_card(card("H5", "t", load=6))
        self.assertIsInstance(self.db.cards()[0]["load"], int)

    def test_next_free_works_against_the_store(self):
        self.db.save_card(card("A1"))
        self.db.save_card(card("B1"))
        self.assertEqual(
            cards.next_free(self.db.cards(), cards.ROW_MAJOR), "C1")
