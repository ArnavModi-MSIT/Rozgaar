"""
Local job-search UI over db/jobs.db. Upload a resume and jobs are ranked by
sentence-embedding cosine similarity (core/matcher.py) instead of a
hardcoded keyword score — related-but-not-identical roles (e.g. a resume
listing SQL/Excel matching a Python/ML posting) still score reasonably,
not just exact keyword hits. Location/seniority/city/country are UI
filters, not scrape-time filters — run.py saves everything; you narrow
down here instead. Jobs can be dismissed (applied / not interested) from
here too — that write persists to jobs.db so they stay hidden across
restarts.

Performance note: resume scoring (embeddings over the whole job pool) is
computed ONCE per resume upload and cached in session_state, not
recomputed on every Streamlit rerun (which happens on every filter change,
checkbox click, etc.) — recomputing it every rerun was the main source of
lag. The job list is also paginated rather than rendering every match at
once, which was the other main cost with 1000+ matches.

Job-pool embeddings are ALSO cached separately from the resume's own
embedding (see core/matcher.py's embed_jobs_incremental()) — they don't
depend on the resume at all, only on the job pool, so re-uploading a
tweaked resume only re-embeds that one short string instead of
re-embedding every job in the pool again. The cache is per-job-id and
content-hash-based, not a single whole-pool fingerprint — dismissing a
few jobs, or a handful of new postings from run.py, only touches those
specific jobs' embeddings, never the entire pool.

Run from project root:  streamlit run ui/app.py
"""

import hashlib
import os
import sys
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import streamlit as st

import config
from core.experience import extract_experience_sentences
from core.location import is_remote, parse_city, parse_country
from core.matcher import embed_jobs_incremental, load_embedding_cache, rank_by_resume, save_embedding_cache
from core.resume_text import extract_text
from core.skills import build_patterns, extract_skills, skill_overlap
from core.storage import (
    add_custom_skill, get_custom_skills, get_resume_skill_override, init_db,
    mark_dismissed, mark_dismissed_bulk, remove_custom_skill,
    save_resume_skill_override,
)

DB_PATH = "db/jobs.db"
# Same reasoning as run.py — fresh clones won't have db/ at all, and
# someone might open the UI before ever running run.py first.
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
PAGE_SIZE = 25

st.set_page_config(page_title="Job Intel", layout="wide")

# Runs the `dismissed`/`category` column migrations if this db predates
# them. Cheap no-op on every rerun once the columns exist. Connection
# explicitly closed — `with sqlite3.connect(...)` only manages the
# transaction (commit/rollback), it does NOT close the connection, a
# common sqlite3 gotcha.
_init_conn = sqlite3.connect(DB_PATH)
try:
    init_db(_init_conn)
    # Loaded fresh each rerun — cheap (single small table query), and
    # needs to reflect any add/remove from the skill editor immediately,
    # not just after a cache TTL expires.
    custom_skills = get_custom_skills(_init_conn)
finally:
    _init_conn.close()

skill_patterns = build_patterns(custom_skills)


def dismiss_jobs_over_experience(conn, jobs_df, max_years):
    """Bulk-dismisses every job in jobs_df requiring MORE than max_years
    of experience. Jobs where experience_years is unknown (-1 — extraction
    found nothing in the description, see core/experience.py) are
    deliberately left untouched: "unknown" isn't evidence a job needs too
    much experience, so it shouldn't get removed just because it couldn't
    be determined. Returns the number of jobs dismissed."""
    to_dismiss = jobs_df[(jobs_df["experience_years"] >= 0) & (jobs_df["experience_years"] > max_years)]
    if to_dismiss.empty:
        return 0
    return mark_dismissed_bulk(conn, to_dismiss["id"].tolist())


@st.cache_data(ttl=30)
def load_jobs():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM jobs WHERE dismissed = 0 ORDER BY first_seen DESC", conn)
    conn.close()
    if not df.empty:
        df["first_seen"] = pd.to_datetime(df["first_seen"], unit="s")
        # Derived, not stored — location text is inconsistent across ATS
        # platforms, so parse fresh each load rather than baking a
        # possibly-wrong guess into the database.
        df["country"] = df["location"].apply(parse_country)
        df["city"] = df["location"].apply(parse_city)
        # Location-type flags backing the Remote/Delhi NCR/India filters
        # below — computed once here (cached alongside the rest of the
        # frame) rather than re-run on every filter interaction.
        df["is_remote"] = df["location"].apply(is_remote)
        df["is_ncr"] = df["location"].fillna("").apply(lambda loc: bool(config.LOCATION.search(loc)))
        # "India" here means the same thing run.py's save-time filter
        # already means (is_india_or_unknown) — confirmed India OR a
        # location string that couldn't be parsed at all. Excluding
        # Unknown would hide real India postings just because their raw
        # location text (e.g. a Workday building/floor code) didn't parse
        # cleanly; confidently-non-India rows never reach this db at all
        # (see run.py), so "Unknown" here is never actually a different
        # country slipping through.
        df["is_india"] = df["country"].isin(["India", "Unknown"])
        # skills is nullable in the DB (NULL = "not extracted yet" — e.g.
        # an interrupted run that saved jobs but didn't reach the skill
        # extraction step). Loaded into pandas that's NaN, which is
        # truthy in Python — an unguarded `if row.get("skills")` below
        # would pass, then crash calling .split() on a float. Normalize
        # to "" here instead of scattering NaN-checks through the render code.
        df["skills"] = df["skills"].fillna("")
        df["category"] = df["category"].fillna("")
        # experience_years: NULL means "not processed yet" (e.g. an
        # interrupted run.py pass) — collapse it into the same -1 "unknown"
        # sentinel core/experience.py + storage.py already use for
        # "processed, nothing found", so the UI only needs to handle one
        # unknown case instead of two.
        df["experience_years"] = pd.to_numeric(df["experience_years"], errors="coerce").fillna(-1).astype(int)
    return df


df = load_jobs()

# Ids dismissed during this session but not yet reflected in a fresh
# load_jobs() read — see render_job_section()'s checkbox handling below for
# why: removing a row from the visible list the instant it's checked forces
# a full re-query + re-filter + re-render, which visibly reflows every
# posting below it. Marking locally instead (checked + struck-through, but
# still in place) avoids that; the row actually drops out of the list once
# load_jobs()'s cache is cleared, which happens on page navigation (see the
# page number widget's on_change below) or the cache's own 30s TTL.
if "locally_dismissed" not in st.session_state:
    st.session_state["locally_dismissed"] = set()

st.title("Job Intel — Local Search")

if df.empty:
    st.warning("No jobs in the database yet. Run `python run.py` first.")
    st.stop()

# Job-pool embeddings, cached independently of the resume — see
# core/matcher.py's embed_jobs_incremental(). Per-job-id + content-hash
# based, not a single whole-pool fingerprint — that distinction matters:
# a whole-pool hash means ANY change (even dismissing 2-3 jobs, which
# shrinks the pool once load_jobs()'s cache TTL expires) invalidates
# everything, forcing a full re-embed of the entire remaining pool. Per-
# job caching means removing rows costs nothing and adding rows only
# costs those specific new embeddings — this runs on every rerun, but is
# cheap (dict lookups + hashing, no model inference) whenever nothing
# actually changed, so there's no need to gate it behind a "did the pool
# change" check first.
if "embedding_cache" not in st.session_state:
    st.session_state["embedding_cache"] = load_embedding_cache()

with st.spinner("Updating job embeddings (only new/changed jobs, not the whole pool)..."):
    job_embeddings, updated_cache, num_new = embed_jobs_incremental(df, st.session_state["embedding_cache"])
if num_new:
    # Only persist to disk when something actually changed — avoids an
    # unnecessary disk write on every ordinary rerun where nothing needed
    # embedding at all.
    save_embedding_cache(updated_cache)
st.session_state["embedding_cache"] = updated_cache
st.session_state["job_embeddings"] = job_embeddings
st.session_state["job_embeddings_df"] = df

# --- Resume upload -------------------------------------------------------------
st.sidebar.header("Resume")
resume_file = st.sidebar.file_uploader("Upload resume (pdf, docx, txt)", type=["pdf", "docx", "txt"])

# Scoring is only recomputed when the resume actually changes, not on
# every rerun — see module docstring. Keyed by content hash, not
# filename+size: two edits could coincidentally produce the same size
# under the same filename, which would silently reuse stale scoring.
# getvalue() reads without moving the stream position, so this doesn't
# interfere with extract_text()'s later .read() call on the same file.
resume_key = hashlib.sha256(resume_file.getvalue()).hexdigest() if resume_file is not None else None

if resume_key and st.session_state.get("resume_key") != resume_key:
    with st.spinner("Reading resume..."):
        try:
            resume_text = extract_text(resume_file)
        except Exception as e:
            st.sidebar.error(f"Couldn't read resume: {e}")
            resume_text = ""
    st.session_state["resume_key"] = resume_key
    st.session_state["resume_text"] = resume_text
    if resume_text.strip():
        auto_skills = extract_skills(resume_text, patterns=skill_patterns)
        # A previously-saved correction for THIS exact resume (by content
        # hash) takes priority over the raw auto-extraction — lets manual
        # fixes from an earlier session persist across restarts instead
        # of needing to be redone every time the same resume is uploaded.
        override_conn = sqlite3.connect(DB_PATH)
        try:
            saved_override = get_resume_skill_override(override_conn, resume_key)
        finally:
            override_conn.close()
        effective_skills = saved_override if saved_override is not None else auto_skills
        st.session_state["resume_skills"] = effective_skills
        with st.spinner("Scoring jobs against resume..."):
            st.session_state["scored_df"] = rank_by_resume(
                st.session_state["job_embeddings_df"],
                resume_text,
                job_embeddings=st.session_state["job_embeddings"],
                resume_skills=effective_skills,
            )
    else:
        st.session_state["scored_df"] = None
        st.session_state["resume_skills"] = set()
elif resume_key is None:
    st.session_state.pop("resume_key", None)
    st.session_state.pop("resume_text", None)
    st.session_state.pop("scored_df", None)
    st.session_state.pop("resume_skills", None)

resume_text = st.session_state.get("resume_text", "")
scored_df = st.session_state.get("scored_df")
resume_skills = st.session_state.get("resume_skills", set())

if resume_text.strip():
    st.sidebar.success(f"Resume loaded ({len(resume_text.split())} words)")
elif resume_file is not None:
    st.sidebar.warning("No text could be extracted from that file.")

# --- Your resume's skills ---------------------------------------------------------
# What actually got extracted from THIS resume, editable — the keyword
# regex can miss a real skill (unusual phrasing) or catch a false
# positive (a word that happens to match but isn't really a skill claim).
# Edits are saved per-resume (keyed by content hash) and take effect on
# scoring immediately, not just in this display.
if resume_text.strip():
    with st.sidebar.expander(f"Your resume's skills ({len(resume_skills)})", expanded=True):
        st.caption(
            "What was detected from your resume. Remove a false positive, "
            "or add a real skill the extractor missed — saved for this "
            "resume file and applied to match scoring right away."
        )
        if resume_skills:
            for skill in sorted(resume_skills):
                col1, col2 = st.columns([4, 1])
                col1.write(skill)
                if col2.button("✕", key=f"remove_resume_skill_{skill}"):
                    updated = resume_skills - {skill}
                    override_conn = sqlite3.connect(DB_PATH)
                    try:
                        save_resume_skill_override(override_conn, resume_key, updated)
                    finally:
                        override_conn.close()
                    st.session_state["resume_skills"] = updated
                    st.session_state["scored_df"] = rank_by_resume(
                        st.session_state["job_embeddings_df"],
                        resume_text,
                        job_embeddings=st.session_state["job_embeddings"],
                        resume_skills=updated,
                    )
                    st.rerun()
        else:
            st.caption("No skills detected.")

        new_resume_skill = st.text_input(
            "Add a skill", key="new_resume_skill_input",
            label_visibility="collapsed", placeholder="e.g. Snowflake SQL",
        )
        if st.button("Add", key="add_resume_skill_btn") and new_resume_skill.strip():
            skill_to_add = new_resume_skill.strip().lower()
            updated = resume_skills | {skill_to_add}
            override_conn = sqlite3.connect(DB_PATH)
            try:
                save_resume_skill_override(override_conn, resume_key, updated)
            finally:
                override_conn.close()
            st.session_state["resume_skills"] = updated
            st.session_state["scored_df"] = rank_by_resume(
                st.session_state["job_embeddings_df"],
                resume_text,
                job_embeddings=st.session_state["job_embeddings"],
                resume_skills=updated,
            )
            st.toast(f"Added: {skill_to_add!r}")
            st.rerun()

        st.caption(
            "Note: a skill you add here only affects scoring against jobs "
            "whose OWN description also has that exact keyword recognized "
            "— see 'Custom skill keywords' below to make a new keyword "
            "recognizable in job postings too, not just your resume."
        )

# --- Custom skill keywords -------------------------------------------------------
# Extends core/skills.py's built-in SKILLS list without editing the source
# file. Adding/removing takes effect immediately for resume matching (see
# below), but NOT retroactively for jobs already sitting in the DB — their
# stored `skills` column was populated by a past run.py pass under the OLD
# keyword list, and only get_unskilled()/process_backlog() (run.py) ever
# re-derives it, never this UI. Said plainly in the caption so this isn't
# a silent gap.
with st.sidebar.expander(f"Custom skill keywords ({len(custom_skills)})"):
    st.caption(
        "Extends the built-in skill list. Takes effect immediately for "
        "your resume, but jobs already in the database keep their old "
        "skill data until you run `python run.py --reprocess-skills`."
    )
    new_skill = st.text_input(
        "Add a skill keyword", key="new_custom_skill_input",
        label_visibility="collapsed", placeholder="e.g. Snowflake SQL",
    )
    if st.button("Add", key="add_custom_skill_btn") and new_skill.strip():
        skill_conn = sqlite3.connect(DB_PATH)
        try:
            added = add_custom_skill(skill_conn, new_skill)
        finally:
            skill_conn.close()
        if added:
            # Forces the existing resume-change-detection block (above) to
            # treat this as if a new resume were uploaded — reuses that
            # logic to fully recompute resume_skills AND scored_df with
            # the updated skill set, rather than duplicating the recompute
            # logic here.
            st.session_state.pop("resume_key", None)
            st.toast(f"Added skill: {new_skill.strip().lower()!r}")
            st.rerun()

    if custom_skills:
        st.caption("Current custom skills:")
        for skill in sorted(custom_skills):
            col1, col2 = st.columns([4, 1])
            col1.write(skill)
            if col2.button("✕", key=f"remove_skill_{skill}"):
                skill_conn = sqlite3.connect(DB_PATH)
                try:
                    remove_custom_skill(skill_conn, skill)
                finally:
                    skill_conn.close()
                st.session_state.pop("resume_key", None)
                st.toast(f"Removed skill: {skill!r}")
                st.rerun()

base_df = scored_df if scored_df is not None else df

# --- Filters ---------------------------------------------------------------------
# Company/City-text/Hide-Senior stayed minimal per an earlier explicit
# request; Source/Category/Experience/Posted-within/Search-text filters
# are still removed entirely. Remote/Delhi NCR/India were added back as a
# dedicated three-way location filter (see is_remote/is_ncr/is_india below)
# — a free-text search over `location` alone couldn't answer "is this
# remote" reliably (many remote postings' location string is a compound
# shape like "Bengaluru / Remote, India" or "Remote - India" that a plain
# substring match handles inconsistently), and description text is too
# noisy for this (see core/location.py's is_remote() docstring for why
# that was tried and deliberately abandoned). Resume match threshold is
# fixed at the backend (see MIN_MATCH_THRESHOLD below), not a UI control.
st.sidebar.header("Filters")

location_text = st.sidebar.text_input(
    "City / State contains", placeholder="e.g. Delhi, Gurugram, Noida"
)

st.sidebar.caption("Location type (checking more than one shows either match)")
lt1, lt2, lt3 = st.sidebar.columns(3)
show_remote = lt1.checkbox("Remote", value=False)
show_ncr = lt2.checkbox("Delhi NCR", value=False)
show_india = lt3.checkbox("India", value=False, help="Anywhere in India, not just Delhi NCR.")

hide_senior = st.sidebar.checkbox("Hide senior/lead/manager-level titles", value=False)

# Same live-filter treatment as hide_senior above — previously the ONLY
# way to act on experience_years was the permanent "Dismiss N job(s)..."
# button further down, which does nothing until clicked. That meant a
# job requiring 3+ years stayed visible in every normal view, with no
# way to just hide it without also permanently marking it dismissed in
# the db. This checkbox is the missing non-destructive equivalent —
# reversible, applied live, uncheck it and those jobs reappear.
#
# Threshold lowered from 2 to 0 (i.e. hide anything requiring 1+ years,
# not just 3+) and default flipped to ON — per explicit request: this is
# a college student's board, targeting fresher/0-experience roles as the
# standing default, not an occasional filter they'd have to remember to
# toggle on each session. Still a real checkbox, not a hardcoded rule —
# uncheck it to see everything again.
EXPERIENCE_DISMISS_THRESHOLD = 0
hide_high_experience = st.sidebar.checkbox(
    f"Hide jobs needing {EXPERIENCE_DISMISS_THRESHOLD + 1}+ years experience", value=True
)

# Fixed at the backend rather than a user-adjustable slider, per explicit
# request — every resume-scored view is filtered to match_pct >= 20
# automatically, with no UI control to change it.
MIN_MATCH_THRESHOLD = 20
min_match = MIN_MATCH_THRESHOLD if resume_text.strip() else 0

# --- Bulk-dismiss jobs below match threshold ------------------------------------
# Sub-threshold jobs are already hidden from every view (see the match_pct
# filter below) — but they still sit in the DB and get re-evaluated on
# every load, forever, unless something actually dismisses them. This
# lets you mark all of them dismissed in one action instead of them
# silently accumulating indefinitely.
if resume_text.strip() and "match_pct" in base_df.columns:
    below_threshold = base_df[base_df["match_pct"] < MIN_MATCH_THRESHOLD]
    if not below_threshold.empty:
        if st.sidebar.button(
            f"Dismiss {len(below_threshold)} job(s) below {MIN_MATCH_THRESHOLD}% match",
            help="Permanently marks every job currently scoring below the "
                 "match threshold as dismissed — same as checking 'Remove' "
                 "on each one individually, just done in one action.",
        ):
            dismiss_conn = sqlite3.connect(DB_PATH)
            try:
                count = mark_dismissed_bulk(dismiss_conn, below_threshold["id"].tolist())
            finally:
                dismiss_conn.close()
            # Unlike the single-job dismiss checkbox (which deliberately
            # avoids an immediate refresh to prevent the list reflowing on
            # every click), this IS meant to be an immediate, visible bulk
            # change — clearing the cache and rerunning right away is the
            # correct behavior here, not an oversight.
            load_jobs.clear()
            st.toast(f"Dismissed {count} job(s) below {MIN_MATCH_THRESHOLD}% match.")
            st.rerun()

# --- Bulk-dismiss senior/lead/manager-level jobs --------------------------------
# Same pattern as the match-threshold dismiss above — these are already
# hidden from view whenever "Hide senior/lead/manager-level titles" is
# checked, but stay in the DB and get re-filtered on every load unless
# actually dismissed. Doesn't depend on a resume being loaded (unlike the
# match-threshold button above), since this filter works title-only.
if hide_senior:
    senior_jobs = base_df[base_df["title"].str.contains(config.EXCLUDE_SENIOR, na=False)]
    if not senior_jobs.empty:
        if st.sidebar.button(
            f"Dismiss {len(senior_jobs)} senior/lead/manager-level job(s)",
            help="Permanently marks every job matching the senior/lead/manager "
                 "title filter as dismissed — same as checking 'Remove' on each "
                 "one individually, just done in one action.",
        ):
            dismiss_conn = sqlite3.connect(DB_PATH)
            try:
                count = mark_dismissed_bulk(dismiss_conn, senior_jobs["id"].tolist())
            finally:
                dismiss_conn.close()
            load_jobs.clear()
            st.toast(f"Dismissed {count} senior/lead/manager-level job(s).")
            st.rerun()

# --- Bulk-dismiss jobs requiring more than 2 years experience -------------------
# Uses core/experience.py's already-extracted experience_years. Jobs where
# the requirement is unknown are deliberately NOT touched — see
# dismiss_jobs_over_experience()'s docstring above. Doesn't depend on a
# resume being loaded, since experience_years is a property of the job
# itself, not of any match scoring. PERMANENT, unlike hide_high_experience
# above — this marks matching jobs dismissed in the db forever (same
# "live filter vs. one-click permanent cleanup" pairing hide_senior /
# the senior-jobs dismiss button below already use).
high_experience_jobs = base_df[
    (base_df["experience_years"] >= 0) & (base_df["experience_years"] > EXPERIENCE_DISMISS_THRESHOLD)
]
if not high_experience_jobs.empty:
    if st.sidebar.button(
        f"Dismiss {len(high_experience_jobs)} job(s) needing {EXPERIENCE_DISMISS_THRESHOLD + 1}+ years experience",
        help=f"Permanently marks every job requiring more than "
             f"{EXPERIENCE_DISMISS_THRESHOLD} years of experience as dismissed. "
             "Jobs where the requirement couldn't be determined from the "
             "description are left alone, not dismissed.",
    ):
        dismiss_conn = sqlite3.connect(DB_PATH)
        try:
            count = dismiss_jobs_over_experience(dismiss_conn, base_df, EXPERIENCE_DISMISS_THRESHOLD)
        finally:
            dismiss_conn.close()
        load_jobs.clear()
        st.toast(f"Dismissed {count} job(s) needing {EXPERIENCE_DISMISS_THRESHOLD + 1}+ years experience.")
        st.rerun()

# --- Apply filters (cheap — just pandas boolean masks on an already-scored df) --
filtered = base_df.copy()

if location_text:
    # Matched against the raw location string, not just the parsed city
    # column — more forgiving of parsing quirks (e.g. "New Delhi" still
    # matches typing "Delhi" even if parse_city() picked a different
    # token as the canonical city). regex=False since this is free-text
    # user input, not a regex the person is expected to write — with
    # regex=True (the default), something as ordinary as typing "L4)"
    # would crash the page on an unbalanced-parenthesis compile error.
    filtered = filtered[filtered["location"].str.contains(location_text, case=False, na=False, regex=False)]

# Remote/Delhi NCR/India are OR'd together (checking more than one WIDENS
# the result — "show me anything remote OR in NCR OR anywhere in India"),
# then that combined set is AND'd against every other active filter above/
# below, same as every other filter in this section. Unchecked = no
# restriction from this row at all, same as today's behavior before these
# existed.
selected_location_types = [show_remote, show_ncr, show_india]
if any(selected_location_types):
    location_mask = pd.Series(False, index=filtered.index)
    if show_remote:
        location_mask |= filtered["is_remote"]
    if show_ncr:
        location_mask |= filtered["is_ncr"]
    if show_india:
        location_mask |= filtered["is_india"]
    filtered = filtered[location_mask]

if hide_senior:
    filtered = filtered[~filtered["title"].str.contains(config.EXCLUDE_SENIOR, na=False)]

if hide_high_experience:
    # experience_years == -1 (unknown) is deliberately kept, not hidden —
    # same "don't drop just because it couldn't be determined" rule
    # dismiss_jobs_over_experience() already follows.
    filtered = filtered[
        ~((filtered["experience_years"] >= 0) & (filtered["experience_years"] > EXPERIENCE_DISMISS_THRESHOLD))
    ]

if resume_text.strip() and "match_pct" in filtered.columns:
    filtered = filtered[filtered["match_pct"] >= min_match]
    filtered = filtered.sort_values("match_pct", ascending=False)
else:
    filtered = filtered.sort_values("first_seen", ascending=False)

# --- Summary -------------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Matching jobs", len(filtered))
c2.metric("Companies", filtered["company"].nunique())
c3.metric("Total in DB", len(df))

st.divider()

# Used by render_job_section() below to detect filter changes and reset
# pagination to page 1 — computed once here since both tabs need it.
filter_signature = (
    location_text, show_remote, show_ncr, show_india,
    hide_senior, hide_high_experience,
)

# --- Analytics (basic, shown once, not duplicated per tab) -----------------------
with st.expander("Analytics", expanded=False):
    a1, a2, a3 = st.columns(3)
    with a1:
        st.subheader("Jobs by company")
        counts = filtered["company"].value_counts()
        if not counts.empty:
            st.bar_chart(counts)
    with a2:
        st.subheader("Jobs by source")
        counts = filtered["source"].value_counts()
        if not counts.empty:
            st.bar_chart(counts)
    with a3:
        st.subheader("Jobs by category")
        counts = filtered["category"].value_counts()
        if not counts.empty:
            st.bar_chart(counts)

st.divider()

if not resume_text.strip():
    st.info("Upload your resume in the sidebar to rank jobs by how well they match it.")


def render_job_section(section_df, key_prefix):
    """Renders paginated job cards for section_df. key_prefix keeps this
    section's pagination state independent from any other section's —
    without it, two tabs sharing one 'page' key would desync (jumping to
    page 5 in one tab would also jump the other tab to page 5)."""
    total = len(section_df)
    total_pages = max(1, (total - 1) // PAGE_SIZE + 1)
    page_key = f"{key_prefix}_page"
    sig_key = f"{key_prefix}_filter_signature"

    # Reset to page 1 whenever the filter selection changes — same
    # reasoning as before, now tracked per-section.
    if st.session_state.get(sig_key) != filter_signature:
        st.session_state[page_key] = 1
        st.session_state[sig_key] = filter_signature

    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    st.session_state[page_key] = min(st.session_state[page_key], total_pages)

    def _on_page_change():
        # Runs before the script reruns (Streamlit's on_change contract) —
        # clearing here means the NEXT load_jobs() call (top of script, on
        # the rerun this triggers) reflects any dismissals made while the
        # user was sitting on the previous page.
        load_jobs.clear()

    _, top_c, _ = st.columns([1, 2, 1])
    with top_c:
        st.session_state[page_key] = st.number_input(
            f"Page (of {total_pages})", min_value=1, max_value=total_pages,
            value=st.session_state[page_key], step=1, key=f"{key_prefix}_page_input",
            on_change=_on_page_change,
        )

    start = (st.session_state[page_key] - 1) * PAGE_SIZE
    page_df = section_df.iloc[start:start + PAGE_SIZE]
    st.caption(f"Showing {start + 1}-{min(start + PAGE_SIZE, total)} of {total}")

    for _, row in page_df.iterrows():
        job_id_ = row["id"]
        is_dismissed = job_id_ in st.session_state["locally_dismissed"]
        with st.container(border=True):
            left, right = st.columns([5, 1])
            with left:
                title_md = f"### [{row['title']}]({row['url']})"
                if is_dismissed:
                    title_md = f"### ~~{row['title']}~~"
                st.markdown(title_md)
                st.write(f"**{row['company'].title()}** · {row['location'] or 'N/A'} · via {row['source']}"
                         + (f" · {row['category']}" if row.get("category") else ""))
                exp_years = row.get("experience_years", -1)
                if exp_years == 0:
                    st.caption("Experience: fresher-friendly (0 years stated)")
                elif exp_years > 0:
                    st.caption(f"Experience: {exp_years}+ year(s) required")
                relevant_sentences = extract_experience_sentences(row["description"])
                if relevant_sentences:
                    with st.expander("Experience-relevant lines"):
                        for sentence in relevant_sentences:
                            st.text(sentence)
                elif row["description"]:
                    st.caption("No numbers or \"experience\" mentions found in the description.")
                if resume_skills and row.get("skills"):
                    job_skills = set(row["skills"].split(",")) if row["skills"] else set()
                    matched, missing, pct = skill_overlap(resume_skills, job_skills)
                    if pct is not None:
                        label = f"Skills matched: {len(matched)}/{len(job_skills)} ({pct}%)"
                        detail = f"Have: {', '.join(sorted(matched)) or '—'}  ·  Missing: {', '.join(sorted(missing)) or '—'}"
                        st.caption(f"{label} — {detail}")
                # key includes key_prefix — the same job could otherwise
                # appear in more than one rendering context, and Streamlit
                # requires unique widget keys even across different tabs
                # in the same run.
                checked = st.checkbox(
                    "Remove (applied / not interested)",
                    value=is_dismissed,
                    disabled=is_dismissed,
                    key=f"{key_prefix}_dismiss_{job_id_}",
                )
                if checked and not is_dismissed:
                    dismiss_conn = sqlite3.connect(DB_PATH)
                    try:
                        mark_dismissed(dismiss_conn, job_id_)
                    finally:
                        dismiss_conn.close()
                    # Marked locally only — NOT removed from section_df/
                    # page_df and NOT clearing load_jobs' cache here. Doing
                    # either immediately is what caused every posting below
                    # this one to visibly reflow up a slot on every click.
                    # It'll actually drop out of the list on the next page
                    # load (see _on_page_change above) or once load_jobs'
                    # cache naturally expires.
                    st.session_state["locally_dismissed"].add(job_id_)
                    st.rerun()  # cheap redraw only — no cache clear, no data mutation
                if is_dismissed:
                    st.caption("Marked — will be removed from the list when you change page.")
            with right:
                if resume_text.strip() and "match_pct" in row:
                    # "Match Score", not "Match %" — this is a blended
                    # heuristic (semantic similarity + skill overlap, see
                    # core/matcher.py), not a calibrated probability of
                    # fit. The % framing implied more precision than the
                    # underlying number actually has.
                    st.metric("Match Score", f"{row['match_pct']:.0f}")
                st.caption(row["first_seen"].strftime("%Y-%m-%d"))


if filtered.empty:
    st.info("No jobs match your current filters.")
else:
    render_job_section(filtered, "all")
