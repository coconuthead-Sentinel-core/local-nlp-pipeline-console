# Changelog — Strata Console

All notable changes to this project. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Reconstructed 2026-09-01 from the commit history, then maintained
forward. Defect entries link to `docs/FORMER_BUGS.md`, which carries the
root cause and the guard.

---

## [Unreleased]

### Added — the note-card panel (2026-11-27)

The grid is now something the owner can see and write, not only ask
about. **🗂 Cards** opens a drawer beside the other source controls.

- **One box, two jobs.** `H5` jumps, words search, empty shows the whole
  grid. The panel never decides which — `cards.find()` does, and that is
  what the tests cover.
- **Reading: across / down** toggles the traversal. Verified end to end:
  the same three cards come back `A1, B1, A2` one way and `A1, A2, B1`
  the other.
- **The next free cell is offered** as the placeholder, and it follows
  the reading order — `C1` across, `A3` down. The question behind "is H5
  taken" is usually "where do I put this".
- **One form files and edits.** Clicking a card loads it into the form
  and names what sits around it. Two forms would be two places for the
  same rule to drift.
- **A rejected card says why, naming the field** — *a card needs a
  title*, *load must be 1 to 10*, *a cell is a letter and 1-3 digits*.
  Swallowing the error and saving something nearly right is how a grid
  fills with rows the owner did not mean.
- Each row is a real `<button>` with an `aria-label`, and the zone is
  printed as a **word**, never carried by colour alone (WCAG 1.4.1).

**12 shell tests.** One asserts the page computes no address of its own
— no `charCodeAt`, no `fromCharCode`, no sort — because an address worked
out in the page would be a second copy of a rule the kernel already owns,
and the copy in the page would be the untested one. The panel introduces
no new colour, so the existing contrast audit still covers every pair.

Suite: **620 passing.**
### Added — note cards on the A1 grid, ported from the browser (2026-11-27)

The feature was built in the published browser page and the laptop
never got it. The reason is worth keeping: the only thing that ever
reached this repository was `strata_console_browser.html`, a **snapshot**
of that page. A snapshot is a record, not code — it documented the
feature perfectly and shipped nothing.

- **[`strata_tools/cards.py`](strata_tools/cards.py)** — the kernel. A
  card is a short note with an **address**: `H5`, `A1`, `Z999`. The
  address is the point: a title can be forgotten and a search can miss,
  but a coordinate can be said out loud, written on paper, and typed the
  same way twice. The pattern is **copied** from the browser build, not
  improved, so a card written there still reads here.
- **Both reading directions**, which are real features rather than
  decoration. Row-major reads `A1, B1, C1` then drops down; column-major
  reads `A1, A2, A3` then moves across. The same cards in a different
  order put different neighbours side by side, which is the whole reason
  to use a grid instead of a list. A test fails if the two orders ever
  agree on a non-trivial grid.
- `neighbours()` reports the four adjacent cards **and the gaps** — the
  gaps are the useful half. `next_free()` so a card can be filed without
  remembering what is taken. `find()` takes one box and forks it: an
  address jumps, words search.
- **The store** on `StrataDB`. The cell is `UNIQUE` and a second save
  updates by address, because two cards at `H5` would make "go to H5"
  ambiguous and defeat the point. `delete_card()` exists **only to
  refuse**, by name, so the absence is a decision a reader can find
  rather than a gap they assume is an oversight.
- **The assistant can read them.** `🗂 Note cards` joins 🌐 and ☁ as a
  context source. Each passage is **named by its address**, so an answer
  can say "H5 says" and the owner goes straight there — a passage quoted
  without a coordinate is one he has to hunt for. Cards rank **second
  only to the file just handed over**: they are his own curated notes and
  outrank anything indexed months ago or fetched from the web. The grid
  is read from the store each turn, so a card written a moment ago is
  findable in the very next message.
- **`/cards`** lists the grid; `/cards down` reads it column-first;
  `/cards H5` reads one card and names what sits around it; an empty
  address reports the next free cell instead of just failing.

**62 kernel and store tests, 5 shell tests.** Two bugs in the kernel were
caught by its own tests before anything was wired: `str(None)` is the
truthy four-character string `"None"`, so a missing title would have
filed a card literally named None; and `walk()` left its order check to
the sort key, which `sorted()` never calls on an empty list — a
misspelled order passed silently and would have failed only once the
owner had cards.

**What did not come over, and why it is the engine and not effort:**
images (llama3.2:3b has no image input), the 🌐 Exa and ☁ Google Drive
sources (those are the viewer's own claude.ai connectors, not endpoints a
local app may call), and the behavioural overlays and 45-cell interaction
matrix (they condition a frontier model on nine simultaneous constraints;
a 3B model cannot act on them). Roughly two thirds of the browser build
transfers; the dividing line is always the same.
### Changed — the browser snapshot is now a repo-side build, not an Artifact mirror (2026-11-25)

The Prompt Library (PR #2) was written against the **108,563-byte**
snapshot and had been open long enough that `main` moved 19 commits past
it, re-filing the snapshot at **235,333 bytes**. Merging it as it stood
would have replaced the larger snapshot with a 124,219-byte one and
silently dropped the Omega-1 overlays, the glyph keyboard, Sheets,
`/find` and `/export` that `main` had recorded since.

So it was rebased rather than merged: the Prompt Library's five hunks
were re-applied on top of the current snapshot.

| | Bytes | SHA256 |
| --- | --- | --- |
| before (main) | 235,333 | `0cfe0684…fa2cc1` |
| PR #2 as written | 124,219 | superseded, never merged |
| **after (this build)** | **250,975** | **`d145859299b3cdf11657234cdb55ca1e80d42c40e9acb7290c93da33948e22ac`** |

Two conflicts were resolved by hand, both keeping `main`'s newer work:

- The `COMMANDS` help map — `main`'s thirteen entries kept, with
  `promptlib` added. PR #2's eight-entry version would have removed
  `avatar`, `keyboard`, `sheet`, `overlay`, `find` and `export`.
- The dispatch path in `send()` — `main`'s **H6 snapshot-at-dispatch**
  block kept in full, with PR #2's `promptlib.retrieve()` injection
  placed ahead of it. PR #2 still read the live `zone`; `main` reads the
  frozen `turnZone`. Taking PR #2's side verbatim would have undone H6
  and let a control flipped mid-answer rewrite a turn already in flight.

**What this file now is.** Until today `strata_console_browser.html` was
a byte-for-byte snapshot of the published Artifact, and its hash could be
diffed against the live page. It no longer can: this build exists only in
the repository. It is the browser build's **source of record**, not a
mirror, and the hash above attests to the file in this commit and to
nothing else. Re-filing a true snapshot means publishing this build to
the Artifact and exporting it back — an owner decision, filed in
docs/OPEN_DECISIONS.md, not taken here.


### Fixed — the JS bridge sent pywebview recursing into the window on every launch (2026-11-24)

`FB-017` — [docs/FORMER_BUGS.md](docs/FORMER_BUGS.md). Found while
measuring the two above.

pywebview builds its bridge by walking `dir()` over the `js_api` object
and recursing into non-callable attributes. `api.window = window` gave
it a path into the WinForms `Form` and down
`AccessibilityObject.Bounds.Empty.Empty.Empty…` until it hit Python's
recursion limit — several hundred times, on the startup path, logged and
discarded. Under `pythonw` there is no console, so nobody ever saw it.

- `api.window` → **`api._window`**. The walker skips `_` names; the
  upload dialog still has its native window.
- Measured: the recursion errors are gone, and the new window reports
  `IsHungAppWindow = false` where the old one reported true.

### Fixed — clicking the icon stood down in favour of a hung console (2026-11-24)

The other half of "it does not open", and the half that made it
permanent. `FB-016` — [docs/FORMER_BUGS.md](docs/FORMER_BUGS.md).

Once the first console stopped responding, its process stayed alive, so
every later launch correctly deferred to it — and then reported success
after calling `SetForegroundWindow` on a window that could not come to
the front. The launch exited having opened nothing, and said nothing.
Reproduced by launching the way the shortcut does: no window in 100
seconds.

- **`single_instance.choose_raisable()`** (new, pure) drops hung windows
  and Windows' own `(Not Responding)` ghost — which belongs to
  `dwm.exe`, and which the old `startswith` title match accepted — and
  requires the window to belong to the process the lock names.
- **`_raise_existing_window(lock_pid)`** now reads `IsHungAppWindow` per
  window. Windows knew the answer the whole time.
- **The decline speaks**: `unresponsive_message()` names the pid, the
  state, that a fresh console is starting, and that the stuck one is
  still holding memory.
- **The fail-open branch is reachable at last.** It was written from the
  start — "a lock naming a live process whose window cannot be found
  starts normally too, saying so" — and `found` was standing in for
  *can actually be raised*.
- **Tests: 529 → 541.**

### Fixed — the window opened 154px below the bottom of the screen (2026-11-24)

Reported as "you click start and it just stays frozen and it does not
open". It was opening; 154 pixels of it, the message box and Send among
them, were below the edge of the display. `FB-015` —
[docs/FORMER_BUGS.md](docs/FORMER_BUGS.md) carries the root cause.

Measured on the owner's laptop, both instances running side by side at
the same moment:

| | Window | Work area | Bottom edge |
| --- | --- | --- | --- |
| before | 1000×633 at (50, 90) | 1097×529 at (0, 40) | 723 vs 569 — **154px off** |
| after | 1000×481 at (48, 64) | 1097×529 at (0, 40) | 545 — fits, 24px clear |

- **`strata_tools/window_fit.py` restored** as a pure kernel. It was
  deleted on 2026-09-01 with the CustomTkinter shell it guarded, and the
  defect it guarded against (FB-001) returned in WebView2 three weeks
  later. `plan()` derives origin and size from the measured work area.
- **`strata_web.py` plans the window** instead of passing
  `width=1000, height=680`, and reads the work area through
  `SPI_GETWORKAREA` with two named fallbacks.
- **The measurement is printed at startup** — `🪟 window 1000x481 at
  (48, 64) fits the work area 1097x529 at (0, 40) (from work area)`.
  FB-001 ran for weeks because a window in the wrong place never
  reported a number.
- **Design-law rule D** (new) fails the build on a literal
  `width`/`height`/`x`/`y` handed to `create_window`. Rule B watched
  Tk's `geometry("WxH")` and so watched nothing at all once the shell
  became HTML.
- **Tests: 508 → 529.** `tests/test_window_fit.py` sweeps 17 work areas
  × 8 desired sizes × 4 margins; `tests/test_ci_workflow.py` trades a
  filename ban on `window_fit.py` for a content assertion that it exists
  and carries no Tk.

### Removed — the token keys, leaving the keyboard empty (2026-10-17)

Owner's instruction, straight after the pictures came off: with the emoji
gone the keys are not wanted either — the panel should be blank and
refilled with a vocabulary he is choosing. **Version 18 of the Artifact.**

- `KBD_BANKS` is now `[]` and `KBD_ALT_DIGITS` is `{}`. No key is built,
  and no Alt-shortcut types a token the keyboard no longer shows.
- **The machinery is deliberately left standing.** `kbdKey`,
  `kbdTokens`, the grammar layer, the sequence bar and the Recent row
  are all still here. Refilling is a DATA change — add a bank to
  `KBD_BANKS` — not a rebuild, and the shape is documented in a comment
  at the empty list.
- **An empty panel says it is empty.** A blank drawer with no
  explanation reads as a control that failed to load, which is the
  defect class this shop names first. It states that the set was
  removed, that a new one has not arrived, and that the message box
  works as normal meanwhile.
- The `/keyboard` command and the button tooltip say the same thing
  rather than advertising keys that are not there.

The operator vocabulary itself (`GLYPHS`) is untouched, so **knowledge-
base cards already saved against it still resolve** — both as written
tokens and as the retired emoji. Emptying the keyboard removed a way to
TYPE the vocabulary, not the vocabulary.
### Removed — the emoji keys on the browser keyboard (2026-10-17)

Owner's instruction, with a screenshot of the keyboard: the eighteen
picture keys were to go. **Published as Version 17 of the Artifact** — the
browser build is edited where it is published, so the desktop change
earlier today did not touch it.

- **A key reads as a word.** `EXECUTE`, `GOLDEN SOURCE`, `ANALYZE` — the
  name only. No picture is drawn on any operator key.
- **A tap types a written token**, `[EXECUTE]`, into the message box.
  A written token survives copy-paste, search, a screen reader and a
  plain-text export; an emoji survives none of those reliably.
- **The classifier and the sequence bar read both spellings.** The
  retired pictures still resolve to the same operator, so a message
  typed from old habit — and, the real reason, a **knowledge-base card
  already saved with a glyph** — still reads. The glyph character
  remains the internal identity, so the interaction matrix, the card
  lifecycle and the avatar are untouched.
- `/lexicon` lists tokens; the grammar verdicts and the keyboard's
  tooltips say "token" where they said "glyph".
- The grammar operators (`→ + ↔`), Space and Backspace keep their symbols:
  those are the grammar itself, not the vocabulary that was retired.

**A bug caught in test before it shipped.** The rewritten tokenizer
indexed the message with `src[i]`. An emoji is a surrogate **pair**, so
numeric indexing splits it in half — and every retired picture silently
stopped being recognised, which would have broken exactly the stored
cards this change was built to protect. `Array.from` restores code-point
iteration. Found by running the patched functions under Node against six
cases (new token, old emoji, mixed chain, lower case, prose, operators)
before publishing, not by reading the diff.

**Still owed:** the replacement set — OD-002. Nothing was invented.
### Removed — the emoji operator vocabulary (2026-10-17)

Owner's instruction, given on inspection: the pictures were too easy for
a person and a language model to read differently, and were to be erased.

- **`GLYPH_CODEX` is deleted from `strata_core.py`** — the nine-emoji
  table the input classifier matched on and `/lexicon` printed. The
  engine vocabulary is now `TOKENS`, derived from `codex.OPERATORS`:
  nineteen operators addressed by a stable four-letter **code**. This is
  what `codex.py` was built for on 2026-10-15 — *"so a glyph can stop
  being one"* — and the engine had simply never been moved over.
- **The classifier reads codes.** `EXEC ship the thing` is detected as
  `EXEC`. NM-009 is the argument: one ice cube had come to mean three
  different things across three artefacts, and whichever meaning
  happened to be listed first decided how every stored row would be
  re-read. A four-letter code cannot have that ambiguity.
- **`/lexicon` prints codes**, never pictures.
- **The keyboard never showed one.** Ticket 6 was built on
  `codex.display()`, which returns label, zone and icon name and no
  glyph character at all. Confirmed, not assumed: a test now walks every
  key the keyboard is handed and fails on any codepoint above U+2500.

**What was deliberately kept.** `codex.LEGACY_RESOLUTION` still maps each
retired emoji to the code that replaced it, and the classifier still
resolves one — so a message typed from old habit, and more importantly a
row **already stored in SQLite**, still reads. Archive, never delete:
retiring a vocabulary must not make the records written in it unreadable.
Resolving an old picture is not offering a new one, and that is the line
the new tests hold.

**Gate:** `tests/test_codex.py` fails if a picture appears in any offered
surface — operator labels and instructions, action verbs, the keyboard
payload, a `reads_as()` sentence, the engine's `TOKENS`, or either shipped
shell file. Four detection tests cover codes found, nothing found, a
legacy picture resolved, and a legacy picture stripped from the residual.

**Still owed:** the replacement glyph set. The owner has one; it is not in
this repository, not in `Claude AI`, and not in the session that made this
change. Nothing was invented to fill the gap — the vocabulary is codes
until he supplies it. See [`docs/OPEN_DECISIONS.md`](docs/OPEN_DECISIONS.md) OD-002.
### Added — the glyph keyboard and the cycle summary (2026-10-17)

The last two kernels with no control attached. Both are now reachable.

**Ticket 6 — the glyph keyboard.** `/keys` or **Alt+K** opens a panel of
the nineteen codex operators in address order plus the eight action
verbs. Tapping keys builds a chain; the sequence bar reads it back in
English through `codex.reads_as()` — "Take it in -- execute, in the
green zone" — so a chain can be checked without consulting a legend,
which is the test the old keyboard failed.

- **The keys type into the message box**, the same box a hardware
  keyboard types into. One input path, never two, so commands, the
  pipeline and the dictation polish all see one kind of message. A test
  asserts the insert path touches `#msg` and never calls `api.send`.
- **The grammar stays in the kernel.** The page asks `codex_reads()` and
  renders the answer; a test forbids the page from reimplementing the
  joining rule, because the copy in the page would be the untested one.
- **An unrecognised code is named, not swallowed** — a key that types a
  token the codex does not know and says nothing is a silent decline.
- Each key carries its meaning three ways: label, zone word, and
  `aria-pressed` plus a thickened border for selection, so colour is
  never the only cue (WCAG 1.4.1). **Alt+K** exists because a panel only
  openable by click is a panel some people cannot open (WCAG 2.1.1).

**Ticket 7 — what the cycles say.** A **Stats** button and `/focus stats`
render the six analysis functions that shipped on 2026-10-15 and had
never been displayed: completion rate, a per-length table, the length
actually finished most often, mean reported load at each phase and its
change, and a work-day versus rest-day comparison.

- **Every figure comes from the kernel.** A test forbids the page from
  computing a statistic of its own.
- **Nothing is crowned on a thin field.** `best_cycle_length` requires
  three closed cycles, and the summary reports the absence as "the
  honest answer, not a missing number" rather than naming a winner from
  two tries.
- **The day comparison carries its caveat in writing**: observed
  differences, not causes — a work day differs from a rest day in more
  ways than one record can separate, sleep among them.
- Every load figure is labelled a *report*, and structural problems from
  `validate()` are surfaced rather than hidden.

### Fixed — the summary crashed on a single day type (2026-10-17)

- `compare_by_day_type` emits one row per day type **always**, and a type
  with no cycles comes back short — `day_type`, `cycles`, `note`, and no
  `completion_rate`. The summary read `completion_rate` off every row, so
  it raised `KeyError` whenever only one day type had data, which is
  every early day of use. Caught by the new tests before it reached the
  owner. **Guard:** rows with no cycles are filtered out and the table is
  drawn only when two day types actually have data — a comparison
  against an empty column is not a comparison — with three regression
  tests including a cycle on a day that was never recorded.

### Removed — the last of the CustomTkinter shell (2026-10-17)

- **`strata_tools/keyboard.py`** and its 20 tests. 239 lines of Tk
  focus-ring traversal for a shell retired on 2026-09-01. `layout.py`,
  `window_fit.py` and `selection.py` went with that shell; this one was
  missed and sat in the tree for six weeks driving a toolkit nothing
  imports. Twenty green tests made it look alive.
- One constant was still in use: `FOCUS_RING`, by the web shell's own
  contrast tests. It moved to [`strata_tools/theme.py`](strata_tools/theme.py),
  where a colour belongs — not in a module about widget traversal.
- **Gate:** `tests/test_ci_workflow.py` now fails if any shipped module
  imports `customtkinter` or `tkinter`, or if any of the four retired Tk
  kernels reappears in `strata_tools/`. `turbo_console.py` is exempt and
  named: it is a separate dormant tool that still declares the
  dependency in `requirements.txt`. A sweep ends with a static gate.
### Added — the focus timer and the two-tap report (2026-10-17)

Ticket 5b. The kernel and the store existed; nothing could reach them.
Now a cycle can be started, watched, closed and reported on from the
shell. Pseudocode was written and filed before the code, at
`Claude AI\Portfolio\boards\2026-10-17_focus-timer-two-tap-report.md`.

- **The timer** — a length (15 | 25 | 45), Start, Stop, and a countdown
  in the top row. 15 minutes is offered first because that is the window
  a work day actually leaves; the roster chose the list, not a
  productivity convention.
- **The engine owns the clock.** Both timestamps on a stored row are
  stamped in Python. The page asks `focus_state()` for the remaining
  seconds and displays them, and a test asserts the page never stamps a
  timestamp of its own. Two clocks writing one row could record a
  negative length — which `focus.close_cycle` raises on, at the worst
  possible moment, after the work is already done.
- **A reload mid-cycle restores the timer**, because the open cycle lives
  on the bridge and the remaining time is derived from the stored start
  rather than from when the script began.
- **The cycle persists before it ticks.** If the write fails the timer
  does not start and says so. A countdown with no row behind it is a
  control that does nothing — and the owner would find out fifteen
  minutes later, with the work done and the record gone.
- **Starting twice is refused by name**, quoting the open cycle's length
  and start time rather than failing quietly.
- **The two-tap report** — tap a load from 1 to 10, tap a working mode,
  done. Offered at START and at END, and **Skip carries the same control
  class as the alternatives**: a Skip that is smaller or greyer than the
  button beside it is a nudge, and §2's carve-out rules out nudges, so
  equal prominence is asserted structurally rather than promised.
- **The wording asks what is reported, not what is.** "How loaded does
  this feel right now?" A dial is not an instrument for cognitive load;
  §3 makes any label implying otherwise a defect, and tests ban
  "measured", "detected" and the rest from the prompt.
- **Nothing urges.** An abandoned cycle is reported as data — "a cycle
  cut short is how the length you can actually finish gets found" — and
  tests ban streak, praise, goal, target and quota language from the
  kernel, the HTML and the JavaScript alike. "Well done" and "you broke
  your streak" are one defect in two coats: both treat the number as a
  score.
- **`/focus`** starts, reports and stops a cycle from the message box;
  `/focus` alone says what is open.
- Shell-facing rules went to the kernel first, as always:
  `format_remaining`, `remaining_seconds`, `report_prompt`,
  `closing_note`, `start_refusal`, `MODES`, `LENGTHS` — **15 kernel
  tests** — then **15 shell tests** on the shipped HTML, CSS and JS. The
  focus rules introduce no new colour, so the existing contrast audit
  still covers every pair on screen.

### Fixed — the suite stopped spilling warnings (2026-10-17)

- `tests/test_web_shell.py` read the three shell files with bare
  `open(path).read()` in **nineteen** places, leaving each handle to the
  garbage collector and spilling a `ResourceWarning` per test. One
  `read()` helper now closes them. Warning noise is not harmless — it is
  where a real warning goes to hide, and the suite had been printing
  enough of it to bury one.
### Fixed — the quality gate had been failing for six weeks (2026-10-17)

- **CI has been red on every push since 2026-09-01** and nobody knew.
  `strata_console.py` was deleted with the CustomTkinter shell that day;
  `.github/workflows/ci.yml` went on running `py_compile
  strata_console.py` and `import strata_console`. Eight consecutive
  failed runs, across four feature tickets and three documentation
  commits, while `SCOPE.md` §3 listed "proven by CI" as a met
  acceptance criterion. The suite was green throughout — which is
  exactly what kept it hidden. Recorded as
  [FB-013](docs/FORMER_BUGS.md) with standing law 10: *a gate that
  cannot pass is not a gate, it is a false acceptance claim.*
- The compile list now names files that exist; the degraded-mode check
  asserts both that the engine imports with **no** UI library and that
  the shell imports on `pywebview` alone. `customtkinter`, retired as a
  dependency on 2026-09-01, is no longer installed in CI; `pywebview`,
  which the shell actually requires, now is — it never had been.
- **Guard:** [`tests/test_ci_workflow.py`](tests/test_ci_workflow.py),
  8 tests in the **local** suite, asserting every path and module the
  workflow executes exists, that no live step names the retired shell,
  and that CI installs nothing optional. It runs outside the gate it
  watches, because a gate cannot report its own death. Verified by
  reintroducing the defect and confirming the guard fails.

### Added — focus cycles persist (2026-10-17)

Ticket 5a. `strata_tools/focus.py` declared a `SCHEMA` on 2026-10-15 but
nothing created those tables, so a recorded cycle lived only until the
window closed. Six methods on `StrataDB` close that seam and decide
nothing: `save_cycle`, `save_report`, `save_day`, `cycles`, `reports`,
`days`.

- **The schema is executed from the kernel's own declaration**, never
  retyped — `for statement in focus.SCHEMA`. NM-009 was a second copy of
  a mapping drifting from the first; a schema is the same hazard, so
  there is exactly one definition of it.
- **Additive migration.** The three existing tables and their rows are
  untouched; a database written before these tables existed gains them
  on open and keeps everything it held.
- `save_cycle` is `INSERT OR REPLACE`, because `focus.close_cycle`
  returns a new dict carrying the id it was opened with. A plain INSERT
  would store the finished cycle a second time and leave the open one
  behind — a duplicate id, which `validate()` reports and every average
  would then count twice.
- `save_report` is append-only by design: a report records what was felt
  at a moment, and a moment does not get revised. There is deliberately
  no update and no delete.
- **22 tests** ([`tests/test_focus_store.py`](tests/test_focus_store.py)),
  written before the implementation and red first. The ones that matter
  run the kernel's own analytics over rows that made the **round trip**,
  not over dicts that never left memory — so a load arriving back as a
  string, or minutes as a float, fails here rather than in a chart months
  from now. Every test uses a throwaway database, and one reads the live
  file directly to assert the suite never wrote to it.

No UI yet. The timer and the two-tap report are ticket 5b; a control
that does nothing would be a defect, so nothing was added to the shell.
### Added — the operator codex and the focus kernel (2026-10-15)

Two pure kernels, both headless, neither wired to any UI. Scope decision
logged in [`docs/SCOPE.md`](docs/SCOPE.md) §6 before either was written.

- **[`strata_tools/codex.py`](strata_tools/codex.py)** — nineteen
  operators, each carrying a stable four-letter `code`, a `number` (its
  address), a `label`, an `icon` name, a `zone`, a `load` range, the
  pipeline `stage` it conditions, and its model instruction.

  **Identity moved off the glyph.** The ice cube had come to mean three
  different things across three artefacts — *Logic / Stabilize* in one
  source document, *Crystallized Memory* in another, and `GOLDEN_SOURCE`
  in the shipped browser build. Nobody erred; a picture can be re-read,
  and re-reading leaves no trace. A code cannot drift, because changing
  one is a visible edit. The icon is now display only and can be replaced
  on any day without migrating a stored row.

  Emoji are out of every identifier: they render differently per
  platform, screen-read as their Unicode name ("snake", not "cycle"), and
  reach a language model carrying their own conventional meaning. A test
  holds every code, label, icon and instruction to ASCII.

  Codex v2 is **frozen at eighteen** in `CODEX_V2_FROZEN` — superseded,
  not deleted — and every frozen glyph still resolves, so no stored row
  becomes unreadable. The cube split into `STAB` (structure) and `GOLD`
  (canonical); `WAVE` kept the shipped meaning of uncertainty. The
  governance glyphs are cut and recorded in `RETIRED` with their reasons:
  they claimed the system validates ethics, balances equity and forgives
  error, and it does none of those. A test bans that vocabulary from
  every instruction string.

  Nineteen, not twenty. Twenty was a round number chosen before the
  concepts were counted.

- **[`strata_tools/focus.py`](strata_tools/focus.py)** — focus cycles and
  experience sampling. Three tables declared as `SCHEMA`, constructors
  that refuse bad input by name, and the queries that answer the owner's
  own question: `cycle_length_report()` and `best_cycle_length()` give the
  completion rate for every cycle length he has tried.

  What it records is a **self-report**. The column is `reported_load`, not
  `cognitive_load`, per the acceptance criterion added to `SCOPE.md` §3.

  Rows, not cells: `cycles` is a fact table that grows downward and `days`
  is a small dimension table, because a fixed grid cannot model a calendar
  when months are 28, 30 or 31 days and the roster is two on, two off,
  three on.

  An abandoned cycle is **data, not failure**, and is persisted as such.
  A skipped prompt leaves the cycle unaffected. `completion_rate` returns
  `None` for nothing-recorded and `0.0` for everything-abandoned, because
  those are different facts. `compare_by_day_type` carries `hours_slept`
  through and stamps every row `observed_not_caused`.

- **Two near-misses recorded** in
  [`docs/FORMER_BUGS.md`](docs/FORMER_BUGS.md) — **NM-009** (list order
  silently deciding a data migration) and **NM-010** (a gamification guard
  that could not tell a ban from a reward). Both were caught by the suite
  before shipping; both now carry guards.

400 tests pass, including the design-law linter over the whole repository.

---

Docs and on-repo reference for the **browser build** (a separate
single-page snapshot of Strata Console, published as a claude.ai
Artifact). No application behaviour changes; no Python touched, and the
desktop shell, engine, tools and tests are untouched.

### Added
- **`strata_console_browser.html`** at the repository root — byte-for-byte
  snapshot of the Strata Console browser Artifact as served, the
  publish-time `<head>` included. **Re-filed 2026-10-17 from Version 18:
  235,333 bytes, SHA256**
  `0cfe0684eac7a1b4311f2ac47f6ffdbfab2bcc6307c00a002a730d96b8fa2cc1`.
  Filed as the permanent on-repo reference alongside the Artifact link
  and the Google Docs / OneDrive record; a diff against that hash tells
  you whether this file still matches the published Artifact.

  The snapshot it replaces was filed 2026-09-17 at 108,563 bytes and
  SHA256 `6e99db91...`. The browser build more than doubled in the four
  days after it, and the repository recorded none of that — so the
  integrity line above was answering a question nobody could use: it
  proved the file matched a September snapshot, while reading as though
  it proved the file matched the published build. A stale snapshot is
  worse than an absent one, because it looks like a record.
The **browser build**'s documentation gate and its first shipped
feature. Nothing in the Python desktop app changes; the desktop shell,
engine, tools and tests are untouched.

### Added
- **Prompt Library v1** in the browser build (`strata_console_browser.html`).
  Every completed pod exchange is captured, classified into one of ten
  fixed Dewey-style drawers (A–J) with a per-drawer arrival coordinate,
  and searched on the next message so the assistant can flag anything
  already tried. Lives under its own storage key `strata_promptlib_v1`,
  fully separate from the conversation stores and the Knowledge Base.
  Includes a `/promptlib` command showing counts, coordinates and
  storage used. Blueprint: `docs/PROMPT_LIBRARY_BLUEPRINT.md`.

  Design gaps flagged in the blueprint's Copilot review are closed in
  this v1:
  - **Coordinates never collide** after delete or prune. A monotonic
    per-class sequence (`nextRow`) is only ever incremented; pruned or
    deleted records leave gaps rather than freeing the number.
  - **Ties are deterministic.** Classification breaks ties to the
    earliest class in A→I order. J is used only when every score is
    zero.
  - **Shared-quota safety.** Cap is 400 records **or** 2.5 MB serialized,
    whichever first (measured with `TextEncoder`, not UTF-16 code
    units, so non-ASCII payloads count accurately). Every write is
    guarded — a `QuotaExceededError` from another store crowding
    localStorage triggers a snapshot-and-prune with a **visible warning
    in the transcript** so nothing is silently lost, and points the
    user at `/promptlib export` to save an archive before more records
    are pruned. A two-strike quota failure rolls RAM back to the
    pre-capture state so the in-memory view matches disk (no mixed
    state that could overwrite older records on the next successful
    write).
  - **Reproducible classification.** The keyword lexicons for A–I are
    listed in the module; tokenizing is lower-case word-boundary
    matching; each keyword hit is one point (multiplicity counts); J
    is the zero-score fallback. This is v1; classes and coords stay
    editable — the machine files, the librarian corrects.
  - **Retrieval de-noised.** Query and record text are compared on
    content tokens only — a small stopword list strips filler words
    like "a", "do", "the", "for" so a message mentioning them doesn't
    drag every stored record into context.
  - **`/promptlib export`** dumps the whole archive as JSON in the
    transcript, so pruned records can be saved elsewhere before the
    browser store runs out of room. `/promptlib` itself always shows
    each drawer's next coord (including empty drawers, which start at
    row 1).

  The full Library-drawer UI (browse, re-file, delete, export) is a
  follow-up increment per the blueprint's "small increments" gate.
- **`strata_console_browser.html`** at the repository root — filed as
  the permanent on-repo reference alongside the Artifact link and the
  Google Docs / OneDrive record. Initially a byte-for-byte snapshot of
  the published Artifact (commit `2e06070`, 108,563 bytes, SHA256
  `6e99db91ef61c656b0ffe1682408764f26f7bf42f660171569e4be888b2d9241`).
  With Prompt Library v1 added, this file is now the browser build's
  living source rather than a snapshot; a future re-publish of the
  Artifact resyncs the two.
- **[`docs/PROMPT_LIBRARY_BLUEPRINT.md`](docs/PROMPT_LIBRARY_BLUEPRINT.md)** —
  v1 blueprint. Ten fixed Dewey-style classes (A–J) with keyword-scored
  classification, one record per completed pod exchange stored under
  `strata_promptlib_v1` (400-record / 2.5 MB cap, export-then-prune at
  the cap), retrieval labelled as past-conversation memory, and a
  `/promptlib` command. Includes the storage-tier proposal (hot / warm
  / archival to Google Drive), pseudocode, and the ISO/IEC/IEEE 12207
  process gate. **Owner-approved; v1 implementation lands under this
  `[Unreleased]`.**
- **README section "Browser build"** — points at the on-repo file,
  explains its relationship to the desktop app documented above it, and
  names the Prompt Library as the first browser-side feature scoped
  through the documentation gate.

### Browser build — the record the repository was missing

Recorded 2026-10-14, reconstructed from the build's own port notes
(`/port` in the console). None of the following is desktop work: no
Python was touched and the desktop shell, engine, tools and tests are
unchanged. It is listed here because the repository is the record for
both build targets, and for four days it was the record for only one.

- **2026-09-18 — Dictation failure named before it happens.** A host
  that embeds the page in a frame without delegating microphone access
  hard-blocks dictation before any permission prompt appears. The
  console detects that up front, dims **Speak**, and says why, rather
  than offering a control that cannot work — the same law the desktop
  learned at FB-002 and the interpreter rule.
- **2026-09-18 — Images.** 📎 attaches PNG, JPEG, WebP or GIF and the
  pod assistant sees the image itself while it stays attached. A second
  lane beside the text one, not a new pipeline stage: pixels cannot be
  chunk-ranked, so the image bypasses the retrieval kernel. **Web-only —
  llama3.2:3b has no vision, so this cannot be ported.**
- **2026-09-19 — Avatar Visualizer.** The orb in the top bar is a live
  view of console state from real signals (processing, error, focus,
  idle), specified as React/Tailwind and implemented as plain SVG in the
  console's measured hues, honouring reduced motion.
- **2026-09-19 — Omega-1.** Codex Glyph Legend v2: nine glyphs each
  carrying a zone, a cognitive-load range and an AI instruction. Five
  behavioral overlays (executive_focus, safe_mode, flow_state,
  reflection_mode, crisis_triage) plus a 1-10 load dial.
- **2026-09-19 — Export bridge.** Every knowledge-base item and tab
  exports as a self-describing markdown record. Export reads the data
  model, not the view, so the drawer's 700-character display clip never
  truncates anything on its way out. It exists because a handoff filed
  in browser-local storage cannot be read by anything outside that
  browser: the human is the bridge, by design.
- **2026-09-19 — The H5 build.** A 45-cell glyph x overlay interaction
  matrix conditioning the assistant; card history, links and a startup
  lifecycle pass (🎯 softens after 7 days, RED archive at 30, 🧊 exempt,
  nothing ever deleted); Crisis Triage formalized as **manual-only** —
  no keyword scoring and no automatic switching, naming real support
  (988; text HOME to 741741) because a productivity tool should know
  what it is not.
- **2026-09-20 — Codex Expansion v3.8.** Six new glyphs adopted with
  real instructions. The v3.8 meanings that would contradict v2 (🧊 as
  mere stabilize, 🌊 as peace) were refused — one glyph, one meaning —
  and 👥 multi-agent orchestration was declined outright: this console is
  structurally Claude-only, and a key that pretends otherwise lies.
- **2026-09-20 — The glyph keyboard.** An on-screen codex keyboard with
  a grammar layer and a sequence bar that translates a chain as it is
  built (Alt+K; Alt+1-0 for the core ten). It types into the same
  message box a hardware keyboard does — one input path, never two.
- **2026-09-20 — Chronofold declined, and the reasoning kept.** The H6
  card asked for handshake engines and a lattice validator from
  asynchronous circuit design. The field is real; the need here is not —
  a browser page is single-threaded with run-to-completion semantics, so
  the no-deadlock, no-race guarantee holds by construction, and
  machinery that solves no problem is risk, not rigor. Recorded because
  a refusal with a reason is an engineering decision, not a gap.
- **2026-09-21 — Strata Sheets.** A working spreadsheet: cells A1-Z200,
  formulas (SUM, AVERAGE, COUNT, MIN, MAX, ROUND, ABS), CSV in and out,
  readable and writable by the assistant through page-defined tools. The
  ask was LibreOffice-class; the answer was honest about why one page
  cannot be a desktop office suite, and then built what it can be.

### Fixed
- **The published Quick start no longer sends people to a repository
  that does not exist.** The clone URL still named `strata-console`,
  retired in the 2026-09-03 rename; step 1 of the only installation
  instructions the project offers returned a 404. Now
  `local-nlp-pipeline-console`, matching the actual remote.
- **The snapshot integrity check now works on the platform the project
  targets.** `strata_console_browser.html` was committed without a
  line-ending rule, so with Git's `core.autocrlf=true` -- the Windows
  default -- checkout rewrote 2,700 line endings and the working copy
  arrived 111,263 bytes hashing to `99a99799...`. The byte count and
  SHA256 published above were correct for the committed blob and wrong
  for every file a Windows reader could actually hold, which is the
  only file they can hash. A `.gitattributes` now marks the snapshot
  `-text`, so it is never converted and the documented check answers
  truthfully. Verified: on-disk file is 108,563 bytes, SHA256
  `6e99db91ef61c656b0ffe1682408764f26f7bf42f660171569e4be888b2d9241`.
- **Stray files cleared from the repository root** -- an empty `e.txt`,
  the `.coverage` pytest-cov artifact, and a Windows shortcut to an
  unrelated project. `.gitignore` gained `.coverage` and `*.lnk`.
### Integrity
- After Prompt Library v1 with review-round fixes: 124,219 bytes, SHA256
  `22739c3391add560ffca89b5c3e7db0ae0ce668157fe63baca288a3d0fc02e5c`.
  A `sha256sum strata_console_browser.html` matching this value confirms
  the file has not drifted since v1 was filed. (Earlier v1 draft was
  120,357 bytes / `0bce3992…`; superseded by review fixes for UTF-16
  byte accounting, retrieval de-noising, empty-drawer display, quota
  rollback consistency, and the `/promptlib export` command.)

## [2.2.0] — 2026-09-02

The owner asked, fairly, whether the app was using too much memory and
whether it should simply be removed. The first answer is yes; the
second is no. This release makes the first answer visible.

### Fixed
- **The model no longer denies a capability the console has** (FB-012).
  Asked to search with web search off, llama3.2 answered "I can't browse
  the internet" from its training — true of the model, false of the
  app, and reported as the feature not working. The system prompt now
  briefs the model on its tools both ways: with results present, "the
  search has been done for you, cite it"; without, "tell the user to
  tick 🌐 or say 'search the web'". Verified live: the same question
  now searches and cites AccuWeather.
- **Everyday search phrasing is recognised.** "search for", "look up",
  "find out", "latest news", "do a search" and four more join the
  trigger list. The owner had asked in words the list did not cover.

### Added
- **A RAM budget for the language model** (`strata_tools/model_budget.py`,
  12 tests), the discipline the voice model has had since FB-002. Free
  memory is measured against the size Ollama reports for the model. On
  a starved machine the startup warm-up is **skipped** — loading 2.3 GB
  into 475 MB of free RAM is what freezes the window — and the owner is
  told in numbers: `⚠ Low memory: 1,277 MB free, and llama3.2:3b wants
  about 2,225 MB — 948 MB short. Replies will be slow (measured: 3 s
  with room, over 100 s without). Close other programs, or switch to
  the lighter llama3.2:1b.`
- **Free RAM on screen, always**, in the header. A figure seen every
  day is one that can be read at a glance when it drops.
- `LLMBrain.size_bytes` — resident size from `ollama list`, so the
  budget is computed rather than assumed.

### Measured, for the record
Same code, same model, same question:

| Free RAM | Pagefile in use | One reply |
| --- | --- | --- |
| 978 MB | — | 2.9 s |
| 1,277 MB | — | 78 s |
| 475 MB | 3.3 GB | 103.5 s |

What was crowding the machine at the slow readings: three Claude Code
processes (~1 GB), Windows Voice Access (253 MB), Defender (270 MB),
Edge. The app was not broken at any of them.

## [2.1.0] — 2026-09-01

### Fixed
- **The first message no longer looks like a hang** (FB-011). Reported
  as "it launches but just asks you to wait". Nothing was broken: a cold
  Ollama load is 2.3 GB into RAM on a CPU-only laptop, measured at
  **20.5s for the first reply against 2.9s once warm**, and the page
  showed a static `thinking (local model)…` throughout. A wait with no
  evidence of progress cannot be told apart from a crash.

### Added
- **Model warm-up at startup.** `LLMBrain.warm()` runs on a background
  thread as the window opens, so the load is paid while the opening
  message is being read rather than against the owner's first question.
  Measured effect: first user message **20.5s → 6.3s**. Progress is
  reported through the existing note queue.
- **`LLMBrain.is_loaded()`** — residency straight from the daemon,
  returning False whenever the answer is unknown. The asymmetry is
  deliberate: promising a fast reply and delivering twenty seconds is
  the failure being prevented.
- **An elapsed counter on the placeholder.** `thinking (local model)…
  7s`, or `loading the local model — first message, about 20 seconds…
  12s` when the model is genuinely cold. A number that changes is the
  difference between working and frozen.
- README section **"It launched but it just says wait"** with the real
  numbers and the `curl /api/ps` check.

### Investigation notes
Two strong hypotheses were checked and discarded first, recorded in
FB-011 because both looked convincing. The database and all 100 source
files carry `ReparsePoint` — OneDrive Files On-Demand — so hydration
stalls were the first suspect; **zero** files were actually `Offline`.
Startup was then timed against the real 97-thread database rather than a
temporary one; `bootstrap()` returned in 0.00s. Only timing three
consecutive messages located the cost.

## [2.0.0] — 2026-09-01

Major, because a whole front end was removed. Nothing the owner can do
was removed with it — see **Parity first**, below.

### Added
- **Slash commands in the web shell**: `/status`, `/lexicon`,
  `/mode green|yellow|red`, `/clear`, `/help`, with `/zone` and `/new`
  still accepted. Grammar and formatting live in
  `strata_tools/commands.py` as a pure kernel; executing a command
  touches the pipeline, so that stays in the bridge.
- **The operator token lexicon is reachable again** (`/lexicon`).
  `bootstrap()` had been shipping `ALL_GLYPHS` to the page since the web
  shell was written, and `app.js` never read them.

### Removed
- **`strata_console.py` — the CustomTkinter shell.** Retired at the
  owner's instruction. The two shells ran side by side so they could be
  compared on his real screen; the comparison concluded, and carrying
  the loser meant paying maintenance twice.
- Tk-only kernels: `strata_tools/layout.py`, `window_fit.py`,
  `selection.py`, and their tests.
- The five CustomTkinter measuring tools: `tools/dpi_check.py`,
  `fit_sweep.py`, `layout_probe.py`, `scaling_probe.py`,
  `_one_scaling.py`, plus `a11y_check.py`, which audited the Tk widget
  tree.
- `launch_strata_web.vbs`. **`launch_strata.vbs` now launches the web
  shell** and deliberately kept its name: the desktop and Start-menu
  shortcuts point at that path, and renaming it would orphan both.
- `customtkinter` from required dependencies.

### Parity first
Retirement was gated on capability, not preference. The Tk console could
do two things the web shell could not — slash commands and the lexicon —
and **both were ported and tested before it was deleted**, in a separate
commit, so the removal could not quietly take a feature with it.

### Changed
- Design-law **rules A and B are kept but re-scoped**. Neither can fire
  on the shipped shell any more, and this linter's own docstring says a
  rule that cannot fire is worse than none because it reads as proof.
  They stay as a tripwire for the dormant `turbo_console.py` and for any
  future return of Tk; `design_laws.py` now states that plainly.
- `test_session.py`'s "the shell does not shadow DB_PATH" check follows
  the shell rather than the filename — it now asserts against
  `strata_web`. The rule was never about `strata_console.py`.
- The design-law repository gate's "guard the guard" assertion now
  requires `strata_web.py` in the scanned set.

### Notes
- Suite: 294 tests green. The count fell from 333 because 39 tests went
  with the Tk code they existed to test — a smaller suite covering the
  same shipped surface, not less coverage.
- Three recorded defects (FB-001, FB-005, FB-006) were widgets drawn
  off-screen or unreachable by keyboard. That failure mode leaves with
  the toolkit.

## [1.5.0] — 2026-09-02

### Added
- **The three context sources reach the web shell**: 🌐 web search,
  ☁ OneDrive files and 📎 upload, which until now only the desktop
  shell had. Both stay switched on across turns, which is the point —
  the material can be discussed over a whole conversation rather than
  consulted once. Typing "look this up" still turns the web on for a
  single message without touching the checkbox.
- **Answers say what they read.** A `Read: 📎 lease.pdf · 🌐 web` line
  under a reply reports which sources were actually consulted. Without
  it there is no way to tell a grounded answer from the model answering
  confidently out of its own head.
- **`strata_tools/context_sources.py`** — the rule for what the model is
  handed, lifted out of `strata_console.py` into a pure, headless-tested
  kernel that both shells now call. 28 tests. It had been UI code no
  test could reach, and copying it into the second shell would have
  produced two rules that agreed until the first edit.

### Fixed
- **The web shell's note channel was never connected.** `Api` exposed
  `memory_note()` and no page ever called it, so the voice-model release
  watch — which does real work and frees ~221 MB — reported to nobody.
  Replaced with `poll_notes()`, a drained queue the page polls every
  five seconds, now shared with OneDrive indexing. A method the UI never
  calls is the bridge equivalent of a button that does nothing.
- **The web-search trigger phrases were never tested.** Eleven phrases
  shipped inside the Tk shell with no coverage; a dead entry among them
  would have been invisible. Each one is now asserted to fire.

### Guarded
- `tests/test_web_shell.py` imports the bridge and checks that **every**
  `api.*` call in `app.js` resolves to a real method on `Api`. A method
  indented one level wrong greps clean and fails at runtime as a
  rejected promise, which the page shows as nothing happening.
- The upload dialog's filter is asserted equal to `doc_index.SUPPORTED`,
  so the dialog can never offer a format the extractor cannot open.

## [1.4.1] — 2026-09-02

### Added
- **Read-along highlighting** in the web shell. While an answer is read
  aloud the sentence being spoken is highlighted and the current word is
  underlined, so the text can be followed by eye and by ear at once.
  Click any sentence to hear it again from that point; Escape stops.

  The alignment problem, and how it is solved: what is *spoken* is not
  always what is *shown* — `speech.speakable()` turns "$32" into
  "thirty-two dollars" so the engine pronounces it. The page therefore
  splits the **rendered** text and Python returns each piece's spoken
  form plus a `matches` flag. Sentence highlighting is exact because
  both sides index one array. Word highlighting uses the engine's
  character offsets, which only point into the displayed string when
  `matches` is true — otherwise it is skipped rather than lighting up
  the wrong word.

  Verified in a browser harness: a sentence running across `**bold**`
  stays one highlight over three spans; code blocks are excluded from
  what is read; every character offset maps to the correct word,
  including across an element boundary.

  Both highlight colours keep the body text above 4.5:1 (8.04:1 and
  6.04:1 measured), and the current word carries an underline as well as
  a background, so the two levels are not distinguished by colour alone.

---

## [1.4.0] — 2026-09-02

A second shell, and the engine split out so both can share it.

### Added
- **`strata_core.py`** — the engine with no interface attached: the
  SQLite store, the five pipeline stages, the model client. Imports no
  Tk and nothing that assumes a window.
- **`strata_web.py` + `web/`** — an HTML/CSS/JS front end in a native
  WebView2 window (pywebview). Same database, same modes, same voice
  path, same Ollama daemon. Launch with `launch_strata_web.vbs`.
- Auto-read, spoken punctuation, the clear floor and the RAM budget all
  work in both shells because they were already kernels.
- `tests/test_web_shell.py` — 18 tests that parse the real stylesheet and
  markup, so the two shells cannot drift into different palettes or
  different accessibility stories.

### Fixed
- Auto-read for the desktop shell, and its template-mode path, which had
  never set `_last_reply` and so replayed the previous answer.
- Buttons: FB-007. Every control failed WCAG 1.4.11 against its frame.

### Notes
- **The Tk shell is unchanged and still the default.** This is a
  comparison, not a replacement. Nothing was thrown away.
- What HTML gave for free that Tk needed written by hand: keyboard
  operation, a visible focus ring, whole-interface text resize, content
  that scrolls instead of silently not being drawn, and a 68ch reading
  column — the measurement the Tk shell reported at ~53 characters and
  could not fix.
- What it does **not** do: make the assistant smarter. Same model, same
  prompts, same answers.

---

## [1.3.0] — 2026-09-01

The accessibility pass. Planned in `docs/ACCESSIBILITY_PLAN.md`, which
also sets out honestly which standards actually bind a personal desktop
tool (none) and which one we hold to anyway (WCAG 2.1 AA, plus the
cognitive criteria added in 2.2).

### Fixed
- **Thirteen controls were never drawn**, including the transcript —
  FB-005. The chrome needed 919px in a 486px window and Tk silently
  stopped mapping children. Verified pre-existing at commit `807c5ba`.
- **Every button was unreachable by keyboard** — FB-006. The real Tab
  ring held 2 widgets of 22. WCAG 2.1.1, Level A.
- `StrataDB` resolved `DB_PATH` as a default argument, so tools that
  redirected it still wrote to the real database — NM-005.

### Added
- **Keyboard operation** for every control, with Return and Space, and a
  visible focus ring whose colour clears 3:1 on every surface it can
  land on (`strata_tools/keyboard.py`).
- **Colour-coded modes** — green, amber and red, each measured against
  the label text at AA. The active mode also carries a bullet and a
  border, so colour is never the only cue (WCAG 1.4.1).
- **App-wide text scaling**: A+/A− now moves 22 widgets instead of 2,
  with the chrome capped at a measured 12pt so growing text cannot
  re-hide controls.
- `strata_tools/layout.py` — content-fits-the-window as a tested kernel;
  `tools/a11y_check.py` and `tools/layout_probe.py` as benches.

### Changed
- The decorative title banner is gone (the window title bar already said
  it) and status moved into the row below — one fewer stacked row.
- The dyslexia-font comment in `strata_console.py` was **corrected**: the
  research does not support the claim it made. The font menu stays,
  because reader *choice* is the intervention that is supported.

### Known
- Reading width is ~53 characters against BDA guidance of 60–80. Short
  rather than long, and reported rather than forced.

---

## [1.2.0] — 2026-09-01

The completion pass. Every capability the console already advertised now
works end to end, and the engineering apparatus that proves it is in
place. Planned in `docs/BUILD_PLAN.md`; the transfer that supplied the
material is catalogued in `docs/TRANSFER_CATALOG.md`.

### Added
- **Clear** — button, `/clear` (and `/new`), or **Ctrl+L**. Empties the
  transcript *and* the context the model recalls. Nothing is deleted: a
  floor is raised in `system_state` and the rows stay in SQLite
  (`strata_tools/session.py`).
- **Spoken punctuation for dictation** — "period", "comma", "question
  mark", "new line", "cap", "caps on/off", "all caps on/off" and the
  rest become real characters, with recogniser collisions resolved
  (`strata_tools/dictation.py`). Listed in `/help`.
- **A speech front end for read-aloud** — markdown stripped, then
  numbers, money, percents, ordinals, years and abbreviations expanded,
  with inline code held atomic (`strata_tools/speech.py`).
- **Continuous integration** — `py_compile` plus the unit suite on
  Windows against Python 3.11 and 3.13, every push and pull request,
  including a degraded-mode import check that proves the console still
  starts with nothing optional installed.
- **A design-law linter** with three rules, each earned by a real
  defect, gated over the whole repository inside the test suite
  (`strata_tools/design_laws.py`).
- **`requirements.txt`** — a documented runtime, carrying the
  two-interpreters warning at the top.
- **Documentation set** — `docs/SCOPE.md`, `docs/BUILD_PLAN.md`,
  `docs/TRANSFER_CATALOG.md`, `docs/FORMER_BUGS.md`, this changelog.
- **Ctrl+A** selects all of whichever box has focus
  (`strata_tools/selection.py`).
- **WCAG contrast audit** of the console's real palette, read from the
  CustomTkinter theme (`strata_tools/wcag.py`).

### Changed
- Window sizing moved from inline arithmetic to a tested kernel
  (`strata_tools/window_fit.py`). **Behaviour is byte-identical** —
  verified at 999×486+30+20 before and after.
- `/status` now counts the threads still in play rather than every row
  ever written, so it agrees with what the model can actually see.

### Fixed
- **Dictation returned unpunctuated text** — FB-003.
- **Read-aloud spoke the markdown** — FB-004.

### Known and accepted
- Two colour pairs miss WCAG AA: the default button at 4.47:1 (against
  4.5 — CustomTkinter's stock theme) and the recording-state red at
  3.77:1. Reported rather than recoloured, with reasons, in
  `wcag.ACCEPTED_SHORTFALLS`. The recording red also changes its label
  to "Stop", so state is not carried by colour alone.

### Decided against
- **`platform_dpi` (DPI awareness)** — declined on measurement, not
  preference. It would drop the window from 91% to 52% of screen width.
  See NM-002; reproduce with `tools/dpi_check.py --aware`.
- **`prompt_coach`, `prompt_archive`, `legibility` presets, the BM25
  retrieval swap, `readability`, `doc_writer`, `stt_command`** — all
  would change the console's design or duplicate Imprint. Recorded in
  `docs/TRANSFER_CATALOG.md` so each is a decision, not an oversight.

---

## [1.1.1] — 2026-08-31

### Fixed
- **The microphone was dead for weeks and the hardware was fine** — the
  launcher was starting a Python without the voice packages installed.
  FB-002. The launcher now prefers an interpreter that carries them, and
  `cscript //nologo launch_strata.vbs /which` reports its choice.

---

## [1.1.0] — 2026-08-23

### Added
- Voice-path bench check (`tools/voice_check.py`) running capture, RAM
  budget and transcription as separate stages.
- Sentinel-style dockable toolbar: 🎤 dictation with Fast/Accurate/Best
  tiers, 🔊 read-aloud with a 🐢/🐇 speed picker, ❓ guided tour.
- Context sources: 🌐 web search, ☁ OneDrive document indexing,
  📎 single-file upload.

### Fixed
- Whisper model loading exhausted RAM alongside Ollama and died inside
  MKL. Each tier's peak working set is now measured and budgeted against
  free RAM, and only one model is ever resident
  (`strata_tools/voice_budget.py`).

---

## [1.0.0] — 2026-07-06

Initial baseline as running on the laptop: the five-stage local-first
NLP pipeline, SQLite context store, operating modes, slash commands, and
dyslexia-friendly reading fonts, answered by a local model via Ollama
with a deterministic template fallback.
