# Open decisions — Strata Console

Decisions that are the **owner's** to make, recorded here so they are not
lost, not quietly decided by whoever touches the repo next, and not
mistaken for work nobody has noticed.

A decision leaves this file in one of two ways: the owner makes it, and
it moves to `docs/SCOPE.md` §6 as a logged change; or it is found moot,
and the row says so with the date.

Opened 2026-10-17.

---

## OD-001 — Prompt Library v1 exists on a branch that cannot be merged

**Status:** open, awaiting owner decision · **Opened:** 2026-10-17
**Blocks:** deleting branch `claude/zealous-babbage-m6ltou`; closing
[PR #2](https://github.com/coconuthead-Sentinel-core/local-nlp-pipeline-console/pull/2)

### What exists

PR #2 is open and carries two commits that `main` does not have:

| Commit | What it is |
| --- | --- |
| `f896f3d` | `feat(browser): Prompt Library v1 — capture, classify, retrieve, /promptlib` |
| `1611f95` | `fix(promptlib): close review-round findings from Copilot on PR #2` |

It is a real implementation of the feature blueprinted in
[`docs/PROMPT_LIBRARY_BLUEPRINT.md`](PROMPT_LIBRARY_BLUEPRINT.md) — about
350 lines added to `strata_console_browser.html`, plus a round of review
fixes. It is not a sketch, and it is the **only** copy.

### Why it cannot simply be merged

The two sides forked, and the fork is in the same file:

| | `strata_console_browser.html` | Prompt Library | Avatar · Omega-1 · Sheets · glyph keyboard |
| --- | --- | --- | --- |
| `main` | 232,016 bytes | **absent** | **present** |
| PR #2 | 124,219 bytes | **present** (35 references) | **absent** |

The merge base is `7c34caf`. PR #2 was built on the snapshot filed
2026-09-17 (108,563 bytes). Independently, the published Artifact itself
was developed from 2026-09-18 to 2026-09-21 — images, the Avatar
Visualizer, Omega-1, the export bridge, the H5 build, the glyph keyboard,
Strata Sheets — and on 2026-10-17 `main`'s snapshot was re-filed from
that live page.

So merging PR #2 would replace a file that **mirrors the published
Artifact** with one that is four days of browser work behind it. The
repo's integrity claim — byte count and SHA256 in `CHANGELOG.md`, the
thing that lets a reader check the snapshot against the real page —
would become false. That claim has already failed once (FB-013's
sibling: a stale snapshot that looked like a record), and the fix cost
more than the original work.

### The thing that actually decides it

**The published Artifact has no Prompt Library.** A search of the
2026-09-21 page returns zero references. The browser build is edited
*where it is published*, so the Artifact is the source and the file in
this repo is a dated snapshot of it — never the other way round.

That means PR #2's code never reached the product. It is an
implementation that exists only as a diff against an old snapshot of a
page that has since moved on.

### The options, honestly

1. **Carry the feature forward into the live Artifact.** Treat PR #2 as
   a design and a reference implementation, re-apply the Prompt Library
   to the *current* browser build where it is published, then re-file the
   snapshot and close PR #2 as superseded. Costs the most work; is the
   only route that ends with the feature actually shipped. The blueprint
   and the reviewed code both survive to guide it.
2. **Close PR #2 and keep the branch as the record.** Decide the Prompt
   Library is not wanted in the browser build for now. The branch stays
   on GitHub as the archive, the blueprint keeps its `BLUEPRINT` status,
   and nothing is deleted. Costs nothing; ships nothing.
3. **Merge it.** Not recommended, and recorded only so the option is not
   silently missing: it would ship the Prompt Library code into the
   snapshot while reverting the snapshot's fidelity to the published
   page. The repo would then describe a browser build that does not
   exist in either place.

### What must not happen

**The branch must not be deleted while this is open.** It holds the only
copy of `f896f3d` and `1611f95`. A deleted branch's commits are
unreachable and GitHub will garbage-collect them. If the decision is
option 2, the branch is the archive and stays; if option 1, the branch is
the reference and stays until the work lands.

---

## Branch state while OD-001 is open

| Branch | Why it exists | Deletable? |
| --- | --- | --- |
| `main` | the trunk | no |
| `forge-work` | the git worktree at `Desktop\.claude\worktrees\strata` is checked out on it | no, not while that worktree exists |
| `claude/zealous-babbage-m6ltou` | holds PR #2 — see OD-001 | **no**, holds unmerged work |

Every branch in this repository is accounted for. None is a leftover.
