"""
Best-effort extraction of the minimum years of experience a job posting
asks for, scanned from free text (title + description). Heuristic, like
core/classify.py and core/location.py — not authoritative, just good
enough to filter by.

Approach: find every occurrence of the word "experience" in the text, look
at a small window of characters around each one, and pull out any
"N years"/"N+ years"/"N-M years" style number found in that window. Using
a window (rather than matching numbers+years anywhere in the text) is
deliberate — it avoids false positives from unrelated years-mentions
elsewhere in a posting (e.g. "5 years in business", certifications valid
for "2 years", benefits described in years), which a bare
"\\d+\\s*years?" search anywhere in the text would happily match.

REQUIRED vs PREFERRED (added after review feedback): a naive "take the
minimum across every number found" conflates hard requirements with soft
preferences — "2 years preferred, 4+ years required" would previously
report 2, silently understating the actual gate. Each number match now
also gets a tighter local-context check for requirement-language
("required", "must have", "at least", "minimum", "needed") vs preference-
language ("preferred", "nice to have", "a plus", "desirable"). Priority
when picking the final value: REQUIRED numbers win if any exist; else
UNSPECIFIED numbers (the common case — most postings don't bother
tagging "required" explicitly, they just state it); a number tagged ONLY
as "preferred" with nothing else found is treated as unknown (None)
rather than misreported as a hard minimum — a soft preference isn't a
real gate, and reporting it as one risks hiding a job you'd actually
qualify for, which is the opposite failure mode but still wrong.

Known unsolved limitation (flagged, not fixed): multi-track postings like
"Freshers with 0 years welcome for the associate track; senior track
requires 5 years" describe TWO different roles with two different bars,
not one job with a soft/hard split. This parser has no way to tell that
apart from the required/preferred case above — it will report 5 (the
REQUIRED number) even though a fresher-eligible track genuinely exists
in the text. Reliably solving this needs actual sentence-level
understanding of which requirement belongs to which role, not a regex
window. Documented here rather than papered over.
"""

import re

_WINDOW = 60  # chars of context scanned on each side of "experience"
_LOCAL_WINDOW = 40  # tighter window around each NUMBER match itself, used
# to classify that specific number as required/preferred/unspecified

_YEAR_NUM_RE = re.compile(
    r"(\d+)\s*\+?\s*(?:-|to|–|—)?\s*(\d*)\s*(?:years?|yrs?)", re.I
)

_REQUIRED_SIGNAL_RE = re.compile(
    r"\b(required|requires?|must\s+have|must\s+possess|mandatory|"
    r"minimum|min\.?|at\s+least|needed|you\s+have|you\s+should\s+have)\b",
    re.I,
)
_PREFERRED_SIGNAL_RE = re.compile(
    r"\b(preferred|preferably|nice\s+to\s+have|is\s+a\s+plus|a\s+plus|"
    r"bonus|desirable|advantageous|good\s+to\s+have|ideally)\b",
    re.I,
)

# Catches postings that say they're fresher-friendly without ever stating
# a number ("Freshers welcome", "no prior experience required") — treated
# as 0 years required.
_FRESHER_RE = re.compile(
    r"\b(freshers?|entry[\s-]?level|no\s+(?:prior\s+)?experience(?:\s+required)?)\b",
    re.I,
)


def extract_min_experience(text):
    """Returns an int (minimum years required) or None if the text gives
    no signal either way."""
    if not text:
        return None

    required, unspecified, preferred = [], [], []

    for m in re.finditer(r"experience", text, re.I):
        start = max(0, m.start() - _WINDOW)
        end = min(len(text), m.end() + _WINDOW)
        window = text[start:end]

        for num_m in _YEAR_NUM_RE.finditer(window):
            years_found = [int(g) for g in num_m.groups() if g]
            if not years_found:
                continue

            # Classify THIS specific number mention using a tighter
            # window around the number itself (not the outer "experience"
            # window) — required/preferred language typically sits right
            # next to the number it qualifies, not next to "experience".
            num_abs_start = start + num_m.start()
            num_abs_end = start + num_m.end()
            local_start = max(0, num_abs_start - _LOCAL_WINDOW)
            local_end = min(len(text), num_abs_end + _LOCAL_WINDOW)
            local_ctx = text[local_start:local_end]

            is_required = bool(_REQUIRED_SIGNAL_RE.search(local_ctx))
            is_preferred = bool(_PREFERRED_SIGNAL_RE.search(local_ctx))

            bucket = required if is_required else (preferred if is_preferred else unspecified)
            bucket.extend(years_found)

    if required:
        return min(required)
    if unspecified:
        return min(unspecified)
    # Only preferred-tagged numbers found, nothing required/unspecified —
    # see module docstring for why this falls through to "unknown" rather
    # than reporting a soft preference as a hard minimum.

    if _FRESHER_RE.search(text):
        return 0

    return None


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def extract_experience_sentences(text):
    """Returns only the sentences/lines from `text` that mention a number
    (years, dates, counts, etc.) or the word "experience" — a lightweight
    display filter so a person can quickly scan just the
    experience-relevant lines of a job description instead of reading the
    whole thing. Purely for display in the UI; does NOT feed into
    extract_min_experience() or any filtering/matching logic — this is a
    manual-verification aid, not part of the scoring pipeline.

    Splits on sentence-ending punctuation AND newlines, since job
    descriptions are frequently bullet-point lists ("- 3+ years SQL
    experience") rather than proper prose, and a pure sentence-punctuation
    split would smash unrelated bullets into one blob."""
    if not text:
        return []
    pieces = _SENTENCE_SPLIT_RE.split(text)
    relevant = []
    for piece in pieces:
        piece = piece.strip(" \t-•*").strip()
        if not piece:
            continue
        if re.search(r"\d", piece) or re.search(r"\bexperience\b", piece, re.I):
            relevant.append(piece)
    return relevant
