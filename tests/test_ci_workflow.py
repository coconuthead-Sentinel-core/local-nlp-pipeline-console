"""The CI workflow must only name files that exist.

Earned on 2026-10-17. ``strata_console.py`` was deleted on 2026-09-01
when the CustomTkinter shell was retired, but ``.github/workflows/ci.yml``
went on calling ``py_compile strata_console.py`` and
``import strata_console``. Both steps failed on every push for six weeks
-- through four feature tickets and three documentation commits -- while
``SCOPE.md`` section 3 listed "the full suite is green at every merge to
main, proven by CI" as a met acceptance criterion.

The local suite really was green the whole time. That is what made it
invisible: the work was sound, so nobody went looking, and the only thing
that would have spoken up was the gate itself.

The lesson is not "watch the Actions tab". A gate nobody reads is a gate
nobody reads, and a remote red light is exactly the kind of signal this
shop has learned not to depend on. So the check moves to where it cannot
be missed: the workflow's own file references are now asserted by the
suite that runs on this laptop before anything is pushed. If a file is
renamed or retired and the workflow is not updated with it, this fails
here, in seconds, instead of in a log nobody opens.
"""

import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "ci.yml")


def workflow_text():
    with open(WORKFLOW, encoding="utf-8") as fh:
        return fh.read()


def uncommented_lines(text):
    """Workflow lines with YAML comments stripped.

    The repair comments deliberately name ``strata_console.py`` to record
    why the step changed. A naive grep would read those as live references
    and fail forever, so history is excluded from the check and only
    executable lines are examined.
    """
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        out.append(line.split(" #", 1)[0] if " #" in line else line)
    return out


class WorkflowFileReferenceTests(unittest.TestCase):
    """Every path and module the workflow executes must be present."""

    def setUp(self):
        self.assertTrue(os.path.exists(WORKFLOW),
                        "the CI workflow itself is missing")
        self.lines = uncommented_lines(workflow_text())
        self.body = "\n".join(self.lines)

    def test_every_py_compile_target_exists(self):
        targets = re.findall(r"py_compile\s+([\w./\\-]+\.py)", self.body)
        self.assertTrue(targets, "no py_compile targets found -- did the step move?")
        for target in targets:
            with self.subTest(target=target):
                self.assertTrue(
                    os.path.exists(os.path.join(ROOT, target)),
                    f"ci.yml compiles {target}, which does not exist in the repo")

    def test_every_compileall_directory_exists(self):
        dirs = []
        for match in re.findall(r"compileall[^\n]*", self.body):
            for word in match.split():
                if word.startswith("-") or word in ("compileall", "python", "-m"):
                    continue
                dirs.append(word)
        self.assertTrue(dirs, "no compileall directories found")
        for d in dirs:
            with self.subTest(directory=d):
                self.assertTrue(
                    os.path.isdir(os.path.join(ROOT, d)),
                    f"ci.yml compiles directory {d}, which does not exist")

    def test_every_imported_module_exists(self):
        mods = re.findall(r"python -c \"import ([\w.]+)", self.body)
        self.assertTrue(mods, "no import checks found -- the degraded-mode gate is gone")
        for mod in mods:
            with self.subTest(module=mod):
                path = os.path.join(ROOT, mod.replace(".", os.sep))
                exists = os.path.exists(path + ".py") or os.path.isdir(path)
                self.assertTrue(
                    exists,
                    f"ci.yml imports {mod}, which does not exist in the repo")

    def test_the_retired_tk_shell_is_not_referenced_in_any_live_step(self):
        # The specific defect, nailed down by name so it cannot return.
        for line in self.lines:
            self.assertNotIn(
                "strata_console", line,
                "a live CI step still references the retired Tk shell")

    def test_the_degraded_check_proves_the_engine_needs_no_ui_library(self):
        # SCOPE.md section 4 rests on this claim; CI is where it is proven.
        self.assertIn("import strata_core", self.body,
                      "the degraded-mode check must import the engine")

    def test_pip_installs_are_limited_to_required_and_tooling(self):
        """Installing an optional package in CI would hide a degraded-path
        regression -- the comment in the workflow says so, and this holds
        it to that. coverage is tooling, not an application dependency."""
        allowed = {"pywebview", "coverage"}
        installed = set()
        for match in re.findall(r"pip install[^\n]*", self.body):
            for word in match.split():
                if word.startswith("-") or word in ("pip", "install", "python", "-m"):
                    continue
                installed.add(word.split("=")[0].split(">")[0].split("<")[0])
        self.assertTrue(installed, "no pip installs found at all")
        unexpected = installed - allowed
        self.assertEqual(
            unexpected, set(),
            f"CI installs {sorted(unexpected)}; optional packages here would "
            f"hide exactly the regression the degraded-mode check exists to catch")

    def test_the_suite_itself_is_still_run(self):
        self.assertIn("unittest discover", self.body,
                      "CI no longer runs the suite it claims to prove")

    def test_both_supported_pythons_are_still_in_the_matrix(self):
        # SCOPE.md section 3 names 3.11 and 3.13 specifically.
        self.assertRegex(self.body, r'"3\.11"')
        self.assertRegex(self.body, r'"3\.13"')


if __name__ == "__main__":
    unittest.main()


class NoRetiredToolkitTests(unittest.TestCase):
    """No shipped module drives the toolkit this project retired.

    Earned 2026-10-17. The CustomTkinter shell was retired on 2026-09-01
    and `layout.py`, `window_fit.py` and `selection.py` were deleted with
    it. `keyboard.py` -- 239 lines of Tk focus-ring handling, with 209
    lines of tests that passed -- was missed, and sat in `strata_tools/`
    for six weeks driving a toolkit nothing imports. Twenty green tests
    made it look alive.

    The sweep ends with a gate, per the shop's defect laws: a Tk-only
    module reappearing in the shipped tree now fails here. `turbo_console.py`
    is exempt and named -- it is a separate dormant tool that still
    declares customtkinter in requirements.txt, documented as such.
    """

    EXEMPT = {"turbo_console.py"}

    def shipped_python(self):
        out = []
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs
                       if d not in {".git", "__pycache__", ".claude", "tools"}]
            for f in files:
                if f.endswith(".py") and f not in self.EXEMPT:
                    out.append(os.path.join(base, f))
        return out

    def test_no_shipped_module_imports_the_retired_toolkit(self):
        for path in self.shipped_python():
            rel = os.path.relpath(path, ROOT)
            with self.subTest(module=rel):
                with open(path, encoding="utf-8") as fh:
                    body = fh.read()
                for line in body.splitlines():
                    stripped = line.strip()
                    if stripped.startswith(("import ", "from ")):
                        self.assertNotIn(
                            "customtkinter", stripped,
                            f"{rel} imports the retired toolkit")
                        self.assertNotIn(
                            "import tkinter", stripped,
                            f"{rel} imports tkinter")

    def test_the_retired_tk_kernels_are_gone(self):
        for name in ("layout.py", "window_fit.py", "selection.py",
                     "keyboard.py"):
            with self.subTest(module=name):
                self.assertFalse(
                    os.path.exists(os.path.join(ROOT, "strata_tools", name)),
                    f"strata_tools/{name} belongs to the retired Tk shell")
