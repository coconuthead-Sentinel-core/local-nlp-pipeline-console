# Prompt Library — Scope & Blueprint

**As of:** 2026-09-17 · **Owner:** Shannon Brian Kelley (Coconut head) · **Status:** BLUEPRINT — no code until owner approval

## Purpose

This document is the blueprint for adding a Prompt Library to Strata Console (browser build): automatic capture of every prompt and reply into an indexed, A1-filed archive the pod assistant reads as long-term memory. Per the owner's standing rule — scope first, no blueprint, no build — no code is written until this document is approved.

It satisfies the documentation gate in three parts: the permanent record (Google Docs/OneDrive copy), this GitHub copy (`docs/PROMPT_LIBRARY_BLUEPRINT.md`), and the pseudocode section below.

## Scope statement

v1 adds one thing: a Prompt Library that records, files, and retrieves past exchanges — nothing else changes.

**In scope**

- Automatic capture: when a pod exchange completes, the prompt, reply, mode, timestamp, and sources used are archived. No user action required.
- Deterministic classification: each exchange is keyword-scored into one of ten fixed categories and given an auto card address (column = category, row = arrival order).
- Retrieval: the library is searched with the console's existing keyword kernel; matched past exchanges ride into the assistant's context labeled as past-conversation memory, with an instruction to flag anything already tried.
- Browsing: a Library view (in the existing Knowledge Base drawer) to read, re-file, delete, and export entries.
- Storage safety: a hard cap, oldest-first pruning with an export offer, and JSON export.
- A `/promptlib` command showing counts, categories, and storage used.

**OUT of scope (v1)**

- Semantic or embedding search — keyword only, stated honestly in the UI.
- Model self-classification of exchanges (possible v2, via the existing tools mechanism).
- Cross-device sync, cloud storage, or any recording while the dashboard is closed.
- Any change to existing stores, modes, recall, or sources.

**Acceptance criteria**

- [ ] Every completed pod exchange appears in the library, categorized and addressed, with no user action.
- [ ] Asking a related question surfaces past exchanges, and the assistant cites them by address.
- [ ] The cap is enforced; pruning never fires without an export offer first.
- [ ] All existing behavior passes the same smoke tests that gated the Knowledge Base build.

**Lifecycle target**: additive v1 on the existing artifact URL, same pattern as the Knowledge Base integration.

## The filing scheme

Ten fixed classes, Dewey-style, each owning one column letter; the row number is arrival order within that class — the third code exchange files at D3, like an index card in a drawer.

| Column | Class | Covers |
| --- | --- | --- |
| A | System & Meta | Strata itself, commands, setup, this dashboard |
| B | Planning & Goals | schedules, milestones, decisions, strategy |
| C | Study & Learning | coursework, reading, flashcards, review |
| D | Code — HTML/CSS | markup, layout, box model, styling |
| E | Code — JavaScript | scripts, DOM, events, browser APIs |
| F | Code — Python & other | desktop app work, tests, any other language |
| G | AI & Prompting | prompts, model behavior, agents, RAG |
| H | Writing & Documents | drafts, READMEs, resumes, documentation |
| I | Finance | budgets, bills, savings tools |
| J | General | anything scoring zero everywhere else |

Each class carries a small keyword lexicon; the exchange text is scored against every lexicon with the console's existing scoring kernel; highest score wins, all-zero falls to J. Honest limits, stated in the UI: keyword filing misfiles sometimes, so every card's class and address stay editable — the machine files, the librarian corrects. A fixed scheme is deterministic, costs no extra model call, and matches how Dewey / Library of Congress systems work: the scheme is stable; only the collection grows.

## Data design & storage policy

The library lives under its own storage key, `strata_promptlib_v1` — isolated from the conversation stores and the Knowledge Base. One record per exchange:

| Field | Type | Notes |
| --- | --- | --- |
| id | string | unique, generated |
| at | ISO 8601 | timestamp of the exchange |
| zone | GREEN / YELLOW / RED | mode active when it ran |
| prompt | string, capped 2,000 chars | the user's input |
| reply | string, capped 4,000 chars | the assistant's output |
| class | A–J + label | assigned by the classifier |
| coord | e.g. D3 | column = class, row = sequence |
| sources | list | what grounded the turn (web, Drive, KB, file) |
| tags | list | empty in v1; schema mirrors the desktop excerpt format |

**Storage policy** — localStorage allows roughly 5 MB per site, shared by everything Strata stores:

- Cap: 400 records or 2.5 MB serialized, whichever comes first.
- At the cap: offer a JSON export, then prune the oldest 10% — export first, prune second, never silently.
- Per-field caps keep any one giant exchange from eating the budget.
- Export uses the same JSON-bundle shape as the Study Workstation.

### Storage tiers — the Drive offload (proposed)

A three-tier memory hierarchy matching the zones — the same shape as cache → RAM → disk:

| Tier | Zone | Where | Speed | Holds |
| --- | --- | --- | --- | --- |
| Hot | GREEN | browser storage (5 MB budget) | instant, every turn | current and recent exchanges |
| Warm | YELLOW | JSON export on the laptop | manual, one click | pruned batches, personal archive |
| Archival | RED | dedicated Google Drive folder | searched on demand via ☁ | long-term memory across months |

- **Already works**: the read-back half is shipped — Strata's ☁ source searches Drive and hands passages to the assistant.
- **Unverified**: the write half. The Drive connector exposes a file-creation tool, so console-side upload is likely possible, but must be verified with one small test before it is promised. Labeled possible, not proven.
- **Guaranteed fallback**: export the batch, drop it into the Drive folder manually — the read-back path does not care who uploaded the file.
- **Clutter control**: the console never writes into personal folders. It owns a fixed tree — `Strata Archive/RED/` — with machine-generated names and the same YAML front-matter the desktop excerpt format uses (doc_id, zone, timestamp, class, coord).

## Pseudocode

```
CAPTURE — runs where the console already finishes a turn
  when an exchange completes with (prompt, reply, zone, sources):
    class  ← CLASSIFY(prompt + " " + reply)
    row    ← count of records already in that class + 1
    coord  ← class.column + row            # e.g. "D" + 3 → D3
    record ← {id, now, zone, prompt[..2000], reply[..4000],
              class, coord, sources, tags: []}
    append record to library; save
    if over cap: offer export, then prune oldest 10%

CLASSIFY — deterministic, no cloud call
  for each class A..I:
    score[class] ← keyword overlap(text, class.lexicon)   # existing kernel
  if all scores are zero: return J (General)
  return class with the highest score

RETRIEVE — runs where the console already gathers sources
  when the user sends a new message:
    hits ← rank library records by shared terms with the message
    take the top few within a character budget
    inject as context, labeled:
      "Past conversations from the user's prompt library —
       check whether this was tried before; if it failed,
       say so and propose a different strategy."
    cite each hit by coord and date in the reply
```

Deliberately NOT here: no background loop, no timer, no write the user didn't cause. Capture fires only on a completed exchange; retrieve fires only on send. The model stays stateless — the page carries all memory.

## The textbook process (ISO/IEC/IEEE 12207 · SWEBOK)

1. **Requirements** — the Scope statement above; sign-off is the owner approving this document.
2. **Design** — the filing scheme, data design, and pseudocode; review is the owner reading this.
3. **Verification planning** — test plan written from the acceptance criteria BEFORE building.
4. **Implementation** — small increments, each traceable to a requirement; additions are logged scope changes, never drift.
5. **Verification** — the build is done when the planned tests pass.
6. **Release & configuration management** — version, CHANGELOG, publish, mirrors synced as exact clones.
7. **Documentation ships WITH the release** — updated docs are part of the definition of done for the same increment.

## Prep-work checklist

- [ ] Catch-up documentation: update Strata's README and CHANGELOG for the shipped Knowledge Base.
- [ ] File this blueprint: `docs/PROMPT_LIBRARY_BLUEPRINT.md` in the repo + Google Docs/OneDrive record.
- [ ] Write the test plan: one smoke-test step per acceptance checkbox + KB regression steps.
- [ ] Freeze the scope: owner approves; later additions are logged scope changes.
- [ ] Build in small increments — store, classifier, capture, retrieve, UI, command.
- [ ] Release with docs: README, CHANGELOG, and blueprint status in the same increment; sync mirrors.

Open question for the owner: does the ten-class scheme match how you think about your work, or should any drawer be renamed, split, or merged before it is frozen?
