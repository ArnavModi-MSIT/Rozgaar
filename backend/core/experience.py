"""
Best-effort extraction of the minimum years of experience a job posting
asks for, scanned from description text. Heuristic, like
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

For independent required clauses, the strongest minimum applies: five years
overall plus one year using SQL still requires five years. Each numeric range
contributes its lower endpoint; direct `or N years` alternatives use the lower
bar inside that alternative group. Decimal years are preserved.

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
from html import unescape
from functools import lru_cache

_WINDOW = 60  # chars of context scanned on each side of "experience"
_LOCAL_WINDOW = 40  # tighter window around each NUMBER match itself, used
# to classify that specific number as required/preferred/unspecified

_YEAR_NUM_RE = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?)\s*\+?\s*"
    r"(?:(?:-|to|–|—)\s*(\d+(?:\.\d+)?)\s*\+?)?\s*(?:years?|yrs?)\b", re.I
)


def _year_value(raw):
    value = float(raw)
    return int(value) if value.is_integer() else value


def _strongest_requirement(values, text):
    """Independent requirements all apply; explicit alternatives use the lower bar.

    A range contributes only its lower endpoint. A smaller SQL requirement must
    not erase a separate overall experience requirement. Degree/role alternatives
    remain a heuristic: recognize a direct `... years ... or N years ...` clause,
    while avoiding an unrelated `Python or SQL` from changing the aggregation.
    """
    if not values:
        return None
    allowed = set(values)
    matches = [match for match in _YEAR_NUM_RE.finditer(text)
               if _year_value(match.group(1)) in allowed]
    groups = []
    previous = None
    for match in matches:
        value = _year_value(match.group(1))
        between = text[previous.end():match.start()] if previous else ""
        alternative = bool(previous and re.search(
            r"\bor\s+(?:(?:at least|minimum|a minimum of)\s+)?$", between, re.I))
        if alternative:
            groups[-1].append(value)
        else:
            groups.append([value])
        previous = match
    found = {_year_value(match.group(1)) for match in matches}
    groups.extend([[value] for value in allowed - found])
    return max(min(group) for group in groups)

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


def _extract_min_experience_legacy(text):
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
            # A 2-5-year range is a two-year minimum, not two independent bars.
            years_found = [_year_value(num_m.group(1))]

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
        return _strongest_requirement(required, text)
    if unspecified:
        return _strongest_requirement(unspecified, text)
    # Only preferred-tagged numbers found, nothing required/unspecified —
    # see module docstring for why this falls through to "unknown" rather
    # than reporting a soft preference as a hard minimum.

    if _FRESHER_RE.search(text):
        return 0

    return None


_SECTION_RE = re.compile(r"\b(basic qualifications|required qualifications|minimum qualifications|required skills|preferred qualifications|preferred skills|(?:(?:required|minimum|preferred|professional|work|total)\s+)?experience(?:\s+(?:required|preferred))?(?=\s*:)|(?:key )?responsibilities|benefits)\s*:?[ \t]*", re.I)


def _bare_experience_years(text):
    """A numeric-only first line is meaningful under an explicit Experience heading."""
    lines = [line.strip(" \t:-•") for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    line = _REQUIRED_SIGNAL_RE.sub("", _PREFERRED_SIGNAL_RE.sub("", lines[0])).strip(" .,:;")
    match = _YEAR_NUM_RE.fullmatch(line)
    return [_year_value(match.group(1))] if match else []


def _plain_experience_text(text):
    text = unescape(text or "")
    text = re.sub(r"</?(?:p|div|li|h[1-6]|br)\b[^>]*>", "\n", text, flags=re.I)
    return re.sub(r"<[^>]+>", " ", text)


def _preferred_section(name, previous):
    if "preferred" in name:
        return True
    if name in {"experience", "work experience", "professional experience", "total experience"}:
        return previous
    return False

def _long_requirement_years(text):

    """Catch long clauses without crossing other year counts or sentence boundaries."""

    values=[]

    for match in _YEAR_NUM_RE.finditer(text):

        tail=text[match.end():match.end()+600]

        # A wrapped line is allowed; a separate numbered requirement is not.

        tail=re.split(r"[;.!?]|\n\s*[-•]|\b\d+(?:\.\d+)?\s*\+?\s*(?:years?|yrs?)\b",tail,maxsplit=1)[0]

        prefix=re.split(r"[;.!?\n]",text[:match.start()])[-1][-40:]
        clause=prefix+text[match.start():match.end()]+re.sub(r"\([^)]*\)", "", tail)
        if _PREFERRED_SIGNAL_RE.search(clause) and not _REQUIRED_SIGNAL_RE.search(clause):
            continue
        if re.search(r"\bexperience\b",tail,re.I) or re.match(
            r"\s+(?:in|as)\s+(?:an?\s+)?[^;\n.!?]{0,160}\b(?:role|position)\b",tail,re.I):

            values.append(_year_value(match.group(1)))

    return values

def extract_min_experience(text):

    """Description-based heuristic; required sections outrank preferred sections."""

    text = _plain_experience_text(text)
    if not text:return None

    headings=list(_SECTION_RE.finditer(text))

    if not headings:
        value = _extract_min_experience_legacy(text)
        # Nearby preference words from a different bullet must not erase
        # an otherwise explicit years-of-experience clause.
        if value is None:
            years = _long_requirement_years(text)
            return _strongest_requirement(years, text)
        return value

    required=[]

    remaining=[text[:headings[0].start()]]
    preferred_context = False

    for index,heading in enumerate(headings):

        section=text[heading.end():headings[index+1].start() if index+1<len(headings) else len(text)]

        name=heading.group(1).lower()
        preferred_context = _preferred_section(name, preferred_context)
        if preferred_context:
            continue

        if 'preferred' not in name and name.startswith(('basic','required','minimum','experience','professional','work','total')):

            years=_long_requirement_years(section)

            first_line = section.strip().splitlines()[0] if section.strip() else ""
            if 'experience' in name and not _PREFERRED_SIGNAL_RE.search(first_line):
                years.extend(_bare_experience_years(section))

            legacy=_extract_min_experience_legacy(section)

            if legacy is not None and (years or not _PREFERRED_SIGNAL_RE.search(section) or _REQUIRED_SIGNAL_RE.search(section)):
                years.append(legacy)

            required.extend(years)

        elif 'preferred' not in name:

            remaining.append(section)

    if required:return _strongest_requirement(required, text)

    remaining_text = '\n'.join(remaining)
    value = _extract_min_experience_legacy(remaining_text)
    if value is None:
        years = _long_requirement_years(remaining_text)
        return _strongest_requirement(years, remaining_text)
    return value


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def extract_preferred_experience(text):
    """Preferred years remain separate from mandatory minimum experience."""
    text = _plain_experience_text(text)
    if not text:
        return None
    headings = list(_SECTION_RE.finditer(text))
    candidates = []
    bare_years = []
    preferred_context = False
    for index, heading in enumerate(headings):
        name = heading.group(1).lower()
        preferred_context = _preferred_section(name, preferred_context)
        if preferred_context:
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            candidates.append(text[heading.end():end])
            if "experience" in name:
                bare_years.extend(_bare_experience_years(text[heading.end():end]))
    # Handle explicit preferences without a preferred-section heading too.
    for line in _SENTENCE_SPLIT_RE.split(text):
        if _PREFERRED_SIGNAL_RE.search(line) and not _REQUIRED_SIGNAL_RE.search(line):
            candidates.append(line)
            heading = _SECTION_RE.search(line)
            if heading and "experience" in heading.group(1).lower():
                bare_years.extend(_bare_experience_years(line[heading.end():]))
    years = []
    for candidate in candidates:
        # The containing section or clause already established preference.
        # Removing those words lets the existing year/experience association
        # check run without promoting this preference to a required minimum.
        years.extend(_long_requirement_years(_PREFERRED_SIGNAL_RE.sub(" ", candidate)))
    return _strongest_requirement(years + bare_years, "\n".join(candidates))


def extract_title_experience(title):
    """Use explicit experience ranges/+ years in a title, never seniority words."""
    title = title or ""
    values = []
    for match in _YEAR_NUM_RE.finditer(title):
        if not (match.group(2) or "+" in match.group() or re.search(r"\bexperience\b", title, re.I)):
            continue
        tail = title[match.end():match.end()+35]
        if re.match(r"\s*(?:contract|duration|degree|course|programme|program)\b", tail, re.I):
            continue
        value = _year_value(match.group(1))
        if 0 <= value <= 50:
            values.append(value)
    return _strongest_requirement(values, title)


@lru_cache(maxsize=16384)
def experience_requirements(description, title=""):
    """Combine description requirements with numeric title evidence separately."""
    required = extract_min_experience(description)
    preferred = extract_preferred_experience(description)
    title_years = extract_title_experience(title)
    if title_years is not None:
        if _PREFERRED_SIGNAL_RE.search(title or ""):
            preferred = max(preferred, title_years) if preferred is not None else title_years
        else:
            required = max(required, title_years) if required is not None else title_years
    return required, preferred


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
