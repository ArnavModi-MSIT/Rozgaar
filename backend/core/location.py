"""
Best-effort city/country parsing from free-text location strings. Location
formats vary across ATS platforms (Greenhouse: "City, State", Oracle:
"City, State, Country", Workday/Phenom: sometimes a raw building/floor
string like "1401-G-India: 2-3 FL, 22A, STPI, Gurgaon") so this is
heuristic, not authoritative — good enough for filtering, not for anything
that needs to be reliably correct.
"""

import re

# Not exhaustive — covers countries this project's current company list
# actually posts jobs in. Add more as needed; unmatched locations fall
# back to "Unknown" rather than a wrong guess. "ind" added alongside
# "india" — fetchers/amazon.py's own location field literally uses the
# 3-letter ISO code (country="IND"), which was previously unrecognized
# here and fell through to "Unknown" despite being an unambiguous India
# signal.
COUNTRIES = [
    "india", "ind", "united states", "usa", "us", "united kingdom", "uk",
    "canada", "australia", "singapore", "germany", "ireland",
    "netherlands", "france", "uae", "united arab emirates", "poland",
    "philippines", "mexico", "brazil", "japan", "china", "spain",
    "south korea", "serbia", "sweden", "italy", "switzerland",
    "denmark", "costa rica", "new zealand", "saudi arabia",
    "israel", "finland", "portugal", "austria",
    # Explicit country labels observed in the BCG/Phenom feed. Without
    # these, known foreign postings were treated as Unknown and retained.
    "morocco", "egypt", "indonesia", "kenya", "azerbaijan", "hungary",
    "south africa", "colombia", "chile", "belgium", "malaysia", "czechia",
    "czech republic", "thailand", "norway", "vietnam", "peru", "greece",
    "türkiye", "turkiye", "turkey", "republic of korea",
    "romania", "hong kong", "taiwan",
]

_COUNTRY_DISPLAY = {
    "usa": "United States", "us": "United States",
    "uk": "United Kingdom",
    "uae": "United Arab Emirates",
    "ind": "India",
    "türkiye": "Türkiye", "turkiye": "Türkiye", "turkey": "Türkiye",
    "republic of korea": "South Korea", "czech republic": "Czechia",
}

# US state abbreviations — needed because many US postings (particularly
# Greenhouse/Ashby boards, e.g. Anthropic/OpenAI added this session) write
# locations as "City, ST" with just a state abbreviation, never spelling
# out "United States"/"USA" anywhere in the string ("San Francisco, CA",
# "New York City, NY; San Francisco, CA; Seattle, WA"). Without this,
# parse_country() fell through to "Unknown" for every such posting — and
# since is_india_or_unknown() deliberately treats "Unknown" as pass-
# through (so a genuinely unparseable India posting is never wrongly
# discarded), that silently let a large volume of clearly-US-only
# postings straight through the save-time filter and into the UI.
_US_STATE_ABBREVIATIONS = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
    "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
    "wi", "wy", "dc",
}

# Some ATS boards publish the full state name, or just a well-known US city.
# These are unambiguous location signals observed in saved Databricks/OpenAI
# postings; unknown locations still pass through for manual review.
_US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
}
_US_CITY_ONLY = {"san francisco", "seattle", "mountain view", "bellevue", "chicago", "boston"}
_US_STATE_RE = re.compile(r"\b(?:" + "|".join(re.escape(name) for name in sorted(_US_STATE_NAMES, key=len, reverse=True)) + r")\b")

# Tokens that show up as a location segment but aren't a real city —
# work-arrangement descriptors. Excluded from being picked as the "city"
# candidate (see parse_city), but kept as a legitimate LAST-RESORT
# fallback when no real city is present at all — "Remote" genuinely is
# the honest answer for a location string that's just "Remote, India".
_NON_CITY_TERMS = {
    "remote", "work from home", "wfh", "hybrid", "onsite",
    "various locations", "multiple locations",
}
# Country names are excluded from city candidacy too (see parse_city) —
# without this, "Remote, India" would skip "Remote" only to wrongly
# return "India" (a country) as if it were a city.
_NON_CITY_TOKENS = _NON_CITY_TERMS | set(COUNTRIES)


def parse_country(location):
    if not location:
        return "Unknown"
    text = location.lower()
    for c in COUNTRIES:
        if re.search(rf"\b{re.escape(c)}\b", text):
            return _COUNTRY_DISPLAY.get(c, c.title())
    # Fallback: no country name spelled out anywhere, but a US state
    # abbreviation appears as its own segment. Split on "," AND ";" AND
    # "|" — some postings join multiple full locations with semicolons or
    # pipes rather than commas alone (e.g. the "New York City, NY; San
    # Francisco, CA; Seattle, WA" case above). Exact segment match only,
    # not a substring search — avoids a state abbreviation coincidentally
    # appearing inside an unrelated word.
    segments = [s.strip() for s in re.split(r"[,;|]", text)]
    if any(seg in _US_STATE_ABBREVIATIONS for seg in segments):
        return "United States"
    if _US_STATE_RE.search(text) or text.strip() in _US_CITY_ONLY or re.search(r"\bwashington\s*,?\s*d\.?c\.?\b", text):
        return "United States"
    # ISO 3166-1 alpha-2 country-code prefix, e.g. "IN-Pune", "GB-London",
    # "DE-Munich" — confirmed as Snowflake's own Ashby location convention
    # (not a platform-wide Ashby standard: checked the other three Ashby
    # companies already in this file, none use it). Anchored to the very
    # START of the string only, mirroring the US-state-abbreviation check's
    # own "exact segment, not substring" discipline — this is deliberately
    # NOT a general "in" substring match, which would be a real hazard
    # ("in" is one of the most common words in English). Checked for a
    # possible India/Indiana collision (the same class of bug already hit
    # once for SuccessFactors elsewhere in this project): every US posting
    # observed in this dataset uses a different format entirely ("Austin,
    # TX", "US, Remote" — full state suffix or literal "US", never a
    # hyphenated 2-letter PREFIX), so "IN-" specifically was never observed
    # to mean Indiana here.
    if re.match(r"^in-", text):
        return "India"
    return "Unknown"


def parse_city(location):
    """Best-effort: take the first comma-or-slash-separated segment that
    looks like a real city name — not a building/floor code, not a
    work-arrangement descriptor (Remote/Hybrid/etc.), not a country name.
    Some Workday locations start with digits ("1401-G-India") — skip
    segments that start with a digit or have fewer than 3 letters.

    Splits on "/" as well as "," — some ATS platforms combine multiple
    location descriptors that way (e.g. "Bengaluru / Remote, India"),
    and without splitting on "/" too, that whole compound string would
    get returned as one awkward value ("Bengaluru / Remote") instead of
    correctly identifying "Bengaluru" as the actual city.

    Falls back to the first non-city term found (e.g. "Remote") if no
    segment looks like a real city at all — that's the honest answer for
    a string like "Remote, India", rather than an empty result or an
    arbitrary pick."""
    if not location:
        return ""
    raw_parts = re.split(r"[,/]", location)
    parts = [p.strip() for p in raw_parts if p.strip()]
    fallback = None
    for p in parts:
        if p.lower() in _NON_CITY_TOKENS:
            if fallback is None:
                fallback = p
            continue
        letters = sum(c.isalpha() for c in p)
        if letters >= 3 and not re.match(r"^\d", p):
            return p
    return fallback or (parts[0] if parts else location)


def is_india_or_unknown(location):
    """True if the job's country is India, or couldn't be determined at all.
    Used to gate expensive per-job detail-fetches (e.g. fetching a full
    description via a second API call) — skip that extra work for postings
    confidently outside India (this project is India-focused), but never
    skip, and never drop the job itself, just because the country couldn't
    be parsed. Reused by any fetcher that adds a detail-fetch step, not just
    SmartRecruiters."""
    return parse_country(location) in ("India", "Unknown")


def is_workday_location_placeholder(location):
    """A listing's aggregate count is not a location or country signal."""
    return bool(re.fullmatch(r"\s*(?:\d+|multiple|various)\s+locations?\s*", location or "", re.I))


_REMOTE_RE = re.compile(r"\bremote\b|\bwork\s*from\s*home\b|\bwfh\b", re.I)


def is_remote(location):
    """True if the LOCATION string itself signals a remote/WFH posting.

    Deliberately checked as one substring search across the whole raw
    string, not routed through parse_city()'s segment-by-segment city-vs-
    non-city logic — that logic only ever looks at one comma/slash-split
    segment at a time and returns as soon as it finds a real city, which
    silently loses the remote signal for a common real shape like
    "Bengaluru / Remote, India" (parse_city correctly returns "Bengaluru"
    there — the right answer for the city column — but that means city-
    parsing alone can't also answer "is this remote" for a mixed string
    like that). Checking the raw string directly still catches it, and
    also catches dash-joined shapes like "Remote - India" that parse_city's
    comma/slash splitter never even segments.

    Deliberately does NOT look at the job description. Descriptions
    routinely mention "remote" for reasons unrelated to this posting's own
    work arrangement (a benefits blurb about "occasional remote days", an
    unrelated "remote troubleshooting" skill, or even "this role is NOT
    remote") — a bare substring search over description text produces
    exactly the kind of noisy, unreliable match this function exists to
    avoid. The location field is what ATS platforms themselves use to tag
    a posting remote — the one place this is an intentional signal rather
    than incidental wording.

    Deliberately does NOT count "hybrid"/"onsite" as remote — those still
    require some in-person presence, which isn't what filtering for
    "remote" is asking for."""
    if not location:
        return False
    return bool(_REMOTE_RE.search(location))


def is_smartrecruiters_india_location(location):
    """Legacy SR rows end in an API country code or normalized India label.

    This check is source-specific: IN elsewhere may denote Indiana. Unknown
    locations are not evidence of India when this API provides country codes.
    """
    if not isinstance(location, str): return False
    return bool(re.search(r"(?:^|,)\s*(?:India|in)\s*(?:\(Remote\))?\s*$",location,re.I))
