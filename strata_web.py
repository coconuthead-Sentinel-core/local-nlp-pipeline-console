#!/usr/bin/env python3
"""Strata Console — the web shell. Same engine, different front end.

A second shell over ``strata_core``, rendered as HTML and CSS inside a
native window (pywebview on Edge WebView2, which Windows already has).
Nothing about the engine changes, and ``strata_console.py`` is untouched
and still shipped: this exists to be compared against, not to replace it
before it has earned the job.

**Still local-first.** No server is exposed and no port is opened to the
network — pywebview loads the page from disk and talks to Python through
its own bridge. The model is the same Ollama daemon on loopback.

Why it is worth trying, in one line each — every item is something the
Tk shell needed hand-written Python to achieve, measured across the
accessibility work of 2026-09-01/02:

  * keyboard operation      a ``<button>`` is focusable; no module needed
  * visible focus           ``:focus-visible``, built in
  * text resize             one CSS variable instead of walking widgets
  * nothing silently hidden CSS overflows and scrolls; it never stops
                            drawing a control the way Tk's packer does
  * reading width           ``max-width: 68ch``, the thing measured at 53
                            characters and left unfixed in the Tk shell
  * markdown                rendered, rather than stripped before speech

What this shell does NOT do is make the assistant smarter. Same model,
same prompts, same answers — this is about whether they can be read.

Run it:  py -3 strata_web.py
"""

import os
import threading
from datetime import datetime
import time

import webview

from strata_core import ALL_GLYPHS, StrataPipeline
from strata_tools import (codex, commands, context_sources, dictation,
                          single_instance,
                          focus,
                          session,
                          speech)

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "web", "index.html")


def nl_join(lines):
    """Join rendered markdown lines. Here so the f-strings above stay flat."""
    return "\n".join(lines)

class Api:
    """The bridge the page calls. One method per thing the UI can ask.

    Every method returns a plain dict so the boundary stays JSON and the
    page never holds a Python object. Errors come back as data rather
    than exceptions, because an exception across this bridge surfaces in
    the page as a silent rejected promise -- the web equivalent of a
    control that does nothing.
    """

    def __init__(self):
        self.pipeline = StrataPipeline()
        self._lock = threading.Lock()
        # Set in main() once the window exists. The file dialog is the
        # one thing here that must ask the native window rather than the
        # page: a browser <input type=file> hands back a sandboxed blob
        # with no path, and the indexer needs the real file.
        self.window = None
        # --- context sources -------------------------------------------
        # State lives on the bridge, not in the page, so it survives a
        # reload and so the rule deciding what the model reads stays in
        # one testable place (strata_tools/context_sources.py).
        self._sources = {"web": False, "onedrive": False}
        self._attachment = None
        self._onedrive_index = None      # None = never built / building
        self._onedrive_building = False
        self._notes = []
        self._note_lock = threading.Lock()
        self._rec_stream = None
        self._rec_frames = []
        self._whisper_model = None
        self._whisper_tier = None
        self._whisper_used_at = None
        # --- focus cycles (ticket 5b) ----------------------------------
        # The open cycle lives on the bridge, not in the page, for the
        # same reason the sources do: it survives a reload, and the rule
        # that there is only ever ONE open cycle stays in one place. The
        # engine also owns the clock -- both timestamps on a row come
        # from here, so a cycle can never record a negative length.
        self._open_cycle = None
        self._focus_session = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self._start_warmup()
        # Same idle-release policy as the desktop shell, and for the same
        # measured reason: the model holds ~174 MB and releasing returns
        # ~221 MB on a machine that lives at 400-600 MB free. A timer
        # rather than Tk's after(), but the kernel deciding is identical.
        self._start_memory_watch()

    # --- state ------------------------------------------------------------
    def bootstrap(self):
        """Everything the page needs on load."""
        db = self.pipeline.db
        return {
            "status": self.pipeline.get_status(),
            "zone": self.pipeline.current_zone,
            "brain": bool(self.pipeline.brain.available),
            "model": getattr(self.pipeline.brain, "model", ""),
            "error": getattr(self.pipeline.brain, "last_error", "") or "",
            "fontFamily": db.get_state("web_font", "system"),
            "fontSize": int(db.get_state("web_font_size", "17") or 17),
            "autoread": db.get_state("autoread", "0") == "1",
            "tokens": [dict(t) for t in ALL_GLYPHS],
            "sources": dict(self._sources),
            "attachment": self._attachment_view(),
        }

    def set_pref(self, key, value):
        allowed = {"web_font", "web_font_size", "autoread"}
        if key not in allowed:
            return {"ok": False, "error": f"unknown preference {key!r}"}
        self.pipeline.db.set_state(key, str(value))
        return {"ok": True}

    # --- context sources: web, OneDrive, uploaded document ----------------
    #
    # The model never reaches any of these. The shell fetches text and
    # hands it in as context, which is what keeps "local-first" true
    # while still letting the assistant answer from the open web and
    # from the owner's own documents.
    #
    # Both the attachment and the OneDrive index outlive the turn, on
    # purpose: the point is to keep talking ABOUT the material, so a
    # file uploaded once stays readable until it is removed.

    def _push_note(self, text):
        """Queue a line for the page to collect on its next poll."""
        if not text:
            return
        with self._note_lock:
            self._notes.append(text)

    def _attachment_view(self):
        """What the page is allowed to know about the upload: never the
        text itself, which can be two million characters."""
        att = self._attachment
        if not att:
            return None
        return {"name": att["name"],
                "label": context_sources.attachment_label(
                    att["name"], len(att["text"]))}

    def set_source(self, name, on):
        """Turn 🌐 web search or ☁ OneDrive files on or off."""
        if name not in self._sources:
            return {"ok": False, "error": f"unknown source {name!r}"}
        self._sources[name] = bool(on)
        if name == "onedrive" and self._sources[name]:
            self._ensure_onedrive_index()
        return {"ok": True, "sources": dict(self._sources)}

    def _ensure_onedrive_index(self):
        """Build the index once, off the bridge thread.

        Indexing a whole OneDrive takes minutes the first time and
        seconds afterwards. It runs in the background and reports
        through the note queue, because a bridge call that blocks for
        four minutes is indistinguishable from a hung window.
        """
        if self._onedrive_index is not None or self._onedrive_building:
            return
        self._onedrive_building = True
        self._push_note("☁ Indexing your OneDrive files — the first time "
                        "can take a few minutes; after that it's cached.")

        def work():
            from strata_tools import doc_index
            try:
                cache = os.path.join(doc_index.cache_dir(),
                                     "onedrive_index.json")
                idx = doc_index.build_index_over(doc_index.onedrive_root(),
                                                 cache)
                self._onedrive_index = idx
                note = f"☁ OneDrive ready — {len(idx)} files searchable."
            except Exception as e:
                # An empty list, not None: the difference between "found
                # nothing" and "still working" is what the owner is told.
                self._onedrive_index = []
                note = f"☁ OneDrive indexing failed: {type(e).__name__}: {e}"
            self._onedrive_building = False
            self._push_note(note)

        threading.Thread(target=work, daemon=True).start()

    def upload_document(self):
        """Open the native file dialog and attach what it returns.

        The dialog is the window's, not the page's: an HTML file input
        yields a sandboxed blob with no path, and every extractor in
        ``doc_index`` reads from a path. Borrowing the native dialog is
        cheaper and more honest than rebuilding the extractors in
        JavaScript.
        """
        if self.window is None:
            return {"ok": False,
                    "error": "The window is not ready yet — try again in "
                             "a moment."}
        spec = ";".join("*" + e for e in context_sources.UPLOAD_EXTENSIONS)
        # pywebview renamed this constant: FileDialog.OPEN is current and
        # OPEN_DIALOG is deprecated with a removal promised. Ask for the
        # new name and fall back, so the upgrade that removes the old one
        # does not take the upload button with it.
        open_dialog = getattr(getattr(webview, "FileDialog", None), "OPEN",
                              None)
        if open_dialog is None:
            open_dialog = webview.OPEN_DIALOG
        try:
            picked = self.window.create_file_dialog(
                open_dialog, allow_multiple=False,
                file_types=(f"Readable files ({spec})", "All files (*.*)"))
        except Exception as e:
            return {"ok": False,
                    "error": f"Could not open the file dialog: "
                             f"{type(e).__name__}: {e}"}
        if not picked:
            return {"ok": True, "cancelled": True}

        path = picked[0] if isinstance(picked, (list, tuple)) else picked
        from strata_tools.doc_index import extract_text
        name = os.path.basename(path)
        try:
            text = extract_text(path) or ""
        except Exception:
            text = ""
        if not text.strip():
            return {"ok": False, "cancelled": False,
                    "error": context_sources.unreadable_note(name)}

        self._attachment = {
            "name": name,
            "text": text[:context_sources.MAX_ATTACHMENT_CHARS],
        }
        return {"ok": True,
                "attachment": self._attachment_view(),
                "message": context_sources.attachment_greeting(name)}

    def clear_attachment(self):
        if self._attachment is None:
            return {"ok": True, "attachment": None, "message": ""}
        self._attachment = None
        return {"ok": True, "attachment": None,
                "message": "📎 Attachment removed."}

    # --- the local model's readiness ---------------------------------------
    #
    # Measured on this laptop: a cold first reply takes ~20 seconds while
    # Ollama reads 2.3 GB into RAM with no GPU; once resident, replies
    # take ~3 seconds. The model is dropped again after keep_alive, so
    # the 20 seconds comes back on its own.
    #
    # Neither number is a defect. Showing a static "thinking…" for
    # twenty seconds is: a wait with no evidence of progress cannot be
    # told apart from a hang, and the owner reasonably read it as the
    # app failing to start.

    def _start_warmup(self):
        """Load the model in the background at startup.

        The cold load cannot be avoided; charging it to the first thing
        the owner types can. This runs while he is still reading the
        opening message, and reports through the same note queue as
        everything else.
        """
        def work():
            brain = self.pipeline.brain
            try:
                if not brain.available:
                    return
                # Budget first. Measured 2026-09-02: 2.9 s per reply with
                # 978 MB free, 103.5 s with 475 MB free, same code. On a
                # starved machine the warm-up load is what freezes the
                # window, so it is skipped and the owner is told why, in
                # numbers -- same discipline as the voice model (FB-002).
                from strata_tools import model_budget, voice_budget
                _total, free = voice_budget.free_ram_mb()
                budget = model_budget.plan(free, brain.size_bytes,
                                           brain.model)
                if budget["starved"]:
                    self._push_note(budget["note"])
                    return
                if brain.is_loaded():
                    return
                self._push_note("🧠 Warming the local model — about 20 "
                                "seconds, once. You can type now; the "
                                "first reply will wait for this.")
                if brain.warm():
                    self._push_note("🧠 Model ready — replies take about "
                                    "three seconds now.")
                else:
                    self._push_note(f"🧠 The model did not load: "
                                    f"{brain.last_error}")
            except Exception as e:
                self._push_note(f"🧠 Model warm-up failed: "
                                f"{type(e).__name__}: {e}")

        threading.Thread(target=work, daemon=True).start()

    def model_state(self):
        """Whether a reply will be fast, will wait for a load, or will
        crawl because the machine has no room for the model."""
        brain = self.pipeline.brain
        try:
            loaded = bool(brain.is_loaded())
        except Exception:
            loaded = False
        try:
            from strata_tools import model_budget, voice_budget
            _total, free = voice_budget.free_ram_mb()
            budget = model_budget.plan(free, brain.size_bytes, brain.model)
        except Exception:
            free, budget = 0, {"starved": False, "note": ""}
        return {"ok": True, "available": bool(brain.available),
                "loaded": loaded, "freeMb": free,
                "starved": bool(budget["starved"]),
                "note": budget["note"]}

    def busy_for(self, text):
        """The status line to show while this turn runs.

        Asked of Python rather than decided in JavaScript so that the
        rule for 'did this message ask for a search' exists exactly
        once. A second copy in the page would answer differently the
        first time either was edited.
        """
        use_web = context_sources.wants_web(text or "", self._sources["web"])
        brain = self.pipeline.brain
        try:
            loading = bool(brain.available) and not brain.is_loaded()
        except Exception:
            loading = False
        return {"ok": True,
                "loading": loading,
                "label": context_sources.busy_label(
                    use_web, self._sources["onedrive"],
                    self._attachment is not None,
                    model_loading=loading)}

    # --- commands ---------------------------------------------------------
    def run_command(self, text):
        """Execute a slash command. Returns None-ish when it is not one.

        Kept separate from ``send`` so the page can tell the difference
        without knowing the grammar. ``handled: False`` means "this was
        an ordinary message, send it to the model" -- the one answer
        that must never be confused with "I did not recognise it",
        because an unrecognised command silently answered by the model
        looks exactly like the console working.
        """
        parsed = commands.parse(text)
        if parsed is None:
            return {"ok": True, "handled": False}

        name = parsed["name"]
        if not parsed["known"]:
            return {"ok": True, "handled": True,
                    "message": commands.unknown_message(text),
                    "bad": True}

        if name == "status":
            return {"ok": True, "handled": True,
                    "message": self.pipeline.get_status(),
                    "status": self.pipeline.get_status()}

        if name == "lexicon":
            return {"ok": True, "handled": True, "markdown": True,
                    "message": commands.lexicon_text(ALL_GLYPHS)}

        if name == "help":
            return {"ok": True, "handled": True, "markdown": True,
                    "message": commands.help_text()}

        if name == "clear":
            out = self.clear()
            out["handled"] = True
            out["clearLog"] = True
            return out

        if name == "focus":
            argument = (parsed["argument"] or "").strip().lower()
            if argument in ("stats", "summary", "report"):
                out = self.focus_summary()
                out["handled"] = True
                return out
            if argument in ("stop", "close", "end"):
                out = self.focus_close(ran_to_end=False)
                out["handled"] = True
                return out
            if not argument:
                state = self.focus_state()
                if state.get("open"):
                    state["message"] = (
                        f"{state['display']} left of "
                        f"{state['plannedMinutes']} minutes. "
                        f"/focus stop closes it.")
                else:
                    lengths = " | ".join(str(n) for n in focus.LENGTHS)
                    state["message"] = (f"No cycle open. /focus "
                                        f"{lengths} starts one.")
                state["handled"] = True
                return state
            if not argument.isdigit():
                lengths = " | ".join(str(n) for n in focus.LENGTHS)
                return {"ok": True, "handled": True, "bad": True,
                        "message": (f"How long? /focus {lengths}, "
                                    f"or /focus stop.")}
            out = self.focus_start(int(argument))
            out["handled"] = True
            return out
        if name == "keys":
            argument = (parsed["argument"] or "").strip().lower()
            shut = argument in ("close", "hide", "off")
            kb = self.codex_keyboard()
            kb["handled"] = True
            kb["openKeyboard"] = not shut
            kb["message"] = ("Glyph keyboard closed."
                             if shut else
                             "Glyph keyboard open. Keys type into "
                             "the message box, so everything else "
                             "sees one kind of message.")
            return kb

        if name == "mode":
            argument = parsed["argument"]
            if not argument:
                return {"ok": True, "handled": True, "bad": True,
                        "message": "Which mode? Try /mode green, "
                                   "/mode yellow or /mode red."}
            out = self.change_zone(argument)
            out["handled"] = True
            return out

        # Unreachable while COMMANDS and this dispatch agree -- and a
        # test asserts they do, so this is a guard, not a code path.
        return {"ok": True, "handled": True, "bad": True,
                "message": commands.unknown_message(text)}

    # --- focus cycles and experience sampling (ticket 5b) -----------------
    # Rules live in strata_tools/focus.py; storage in StrataDB. These four
    # methods move data between them and hold the one piece of state that
    # cannot be pure: which cycle is open right now.

    def _now(self):
        """The single clock. Both ends of a row are stamped here."""
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def focus_state(self):
        """What the page needs to draw the timer, including after a reload.

        ``elapsed`` is computed here rather than in the page so the
        countdown survives a reload mid-cycle: the page can be reopened
        and still show the right remaining time, because it is derived
        from the stored start rather than from when the script began.
        """
        if not self._open_cycle:
            return {"ok": True, "open": False,
                    "lengths": list(focus.LENGTHS),
                    "modes": list(focus.MODES)}
        started = self._open_cycle["started_at"]
        try:
            elapsed = (datetime.now()
                       - datetime.strptime(started, "%Y-%m-%dT%H:%M:%S")
                       ).total_seconds()
        except ValueError:
            elapsed = 0
        left = focus.remaining_seconds(
            self._open_cycle["planned_minutes"], elapsed)
        return {"ok": True, "open": True,
                "id": self._open_cycle["id"],
                "plannedMinutes": self._open_cycle["planned_minutes"],
                "remaining": left,
                "display": focus.format_remaining(left),
                "expired": left == 0,
                "lengths": list(focus.LENGTHS),
                "modes": list(focus.MODES)}

    def focus_start(self, minutes):
        """Open a cycle. Persists BEFORE it ticks.

        A timer counting down with no row behind it is a control that
        does nothing -- the owner would find out fifteen minutes later,
        with the work done and the record missing. So the write happens
        first and its failure is reported immediately.
        """
        if self._open_cycle:
            return {"ok": False, "bad": True,
                    "message": focus.start_refusal(self._open_cycle)}
        try:
            cycle = focus.new_cycle(self._focus_session, int(minutes),
                                    self._now())
        except (ValueError, TypeError) as exc:
            return {"ok": False, "bad": True, "message": str(exc)}
        try:
            cycle_id = self.pipeline.db.save_cycle(cycle)
        except Exception as exc:                       # pragma: no cover
            return {"ok": False, "bad": True,
                    "message": f"The cycle could not be saved, so the "
                               f"timer did not start: {exc}"}
        if not cycle_id:                               # pragma: no cover
            return {"ok": False, "bad": True,
                    "message": "The cycle did not persist, so the timer "
                               "did not start."}
        cycle["id"] = cycle_id
        self._open_cycle = cycle
        state = self.focus_state()
        state["message"] = (f"Cycle open: {cycle['planned_minutes']} "
                            f"minutes. Recording.")
        state["prompt"] = focus.report_prompt("START")
        state["phase"] = "START"
        return state

    def focus_close(self, ran_to_end=False):
        """Close the open cycle. Replaces the row; never adds a second."""
        if not self._open_cycle:
            return {"ok": False, "bad": True,
                    "message": "No cycle is open."}
        cycle_id = self._open_cycle["id"]
        stored = [c for c in self.pipeline.db.cycles()
                  if c.get("id") == cycle_id]
        base = stored[0] if stored else self._open_cycle
        try:
            closed = focus.close_cycle(base, self._now(), bool(ran_to_end))
        except ValueError as exc:                      # pragma: no cover
            return {"ok": False, "bad": True, "message": str(exc)}
        self.pipeline.db.save_cycle(closed)
        self._open_cycle = None
        return {"ok": True, "open": False,
                "id": cycle_id,
                "message": focus.closing_note(closed),
                "prompt": focus.report_prompt("END"),
                "phase": "END",
                "lengths": list(focus.LENGTHS),
                "modes": list(focus.MODES)}

    def focus_report(self, cycle_id, phase, load, mode=None, note=None):
        """Store one sample. Skipping never reaches here, by design.

        The kernel raises on a load off the scale and this does NOT
        swallow it: a silently dropped report would be a control that
        appears to work and records nothing.
        """
        try:
            report = focus.new_report(int(cycle_id), phase, int(load),
                                      mode=mode or None,
                                      note=(note or None))
        except (ValueError, TypeError) as exc:
            return {"ok": False, "bad": True, "message": str(exc)}
        self.pipeline.db.save_report(report)
        said = f"Recorded: you reported {report['reported_load']} of 10"
        if report["mode"]:
            said += f", working {report['mode']}"
        return {"ok": True, "message": said + "."}

    # --- the glyph keyboard (ticket 6) ------------------------------------
    # codex.py holds the vocabulary and reads_as() the grammar. The panel
    # TYPES INTO the message box a hardware keyboard types into -- one
    # input path, never two, so everything downstream (commands, the
    # pipeline, dictation polish) sees one kind of message.

    def codex_keyboard(self):
        """Everything the panel needs to draw itself."""
        rows = [[codex.display(code) for code in row]
                for row in codex.keyboard_rows(5)]
        return {"ok": True, "rows": rows,
                "actions": [dict(a) for a in codex.ACTIONS]}

    def codex_reads(self, codes, zone=None):
        """The sequence bar: what the chain says, in English.

        Also returns the peak load and any code the codex does not know,
        because a key that types an unrecognised token and says nothing
        is the silent-decline defect this shop names.
        """
        picked = [c for c in (codes or []) if c]
        return {"ok": True,
                "sentence": codex.reads_as(picked, zone or None),
                "peakLoad": codex.peak_load(picked),
                "unknown": codex.unknown_codes(picked)}

    # --- what the recorded cycles say (ticket 7) --------------------------

    def focus_summary(self):
        """The kernel's analytics over the stored rows, as markdown.

        Six analysis functions shipped on 2026-10-15 and nothing
        displayed them: the owner could record cycles but never see what
        they said, which is a kernel with no control attached -- the same
        gap tickets 5a and 5b closed at the other end.

        Every figure is labelled as a REPORT, and the day-type comparison
        carries the kernel's own observed_not_caused flag as a written
        caveat. An N-of-1 observational record cannot establish cause,
        and a table that lets the owner forget that is a defect under
        SCOPE.md section 3.
        """
        db = self.pipeline.db
        cycles, reports, days = db.cycles(), db.reports(), db.days()
        if not cycles:
            return {"ok": True, "markdown": True,
                    "message": ("No cycles recorded yet. Start one with "
                                "the Focus control or `/focus 15`.")}

        lines = ["### What your cycles say", ""]
        rate = focus.completion_rate(cycles)
        closed = [c for c in cycles if c.get("outcome")]
        lines.append(f"- **{len(cycles)} cycles** recorded, "
                     f"{len(closed)} closed.")
        if rate is not None:
            lines.append(f"- **{round(rate * 100)}%** ran to the end.")

        by_len = focus.cycle_length_report(cycles)
        if by_len:
            lines += ["", "| Length | Closed | Ran to the end |",
                      "| --- | --- | --- |"]
            for row in by_len:
                pct = row["completion_rate"]
                shown = "-" if pct is None else f"{round(pct * 100)}%"
                lines.append(f"| {row['planned_minutes']} min "
                             f"| {row['closed']} | {shown} |")

        best = focus.best_cycle_length(cycles)
        lines.append("")
        if best is None:
            lines.append("- No length has enough closed cycles yet to "
                         "say which one you finish most often. That is "
                         "the honest answer, not a missing number.")
        else:
            lines.append(f"- You finish **{best}-minute** cycles most "
                         f"often, of the lengths tried enough times to "
                         f"compare.")

        ids = [c["id"] for c in cycles if c.get("id") is not None]
        load = focus.load_by_phase(ids, reports)
        if load["reports"]:
            start, end = (load["mean_reported_load_start"],
                          load["mean_reported_load_end"])
            lines += ["", f"- **{load['reports']} reports.** Mean "
                      f"*reported* load: "
                      f"{'-' if start is None else start} at the start, "
                      f"{'-' if end is None else end} at the end."]
            if load["mean_change"] is not None:
                lines.append(f"- Mean change across a cycle: "
                             f"**{load['mean_change']:+}**.")

        rows = focus.compare_by_day_type(cycles, reports, days)
        # A day type with no cycles comes back as a SHORT row -- day_type,
        # cycles and a note, with no completion_rate -- and the kernel
        # always emits one row per type, so "more than one row" was always
        # true and told us nothing. Compare only the types that actually
        # have cycles, and show the table only when two of them do: a
        # comparison against an empty column is not a comparison.
        rows = [r for r in rows if r.get("cycles")]
        if len(rows) > 1:
            lines += ["", "| Day | Cycles | Ran to the end | Reported load (end) |",
                      "| --- | --- | --- | --- |"]
            for r in rows:
                pct = r["completion_rate"]
                shown = "-" if pct is None else f"{round(pct * 100)}%"
                end = r["mean_reported_load_end"]
                lines.append(f"| {r['day_type'].title()} | {r['cycles']} "
                             f"| {shown} | {'-' if end is None else end} |")
            lines += ["", "> These are **observed differences, not "
                      "causes.** A work day differs from a rest day in "
                      "more ways than one record can separate -- sleep "
                      "among them -- so this says what happened, never "
                      "why."]

        problems = focus.validate(cycles, reports, days)
        if problems:
            lines += ["", "**The record has structural problems:**"]
            lines += [f"- {p}" for p in problems[:5]]

        lines += ["", "*Every load figure is what you reported at the "
                  "time, not a measurement of cognitive load.*"]
        return {"ok": True, "markdown": True,
                "message": nl_join(lines)}

    # --- conversation -----------------------------------------------------
    def send(self, text):
        """Run one message through the engine. Blocking; called off the UI."""
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "empty message"}

        # Gather grounding text BEFORE the model runs. Typing "look this
        # up" turns the web on for the turn without touching the box --
        # a request that is understood but not acted on reads as the app
        # ignoring him.
        use_web = context_sources.wants_web(text, self._sources["web"])
        use_onedrive = self._sources["onedrive"]
        web_text = ""
        if use_web:
            from strata_tools.web_search import web_search_context
            web_text = web_search_context(text)
        extra = context_sources.gather(
            text, attachment=self._attachment,
            onedrive_index=self._onedrive_index,
            use_onedrive=use_onedrive, web_text=web_text)

        used = []
        if self._attachment:
            used.append("📎 " + self._attachment["name"])
        if use_onedrive:
            used.append("☁ OneDrive")
        if use_web:
            used.append("🌐 web")

        with self._lock:
            try:
                out = self.pipeline.process_input(text, extra_context=extra)
            except Exception as e:
                return {"ok": False,
                        "error": f"{type(e).__name__}: {e}"}
        reply = out.get("response") or " ".join(
            str(out.get(k, "")) for k in ("summary", "description", "comments")
            if out.get(k))
        return {
            "ok": True,
            "reply": reply,
            "closing": out.get("closing", ""),
            "status": self.pipeline.get_status(),
            "speakable": speech.speakable(reply),
            # What was actually consulted, so the owner can see whether
            # a search happened rather than inferring it from the wait.
            "used": used,
        }

    def change_zone(self, zone):
        result = self.pipeline.change_zone(zone)
        return {"ok": True, "message": result,
                "zone": self.pipeline.current_zone,
                "status": self.pipeline.get_status()}

    def clear(self):
        """Same contract as the Tk shell: archive, never delete."""
        cleared = self.pipeline.db.raise_memory_floor()
        archived = self.pipeline.db.archived_thread_count()
        return {"ok": True,
                "message": session.clear_report(cleared, archived),
                "status": self.pipeline.get_status()}

    # --- voice ------------------------------------------------------------
    def polish_dictation(self, raw):
        """Spoken punctuation into characters -- the shared kernel."""
        return {"ok": True, "text": dictation.polish(raw or "")}

    def speakable(self, raw):
        """Markdown out, numbers spelled out, for the page's own TTS."""
        return {"ok": True, "text": speech.speakable(raw or "")}

    def speakable_batch(self, sentences):
        """Speakable form of each sentence, in order. One bridge call.

        Read-along needs the SPOKEN text and the DISPLAYED text to stay
        aligned sentence for sentence, so the page splits the rendered
        text (which is what the reader actually sees) and asks here for
        each piece's spoken form. Splitting in Python and rendering in
        JavaScript would give two different sentence counts the first
        time an abbreviation appeared, and the highlight would drift.

        ``matches`` tells the page whether a sentence is spoken exactly
        as written. When it is, word-level highlighting can trust the
        speech engine's character offsets; when the text was expanded
        ("$32" -> "thirty-two dollars") those offsets point into a
        different string, so the page falls back to highlighting the
        sentence only rather than lighting up the wrong word.
        """
        out = []
        for raw in (sentences or []):
            text = str(raw or "")
            spoken = speech.speakable(text)
            out.append({"spoken": spoken,
                        "matches": spoken.strip() == text.strip()})
        return {"ok": True, "sentences": out}

    # --- dictation --------------------------------------------------------
    #
    # Capture and transcription stay in Python: the microphone work, the
    # Whisper RAM budgeting and the interpreter rule were all hard-won
    # (FB-002), and re-solving them in JavaScript to save a bridge call
    # would be throwing away the most expensive lessons in the project.
    # The browser is asked only to draw the button.

    def _start_memory_watch(self):
        """Check once a minute whether the voice model should be dropped."""
        def tick():
            try:
                from strata_tools import voice_budget as vb
                if self._whisper_model is not None and self._whisper_used_at:
                    idle = time.monotonic() - self._whisper_used_at
                    _total, free = vb.free_ram_mb()
                    if vb.should_release(idle, free):
                        self._whisper_model = None
                        self._whisper_tier = None
                        self._whisper_used_at = None
                        import gc
                        gc.collect()
                        self._push_note(vb.release_reason(idle, free))
            except Exception:
                pass
            timer = threading.Timer(60.0, tick)
            timer.daemon = True      # never hold the app open
            timer.start()
        timer = threading.Timer(60.0, tick)
        timer.daemon = True
        timer.start()

    def poll_notes(self):
        """Everything the background work wants to tell the page, once.

        Polled rather than pushed, because a background thread reaching
        into the DOM is a race and none of this is urgent enough to be
        worth one. Two producers share the queue: the voice-model
        release watch above, and OneDrive indexing.

        This replaces ``memory_note``, which no page ever called -- the
        release note it returned could not reach the owner, so the
        memory watch was doing real work and reporting it to nobody.
        """
        with self._note_lock:
            notes, self._notes = self._notes, []
        try:
            from strata_tools import voice_budget as vb
            _total, free = vb.free_ram_mb()
        except Exception:
            free = 0
        return {"ok": True, "notes": notes, "freeMb": free}

    def start_recording(self):
        if self._rec_stream is not None:
            return {"ok": False, "error": "already recording"}
        try:
            import sounddevice as sd
        except Exception as e:
            from strata_tools import interpreter as interp
            executable, missing = interp.current_report()
            return {"ok": False,
                    "error": interp.explain_missing(executable, missing or
                                                    ["sounddevice"])}
        self._rec_frames = []
        try:
            info = sd.query_devices(kind="input")
            self._rec_device = str(info["name"]).strip()
        except Exception:
            self._rec_device = "the microphone"
        try:
            self._rec_stream = sd.InputStream(
                samplerate=16000, channels=1, dtype="float32",
                callback=lambda indata, frames, t, status:
                    self._rec_frames.append(indata.copy()))
            self._rec_stream.start()
        except Exception as e:
            self._rec_stream = None
            return {"ok": False,
                    "error": f"Could not open the microphone: {e}"}
        return {"ok": True, "device": self._rec_device}

    def stop_recording(self, tier="Fast"):
        """Stop, transcribe, and return punctuated text."""
        stream, self._rec_stream = self._rec_stream, None
        if stream is None:
            return {"ok": False, "error": "not recording"}
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
        frames, self._rec_frames = self._rec_frames, []
        if not frames:
            return {"ok": False, "error": "nothing was captured"}
        try:
            import gc

            import numpy as np

            from strata_tools import voice_budget as vb
            audio = np.concatenate(frames)[:, 0]
            level = float(np.sqrt((audio ** 2).mean()))

            wanted = tier if tier in vb.TIER_MODELS else "Fast"
            _total, free = vb.free_ram_mb()
            chosen, note = vb.plan_tier(free, wanted)
            if chosen is None:
                return {"ok": False, "error": note}
            if self._whisper_tier != chosen:
                self._whisper_model = None
                self._whisper_tier = None
                gc.collect()
                from faster_whisper import WhisperModel
                try:
                    self._whisper_model = WhisperModel(
                        vb.TIER_MODELS[chosen], device="cpu",
                        compute_type="int8")
                except (MemoryError, RuntimeError) as e:
                    self._whisper_model = None
                    gc.collect()
                    return {"ok": False,
                            "error": f"The {chosen} voice model would not "
                                     f"fit in RAM ({free} MB free). Close "
                                     f"Ollama, or pick Fast. "
                                     f"[{type(e).__name__}]"}
                self._whisper_tier = chosen
            self._whisper_used_at = time.monotonic()
            segments, _info = self._whisper_model.transcribe(audio,
                                                             beam_size=1)
            text = " ".join(s.text.strip() for s in segments).strip()
            text = dictation.polish(text)
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
        if not text:
            if level <= 0.002:
                return {"ok": False,
                        "error": f"{self._rec_device} produced silence "
                                 f"(level {level:.5f}). That is the "
                                 f"microphone or its Windows input level."}
            return {"ok": False,
                    "error": "Sound came through but no words were found."}
        return {"ok": True, "text": text, "note": note if note != "fits"
                else ""}


#: One definition, because the window is found BY this title when a
#: second launch stands down. Two copies could drift apart and the
#: raiser would silently find nothing.
WINDOW_TITLE = "Strata Console — web shell"


def _pid_alive(pid):
    """Is that process still running? Windows, without extra packages."""
    import ctypes
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    k = ctypes.windll.kernel32
    h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not h:
        return False          # gone, or not ours to ask about
    try:
        code = ctypes.c_ulong()
        if not k.GetExitCodeProcess(h, ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE
    finally:
        k.CloseHandle(h)


def _raise_existing_window():
    """Bring the console already running to the front.

    This is the whole point of standing down: the second click must
    HELP. Finding nothing is reported false rather than guessed -- the
    caller then starts normally, because a click that does nothing is
    what produced three processes in the first place.
    """
    import ctypes
    user32 = ctypes.windll.user32
    SW_RESTORE = 9
    found = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p,
                                     ctypes.c_void_p)

    def each(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value.startswith(WINDOW_TITLE):
                found.append(hwnd)
        return True

    try:
        user32.EnumWindows(WNDENUMPROC(each), None)
    except Exception:
        return False
    if not found:
        return False
    hwnd = found[0]
    user32.ShowWindow(hwnd, SW_RESTORE)   # un-minimise, as PID 23392 was
    user32.SetForegroundWindow(hwnd)
    return True


def main():
    if not os.path.exists(INDEX):
        raise SystemExit(f"missing {INDEX}")
    # One console, not three (2026-10-17). The owner clicked the icon,
    # the window did not paint fast enough on a machine with 764 MB
    # free, so he clicked again -- and the app let him start two more
    # copies, each taking memory from the one already struggling. The
    # second click now raises the first window instead of competing
    # with it. The DECISION is a tested kernel; only the effects live
    # here.
    lock = single_instance.lock_path(HERE)
    try:
        with open(lock, encoding="utf-8") as fh:
            existing = fh.read()
    except OSError:
        existing = ""
    verdict = single_instance.decide(existing, os.getpid(), _pid_alive)
    if verdict == single_instance.DEFER:
        pid, _started = single_instance.parse_lock(existing)
        print(single_instance.defer_message(pid))
        if _raise_existing_window():
            return 0
        # The lock says a console is running but no window answered.
        # Starting is the safer failure: a missing window the owner can
        # see beats an app that refuses to open and cannot say why.
        print("No window answered, so starting a new console.")
    try:
        with open(lock, "w", encoding="utf-8") as fh:
            fh.write(single_instance.render_lock(
                os.getpid(), datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))
    except OSError:
        pass          # a lock we cannot write is not worth failing over

    api = Api()
    # Sized as a fraction of the screen rather than a fixed pixel count:
    # the Tk shell's oldest defect was a hardcoded size that did not fit,
    # and there is no reason to import that mistake into a new shell.
    window = webview.create_window(
        WINDOW_TITLE,
        INDEX,
        js_api=api,
        width=1000,
        height=680,
        min_size=(640, 460),
        background_color="#12161A",
    )
    # The bridge needs the window back: 📎 Upload opens the window's own
    # native dialog, because a page-side file input returns a sandboxed
    # blob and the text extractors read from a real path.
    api.window = window
    # Edge WebView2 explicitly: it is present on this machine and the
    # alternative backends are not, so failing loudly beats falling back
    # to something untested.
    webview.start(gui="edgechromium", debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
