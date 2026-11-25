"""The window-fit kernel, and the invariant FB-001 is named after.

The old Tk-era test proved the fit across 110 screen sizes x 5 scaling
factors and asserted that the shape which caused FB-001 fails. This one
does the same job for the WebView2 shell, and adds the case actually
measured on the owner's screen on 2026-11-24.
"""

import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from strata_tools import window_fit as wf

#: The owner's laptop, measured. Display 1097x617; the work area excludes
#: the taskbar, leaving 1097x529 starting 40px down.
OWNER_WORK = (0, 40, 1097, 529)

#: A spread of real work areas: small laptops, the owner's machine,
#: 720p/1080p/1440p panels, a tall portrait monitor, and some deliberately
#: absurd ones. Every combination is swept against every desired size.
WORK_AREAS = [
    (0, 0, 640, 480), (0, 0, 800, 600), (0, 40, 1024, 728),
    OWNER_WORK, (0, 40, 1097, 617), (0, 0, 1280, 720),
    (0, 48, 1366, 720), (0, 0, 1440, 900), (0, 40, 1600, 860),
    (0, 0, 1920, 1040), (0, 0, 2560, 1400), (0, 0, 1080, 1920),
    (0, 0, 320, 240), (0, 0, 200, 120), (0, 0, 1, 1),
    (-1920, 0, 1920, 1040), (100, 100, 900, 500),
]

#: Sizes a shell might ask for, including the one that shipped.
DESIRED = [
    (wf.DESIRED_W, wf.DESIRED_H), (1000, 680), (1750, 1225),
    (640, 460), (1, 1), (4000, 3000), (900, 500), (1097, 529),
]


class TheInvariant(unittest.TestCase):
    """A planned window is inside the work area. Swept, not asserted once."""

    def test_every_plan_lands_inside_the_work_area(self):
        checked = 0
        for work in WORK_AREAS:
            wx, wy, ww, wh = work
            for dw, dh in DESIRED:
                for margin in (0, 8, wf.MARGIN, 200):
                    x, y, w, h = wf.plan(dw, dh, work, margin)
                    where = (f"work={work} desired=({dw},{dh}) "
                             f"margin={margin} -> ({x},{y},{w},{h})")
                    self.assertGreaterEqual(x, wx, where)
                    self.assertGreaterEqual(y, wy, where)
                    self.assertLessEqual(x + w, wx + ww, where)
                    self.assertLessEqual(y + h, wy + wh, where)
                    self.assertGreater(w, 0, where)
                    self.assertGreater(h, 0, where)
                    checked += 1
        # Guard the guard: a sweep that stopped sweeping would pass.
        self.assertGreater(checked, 400, "the sweep collapsed")

    def test_overflow_is_zero_on_every_edge_for_a_planned_window(self):
        for work in WORK_AREAS:
            for dw, dh in DESIRED:
                rect = wf.plan(dw, dh, work)
                over = wf.overflow(rect, work)
                self.assertEqual(
                    sum(over.values()), 0,
                    f"work={work} desired=({dw},{dh}) over={over}")


class TheShapesThatFailed(unittest.TestCase):
    """The regressions, named and asserted to be refused."""

    def test_the_shipped_1000x680_is_refused_on_the_owners_screen(self):
        # What strata_web.py asked WebView2 for until 2026-11-24.
        x, y, w, h = wf.plan(1000, 680, OWNER_WORK)
        self.assertLess(h, 680, "the height that ran off the bottom survived")
        self.assertLessEqual(y + h, OWNER_WORK[1] + OWNER_WORK[3])

    def test_the_measured_window_is_reported_as_escaping(self):
        # Measured on the owner's screen: (50, 90) 1000x633 against a work
        # area ending at 569. This is the reading that proves the defect,
        # and overflow() must call it what it is.
        over = wf.overflow((50, 90, 1000, 633), OWNER_WORK)
        self.assertEqual(over["bottom"], 154)
        self.assertEqual(over["left"], 0)
        self.assertEqual(over["right"], 0)
        self.assertIn("escapes", wf.describe((50, 90, 1000, 633), OWNER_WORK))

    def test_the_tk_era_shape_still_fails(self):
        # FB-001's own number: 1750x1225 physical on 1097x617.
        x, y, w, h = wf.plan(1750, 1225, (0, 0, 1097, 617))
        self.assertLessEqual(w, 1097)
        self.assertLessEqual(h, 617)
        self.assertNotEqual((w, h), (1750, 1225))


class TheOrderOfYielding(unittest.TestCase):
    """Margin yields to the floor; the floor yields to the screen."""

    def test_the_margin_is_honoured_when_there_is_room(self):
        w, h = wf.fit(5000, 5000, 1920, 1040, margin=24)
        self.assertEqual((w, h), (1920 - 48, 1040 - 48))

    def test_the_margin_yields_before_the_floor_does(self):
        # 700 wide: inset would be 652 which clears MIN_W, so margin holds.
        self.assertEqual(wf._axis(700, 24, wf.MIN_W), 652)
        # 660 wide: inset 612 is under MIN_W, so the margin is dropped.
        self.assertEqual(wf._axis(660, 24, wf.MIN_W), wf.MIN_W)

    def test_the_floor_yields_to_a_screen_smaller_than_it(self):
        # The rule the module docstring argues for: a small usable window
        # beats a minimum honoured off the edge of the display.
        self.assertEqual(wf._axis(400, 24, wf.MIN_W), 400)
        w, h = wf.fit(1000, 680, 400, 300)
        self.assertEqual((w, h), (400, 300))

    def test_a_one_pixel_work_area_still_yields_a_real_window(self):
        x, y, w, h = wf.plan(1000, 680, (0, 0, 1, 1))
        self.assertEqual((w, h), (1, 1))


class OriginTests(unittest.TestCase):
    def test_a_window_is_centred_when_it_is_smaller(self):
        self.assertEqual(wf.origin(100, 100, 0, 0, 500, 300), (200, 100))

    def test_the_work_area_offset_is_respected(self):
        # The owner's work area starts 40px down; the title bar must not
        # be planned above it.
        x, y = wf.origin(1000, 400, 0, 40, 1097, 529)
        self.assertGreaterEqual(y, 40)

    def test_a_negative_work_origin_is_carried_through(self):
        # A monitor left of the primary one has negative coordinates.
        x, y = wf.origin(800, 400, -1920, 0, 1920, 1040)
        self.assertLess(x, 0)
        self.assertGreaterEqual(x, -1920)

    def test_an_oversized_window_is_pinned_to_the_origin(self):
        self.assertEqual(wf.origin(5000, 5000, 10, 20, 500, 300), (10, 20))


class DescribeTests(unittest.TestCase):
    def test_a_fitting_window_says_so_with_numbers(self):
        line = wf.describe((24, 64, 1000, 481), OWNER_WORK)
        self.assertIn("fits", line)
        self.assertIn("1000x481", line)

    def test_an_escaping_window_names_the_edge_and_the_amount(self):
        line = wf.describe((0, 40, 1097, 700), OWNER_WORK)
        self.assertIn("bottom by 171px", line)


if __name__ == "__main__":
    unittest.main()
