r"""The operator codex -- a stable vocabulary for the glyph keyboard.

**The defect this exists to end.** The ice cube carried three different
meanings across three artefacts, written months apart:

    source document one   "Logic / Stabilize"
    source document two   "Crystallized Memory / Red Zone"
    shipped browser build ``GOLDEN_SOURCE`` (authoritative / canonical)

Nobody made a mistake. That is simply what happens when the picture *is*
the identity: a glyph can be re-read, and re-reading leaves no trace. A
four-letter code cannot drift, because changing one is a visible edit to
the data.

So the identity moved. Each operator now carries a ``code`` that the
machine uses and an ``icon`` that the owner sees, and the two are
independent. The icon can be replaced on any day, for any reason, and not
one stored row has to migrate.

**Why the emoji went.** Three separate failures, each sufficient on its
own. An emoji renders as a different picture on every platform, so the
appearance was never ours to control. A screen reader announces its
Unicode name -- "snake", not "cycle" -- which breaks the promise the text
labels were keeping. And a language model reads the code point's
conventional meaning, so U+1F40D arrives carrying every association
"snake" has, with the private meaning present only if some prompt happens
to restate it. The icons named here come from one open family instead,
shipped as artwork this project controls.

**What this is, in standard terms.** The second source document turned
out to describe a small domain-specific language: a production rule
(``[ACTION] -> [OBJECT] -> [EFFECT]``), sequencing, parallel composition,
nesting, and a mapping from each symbol onto an operation. This module is
that language's *operator vocabulary*. ``strata_tools/commands.py`` holds
its grammar. The glyphs were only ever its concrete syntax, which is the
interchangeable part -- that is what front ends are for.

**Zone is a property, not a token.** One source document assigned a glyph
per zone; the shipped code made zone an attribute of every operator. The
code was right, and this module keeps it that way. A zone is the state a
piece of work is in. It is not something a person types.

Pure, standard library only, no I/O. ``tests/test_codex.py`` proves every
invariant below before any key is wired.
"""

# ---------------------------------------------------------------------------
# Pipeline stages. Each operator names the stage it conditions.
#
# These are the five stages that actually run in strata_core, not invented
# verbs. The source documents mapped glyphs onto functions like
# ``harmonize(cognition)`` and ``expand(fractal)``, which read as operations
# but name nothing that exists. A semantics that names absent functions is a
# wish, not a specification, so every operator here points at a real stage.
# ---------------------------------------------------------------------------
STAGES = {
    "CLASSIFY": "Input classifier -- tokenizes and extracts operator tags",
    "DISPATCH": "Dispatcher -- routes by intent and operating mode",
    "CONTEXT": "Context manager -- decides what material is retrieved",
    "STYLE": "Style conditioner -- shapes tone and structure of the reply",
    "SYNTH": "Response synthesizer -- conditions the generated answer",
}

# Operating zones. A property carried by each operator, never a key.
ZONES = {
    "GREEN": "Active. Low load, direct work.",
    "YELLOW": "Testing. Moderate load, pattern work.",
    "RED": "Archival or careful. Higher load, slower work.",
    "VARIES": "Depends on what it is applied to.",
}

# Zone display. The traffic-light convention: internationally recognised,
# and aligned with the ISO 3864 safety colours already familiar from every
# road and workplace. Colour alone would fail WCAG 1.4.1, so each zone
# carries a label and a shape name too -- three channels saying one thing,
# which is the only redundancy that reliably survives tiredness.
ZONE_DISPLAY = {
    "GREEN": {"colour": "#2E7D32", "label": "Green", "shape": "circle"},
    "YELLOW": {"colour": "#B8860B", "label": "Yellow", "shape": "circle"},
    "RED": {"colour": "#B3261E", "label": "Red", "shape": "circle"},
    "VARIES": {"colour": "#5F5E5A", "label": "Varies", "shape": "circle"},
}

CODE_LENGTH = 4

# ---------------------------------------------------------------------------
# The operators.
#
# ``number`` is the address, and it is what the numeral layer will carry.
# ``code`` is what a person reads, because four letters survive a glance
# better than two digits do for anyone whose numbers slip.
#
# ``icon`` names a Tabler outline icon (MIT). The names are candidates until
# checked against the shipped set -- see ``unverified_icons()``, which exists
# so that an icon nobody confirmed cannot quietly pass for one that was.
#
# ``legacy_glyph`` records what each operator used to be, so a stored row
# written under the old scheme can still be read. It is history, not
# identity, and nothing in this module dispatches on it.
# ---------------------------------------------------------------------------
OPERATORS = (
    {"code": "EXEC", "number": 1, "label": "Execute", "icon": "player-play",
     "zone": "GREEN", "load": (1, 3), "stage": "DISPATCH",
     "legacy_glyph": "\U0001F53A",
     "instruction": "The user wants immediate action; be direct and executable."},

    {"code": "ANLZ", "number": 2, "label": "Analyze", "icon": "zoom-in",
     "zone": "RED", "load": (4, 6), "stage": "DISPATCH",
     "legacy_glyph": "\U0001F538",
     "instruction": "This needs review: pause and structure the answer before giving it."},

    {"code": "ITER", "number": 3, "label": "Iterate", "icon": "refresh",
     "zone": "VARIES", "load": (3, 5), "stage": "STYLE",
     "legacy_glyph": "\U0001F300",
     "instruction": "Growth and expansion: suggest concrete next steps."},

    {"code": "SYNT", "number": 4, "label": "Synthesize", "icon": "git-merge",
     "zone": "YELLOW", "load": (4, 6), "stage": "SYNTH",
     "legacy_glyph": "\U0001F537",
     "instruction": "Draw the threads into one coherent whole and name what unifies them."},

    {"code": "CORE", "number": 5, "label": "Core", "icon": "circle-dot",
     "zone": "GREEN", "load": (2, 4), "stage": "STYLE",
     "legacy_glyph": "\U0001F4A0",
     "instruction": "A central, essential concept: keep the answer anchored to it."},

    # The cube split. One picture had been carrying two incompatible ideas --
    # structure, and canonical provenance. They are different jobs, so they
    # are now two operators and neither has to give way to the other.
    {"code": "STAB", "number": 6, "label": "Structure", "icon": "brain",
     "zone": "YELLOW", "load": (2, 4), "stage": "STYLE",
     "legacy_glyph": "\U0001F9CA",
     "instruction": "Structured thought: lay the answer out in explicit, ordered parts."},

    {"code": "GOLD", "number": 7, "label": "Golden", "icon": "lock",
     "zone": "YELLOW", "load": (2, 4), "stage": "CONTEXT",
     "legacy_glyph": "\U0001F9CA",
     "instruction": "Treat the referenced material as canonical and archived; it never expires."},

    {"code": "ANCH", "number": 8, "label": "Anchor", "icon": "anchor",
     "zone": "YELLOW", "load": (1, 3), "stage": "CONTEXT",
     "legacy_glyph": "⚪",
     "instruction": "A fixed reference point: do not change or reinterpret it."},

    {"code": "CMAP", "number": 9, "label": "Map", "icon": "sitemap",
     "zone": "YELLOW", "load": (3, 5), "stage": "SYNTH",
     "legacy_glyph": "\U0001F52E",
     "instruction": "Map the concepts and how they relate, rather than answering in prose."},

    {"code": "LINK", "number": 10, "label": "Link", "icon": "link",
     "zone": "VARIES", "load": (2, 4), "stage": "CONTEXT",
     "legacy_glyph": "\U0001F517",
     "instruction": "Connect: tie the answer explicitly to the related material already in play, naming it."},

    {"code": "CYCL", "number": 11, "label": "Cycle", "icon": "rotate-clockwise",
     "zone": "VARIES", "load": (3, 6), "stage": "STYLE",
     "legacy_glyph": "\U0001F40D",
     "instruction": "A refinement loop: treat this as one pass and end with what the next pass should check."},

    {"code": "RESO", "number": 12, "label": "Resonance", "icon": "wave-sine",
     "zone": "YELLOW", "load": (3, 5), "stage": "CONTEXT",
     "legacy_glyph": "\U0001F504",
     "instruction": "Harmonize: keep the answer consistent with what is already established in this session."},

    # Wave kept its shipped meaning. One source document read it as peace;
    # the v3.8 note had already recorded refusing that reading, so the code
    # had decided and only the documents were left disagreeing.
    {"code": "WAVE", "number": 13, "label": "Wave", "icon": "ripple",
     "zone": "RED", "load": (5, 7), "stage": "STYLE",
     "legacy_glyph": "\U0001F30A",
     "instruction": "Experimental and uncertain: hold conclusions loosely and say what is unknown."},

    {"code": "WISD", "number": 14, "label": "Wisdom", "icon": "tree",
     "zone": "RED", "load": (3, 5), "stage": "STYLE",
     "legacy_glyph": "\U0001F333",
     "instruction": "Take the long view: ground the answer in durable principles rather than quick fixes."},

    {"code": "TARG", "number": 15, "label": "Target", "icon": "target",
     "zone": "GREEN", "load": (2, 5), "stage": "STYLE",
     "legacy_glyph": "\U0001F3AF",
     "instruction": "A goal: track progress toward it and say how far along things are."},

    {"code": "URGE", "number": 16, "label": "Urgent", "icon": "alert-triangle",
     "zone": "GREEN", "load": (1, 3), "stage": "DISPATCH",
     "legacy_glyph": "⚡",
     "instruction": "High priority: answer the time-critical part first and explicitly defer the rest."},

    {"code": "SENT", "number": 17, "label": "Sentiment", "icon": "mood-smile",
     "zone": "VARIES", "load": (2, 4), "stage": "STYLE",
     "legacy_glyph": "⭕",
     "instruction": "Attend to tone and feeling, not only to the facts."},

    {"code": "COLL", "number": 18, "label": "Collaborate", "icon": "users",
     "zone": "GREEN", "load": (2, 4), "stage": "STYLE",
     "legacy_glyph": "\U0001F91D",
     "instruction": "Work this through together: offer options and ask before deciding."},

    {"code": "COCO", "number": 19, "label": "Coconut", "icon": "sparkles",
     "zone": "VARIES", "load": (1, 2), "stage": "STYLE",
     "legacy_glyph": "\U0001F965",
     "instruction": "Coconut Protocol: add warmth and contextual humour."},
)

# Nineteen, not twenty. Twenty was a round number chosen before the concepts
# were counted, and the concepts came to nineteen. Inventing a twentieth to
# reach it would be the same error as picking a glyph before knowing what it
# meant.

# ---------------------------------------------------------------------------
# ACTIONS -- the verbs.
#
# **Why this block exists.** The owner laid three keys beside each other --
# assistant, input, data -- and observed that "assistant input data in green
# zone" reads better than any string of operators. He was right, and the
# reason is grammatical: that is a SENTENCE. Actor, verb, object, mode.
#
# The nineteen operators above are MODIFIERS. They say how the assistant
# should answer. A keyboard of nothing but modifiers is a pile of adverbs
# with no verb, which is exactly why it never read as language.
#
# So the parts of speech are three, and they must not share a namespace
# again -- sharing one is what let a glyph mean three things:
#
#   ACTIONS    verbs. What the application DOES.          Input, Save
#   OPERATORS  modifiers. How the assistant ANSWERS.      Execute, Analyze
#   ZONES      mode. The state the work is IN.            Green, Yellow, Red
#
# The object of the sentence -- "data", "note", the thing being acted on --
# is ordinary typed text, not a key. Adding a fourth block of nouns would
# mean inventing a vocabulary for everything a person might mention.
#
# ``destructive`` is carried and is False on every row. SCOPE.md §3:
# "Archive, never delete. No owner data is destroyed by any control." A
# Trash key was proposed and refused -- it would either break that rule or
# lie about what it does. ARCH archives; nothing here deletes.
# ---------------------------------------------------------------------------
ACTIONS = (
    {"verb": "take it in", "code": "INPT", "number": 1, "label": "Input", "icon": "file-import",
     "destructive": False,
     "does": "Take material in: an uploaded file, a pasted passage, a note."},

    {"verb": "find it", "code": "FIND", "number": 2, "label": "Find", "icon": "search",
     "destructive": False,
     "does": "Retrieve from what is already stored, by tag, zone or text."},

    {"verb": "search the web", "code": "WEBS", "number": 3, "label": "Web", "icon": "world",
     "destructive": False,
     "does": "Consult the web for this message. Opt-in, per message."},

    {"verb": "save it", "code": "SAVE", "number": 4, "label": "Save", "icon": "device-floppy",
     "destructive": False,
     "does": "Persist the current work as a record that can be found again."},

    {"verb": "export it", "code": "EXPT", "number": 5, "label": "Export", "icon": "file-export",
     "destructive": False,
     "does": "Write out a readable copy. The store stays as it is."},

    {"verb": "archive it", "code": "ARCH", "number": 6, "label": "Archive", "icon": "archive",
     "destructive": False,
     "does": "Retire from view. The rows stay; a floor is raised, not a "
             "record removed."},

    {"verb": "clear", "code": "CLER", "number": 7, "label": "Clear", "icon": "eraser",
     "destructive": False,
     "does": "Clear the transcript AND what the model recalls, together. "
             "Clearing only the view would leave the assistant quoting the "
             "conversation just cleared."},

    {"verb": "halt", "code": "HALT", "number": 8, "label": "Halt", "icon": "player-stop",
     "destructive": False,
     "does": "Stop the current operation. Nothing already recorded is lost."},
)

BY_ACTION = {a["code"]: a for a in ACTIONS}


def action(code):
    """The action with this code, or None. Case-insensitive."""
    if not code:
        return None
    return BY_ACTION.get(code.strip().upper())


def part_of_speech(code):
    """'ACTION', 'OPERATOR', or None. The two namespaces stay disjoint."""
    if action(code) is not None:
        return "ACTION"
    if operator(code) is not None:
        return "OPERATOR"
    return None


def reads_as(codes, zone=None):
    """A code sequence read back as plain English, for the sequence bar.

    The point of the three blocks: ``["INPT", "EXEC"]`` with zone GREEN
    reads "Input, then execute -- in the green zone." A person can check
    what they typed without consulting a legend, which is the test the
    old keyboard failed.
    """
    verbs, modifiers, unknown = [], [], []
    for code in codes or ():
        kind = part_of_speech(code)
        if kind == "ACTION":
            verbs.append(action(code)["verb"])
        elif kind == "OPERATOR":
            modifiers.append(operator(code)["label"].lower())
        else:
            unknown.append(code)

    if verbs:
        sentence = ", then ".join(verbs)
        if modifiers:
            sentence += " -- " + " and ".join(modifiers)
    elif modifiers:
        sentence = " and ".join(modifiers)
    else:
        sentence = "nothing selected"

    sentence = sentence[0].upper() + sentence[1:]
    if zone in ZONE_DISPLAY:
        sentence += f", in the {ZONE_DISPLAY[zone]['label'].lower()} zone"
    if unknown:
        sentence += f" (unrecognised: {', '.join(unknown)})"
    return sentence


# ---------------------------------------------------------------------------
# Codex v2, frozen 2026-10-15. Superseded, not deleted.
#
# This is the shipped eighteen as they stood, kept so that a row written
# under the old scheme can still be read and so the history stays legible.
# It is a record. Nothing dispatches on it, and it does not grow.
# ---------------------------------------------------------------------------
CODEX_V2_FROZEN = {
    "\U0001F53A": "EXECUTE", "\U0001F9CA": "GOLDEN_SOURCE",
    "\U0001F538": "ANALYZE", "\U0001F300": "ITERATE",
    "\U0001F965": "COCONUT", "\U0001F4A0": "CORE",
    "⚪": "ANCHOR", "\U0001F30A": "WAVE", "\U0001F3AF": "TARGET",
    "\U0001F537": "UNITY", "\U0001F40D": "CYCLE", "⚡": "URGENT",
    "\U0001F333": "WISDOM", "\U0001F504": "RESONANCE", "\U0001F517": "LINK",
    "⭕": "SENTIMENT", "\U0001F52E": "MAP", "\U0001F91D": "COLLABORATE",
}

# Names retired on collation, with the reason. Published rather than removed
# quietly, on the same principle as any other correction notice.
RETIRED = {
    "UNITY": "Renamed SYNT/Synthesize. 'Unity' named a feeling; 'synthesize' names the operation.",
    "GOLDEN_SOURCE": "Split into GOLD (canonical) and STAB (structure). One glyph had carried both.",
    "ETHICAL_SHIELD": "Cut. Claimed the system validates ethics. It does not and cannot.",
    "JUSTICE_SCALE": "Cut. Claimed the system balances equity. Never implemented, never implementable here.",
    "GRACE_DROP": "Cut. Claimed the system forgives error. A system does not forgive.",
}

# How a glyph in an already-stored row resolves to an operator.
#
# DECLARED, not derived. An earlier draft built this by walking OPERATORS and
# taking the first match, and the test suite caught it immediately: the ice
# cube is the ancestor of BOTH ``STAB`` and ``GOLD``, so list order silently
# decided a migration. That is the same class of defect the codes exist to
# end, reproduced inside the module meant to end it.
#
# The rule for an ambiguous ancestor is: resolve to what the SHIPPED BUILD
# meant, because the shipped build is what wrote the rows. The documents
# disagreed with it; the documents never wrote a row.
LEGACY_RESOLUTION = {
    "\U0001F53A": "EXEC",
    "\U0001F9CA": "GOLD",   # ambiguous ancestor: shipped build said GOLDEN_SOURCE
    "\U0001F538": "ANLZ",
    "\U0001F300": "ITER",
    "\U0001F965": "COCO",
    "\U0001F4A0": "CORE",
    "⚪": "ANCH",
    "\U0001F30A": "WAVE",
    "\U0001F3AF": "TARG",
    "\U0001F537": "SYNT",
    "\U0001F40D": "CYCL",
    "⚡": "URGE",
    "\U0001F333": "WISD",
    "\U0001F504": "RESO",
    "\U0001F517": "LINK",
    "⭕": "SENT",
    "\U0001F52E": "CMAP",
    "\U0001F91D": "COLL",
}

# Lookups, built once.
BY_CODE = {op["code"]: op for op in OPERATORS}
BY_NUMBER = {op["number"]: op for op in OPERATORS}
BY_LEGACY_GLYPH = {g: BY_CODE[c] for g, c in LEGACY_RESOLUTION.items()}


def operator(code):
    """The operator with this code, or None. Case-insensitive."""
    if not code:
        return None
    return BY_CODE.get(code.strip().upper())


def by_number(number):
    """The operator at this address, or None."""
    return BY_NUMBER.get(number)


def from_legacy_glyph(glyph):
    """The operator a retired glyph used to mean, or None.

    For reading rows written before the codes existed. The ice cube maps to
    GOLD, because that is what the shipped build meant by it -- the other two
    readings were documentation that the code never followed.
    """
    return BY_LEGACY_GLYPH.get(glyph)


def zone_of(code):
    """The zone an operator belongs to, or None. Zone is a property."""
    op = operator(code)
    return op["zone"] if op else None


def stage_of(code):
    """The pipeline stage an operator conditions, or None."""
    op = operator(code)
    return op["stage"] if op else None


def instructions_for(codes):
    """The model instructions for a sequence of codes, in pipeline order.

    Ordered by stage rather than by how the owner happened to type them, so
    the same set of operators conditions the pipeline the same way every
    time. An unknown code is skipped here; ``unknown_codes`` is what reports
    it, because a silent decline is its own defect.
    """
    order = list(STAGES)
    found = [operator(c) for c in codes or ()]
    found = [op for op in found if op is not None]
    found.sort(key=lambda op: (order.index(op["stage"]), op["number"]))
    return [op["instruction"] for op in found]


def unknown_codes(codes):
    """Codes that name no operator. Returned so the caller can say so."""
    return [c for c in codes or () if operator(c) is None]


def peak_load(codes):
    """The highest upper load of any named operator, or 0 for none.

    A reading of the operators chosen, not a measurement of anything about
    the person. The dial records a self-report; this records what was asked
    for.
    """
    ops = [operator(c) for c in codes or ()]
    loads = [op["load"][1] for op in ops if op is not None]
    return max(loads) if loads else 0


def display(code):
    """Everything the keyboard needs to draw one key, or None.

    Three channels carrying the same message -- icon, text, and zone colour
    with its own label. No single channel has to work alone.
    """
    op = operator(code)
    if op is None:
        return None
    zone = ZONE_DISPLAY[op["zone"]]
    return {
        "code": op["code"],
        "number": op["number"],
        "label": op["label"],
        "icon": op["icon"],
        "zone": op["zone"],
        "zone_colour": zone["colour"],
        "zone_label": zone["label"],
    }


def keyboard_rows(per_row=5):
    """The operators laid out in rows of ``per_row``, in address order."""
    if per_row < 1:
        raise ValueError(f"per_row must be at least 1; got {per_row}")
    codes = [op["code"] for op in OPERATORS]
    return [codes[i:i + per_row] for i in range(0, len(codes), per_row)]


def unverified_icons():
    """Icon names not yet confirmed against the shipped Tabler set.

    Every one of them, for now. The names were chosen from the family's
    conventions rather than read out of its manifest, and an icon that
    nobody confirmed must not pass for one that was. Checking them is a
    bounded job and this is where its result belongs.
    """
    return sorted([op["icon"] for op in OPERATORS] +
                  [a["icon"] for a in ACTIONS])


def validate():
    """Every structural invariant. Returns a list of problems; empty is good.

    Called by the test suite. A codex that fails this has drifted, and the
    whole point of the codes is that drift becomes visible.
    """
    problems = []
    codes = [op["code"] for op in OPERATORS]
    numbers = [op["number"] for op in OPERATORS]

    if len(set(codes)) != len(codes):
        problems.append("duplicate code")
    if len(set(numbers)) != len(numbers):
        problems.append("duplicate number")
    if sorted(numbers) != list(range(1, len(OPERATORS) + 1)):
        problems.append("numbers are not a contiguous run from 1")

    # Every frozen glyph must still resolve, or a stored row goes unreadable.
    for glyph, code in LEGACY_RESOLUTION.items():
        if code not in BY_CODE:
            problems.append(f"legacy glyph resolves to unknown code {code}")
    missing = set(CODEX_V2_FROZEN) - set(LEGACY_RESOLUTION)
    if missing:
        problems.append(f"{len(missing)} frozen glyph(s) have no resolution")

    for op in OPERATORS:
        code = op["code"]
        if len(code) != CODE_LENGTH or not code.isalpha() or not code.isupper():
            problems.append(f"{code}: code must be {CODE_LENGTH} uppercase letters")
        if op["zone"] not in ZONES:
            problems.append(f"{code}: unknown zone {op['zone']}")
        if op["stage"] not in STAGES:
            problems.append(f"{code}: unknown stage {op['stage']}")
        low, high = op["load"]
        if not 1 <= low <= high <= 10:
            problems.append(f"{code}: load {op['load']} outside 1..10 or inverted")
        if not op["label"] or " " in op["label"]:
            problems.append(f"{code}: label must be one word")
        if not op["icon"] or " " in op["icon"]:
            problems.append(f"{code}: icon must be one icon name")
        if not op["instruction"].strip():
            problems.append(f"{code}: no instruction")

    # ACTIONS -- the verbs. A separate namespace on purpose.
    action_codes = [a["code"] for a in ACTIONS]
    action_numbers = [a["number"] for a in ACTIONS]
    if len(set(action_codes)) != len(action_codes):
        problems.append("duplicate action code")
    if sorted(action_numbers) != list(range(1, len(ACTIONS) + 1)):
        problems.append("action numbers are not a contiguous run from 1")

    # The two namespaces must not overlap. Sharing one is what let a single
    # glyph come to mean three different things.
    collisions = set(action_codes) & set(codes)
    if collisions:
        problems.append(f"code in both namespaces: {sorted(collisions)}")

    for act in ACTIONS:
        code = act["code"]
        if len(code) != CODE_LENGTH or not code.isalpha() or not code.isupper():
            problems.append(f"{code}: code must be {CODE_LENGTH} uppercase letters")
        if act["destructive"]:
            problems.append(
                f"{code}: destructive -- SCOPE.md §3 is archive, never delete"
            )
        if not act["does"].strip():
            problems.append(f"{code}: no description of what it does")
        if not act.get("verb", "").strip():
            problems.append(f"{code}: no verb form for the sequence bar")
        if not act["label"] or " " in act["label"]:
            problems.append(f"{code}: label must be one word")
    return problems
