"""
SQLite storage: the `jobs` table is now the actual database (title, company,
location, url, description, score, source, first_seen, dismissed) —
previously `seen` only stored company/title/url for Telegram dedup purposes.
`job_id` is unchanged from bot.py; new-job detection is now a preloaded
in-memory set (load_existing_ids) rather than a per-job query.
"""

import hashlib
import sqlite3
import time

from core.dedup import dedup_key
from core.location import parse_country


def _add_column_if_missing(conn, alter_sql):
    """Runs an ALTER TABLE ... ADD COLUMN, treating 'column already
    exists' as the expected no-op it is on a previously-migrated db —
    but re-raising anything else. A bare `except OperationalError: pass`
    (the previous pattern here) would also silently swallow a locked
    database, a malformed file, a permissions problem, or a genuine SQL
    syntax error, none of which should ever be treated as 'oh, already
    migrated, ignore it' — those are real problems that deserve to
    surface, not vanish."""
    try:
        conn.execute(alter_sql)
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise


def init_db(conn):
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS jobs (
               id TEXT PRIMARY KEY,
               company TEXT, title TEXT, location TEXT, url TEXT,
               description TEXT, source TEXT, score INTEGER,
               first_seen INTEGER
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS run_stats (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               run_id INTEGER,
               timestamp INTEGER,
               platform TEXT,
               jobs_fetched INTEGER,
               jobs_matched INTEGER,
               jobs_saved INTEGER,
               runtime_seconds REAL,
               status TEXT DEFAULT 'ok',
               error TEXT
           )"""
    )
    # User-added skill keywords (via API endpoints) — extends,
    # never replaces, core/skills.py's built-in SKILLS list. Kept in the
    # DB rather than editing skills.py's source at runtime, which would
    # be fragile and mix config data with application code.
    conn.execute(
        """CREATE TABLE IF NOT EXISTS custom_skills (
               skill TEXT PRIMARY KEY
           )"""
    )
    # Per-resume manual skill corrections (see the React resume skill
    # editor) — a resume's AUTO-extracted skills can have false positives
    # (regex matched something it shouldn't have) or misses (a real skill
    # phrased in a way the regex doesn't catch); this stores the person's
    # corrected final set, keyed by resume_key (sha256 of the uploaded
    # file's bytes — same key the API uses to detect resume
    # changes), so edits persist across restarts for the same resume file
    # without needing to redo them every session.
    conn.execute(
        """CREATE TABLE IF NOT EXISTS resume_skill_overrides (
               resume_key TEXT PRIMARY KEY,
               skills TEXT
           )"""
    )
    # Migration: existing jobs.db files (created before this column existed)
    # won't have `dismissed` — add it so "remove from list"
    # in the UI can persist across restarts instead of just hiding for the
    # current session.
    _add_column_if_missing(conn, "ALTER TABLE jobs ADD COLUMN dismissed INTEGER DEFAULT 0")
    # Migration: category is filled in by core/classify.py after saving —
    # NULL means "not classified yet" (either a pre-existing row from before
    # this feature, or newly saved this run and classification hasn't run
    # yet), which is what get_unclassified() looks for.
    _add_column_if_missing(conn, "ALTER TABLE jobs ADD COLUMN category TEXT")
    # Migration: skills is filled in by core/skills.py after saving — a
    # comma-separated string of recognized skill keywords found in the
    # job's title+description. NULL means "not extracted yet".
    _add_column_if_missing(conn, "ALTER TABLE jobs ADD COLUMN skills TEXT")
    # Migration: status distinguishes "platform crashed" from "platform
    # returned 0 jobs" in run_stats — previously a crashed platform had no
    # row at all for that run, indistinguishable from an empty result.
    _add_column_if_missing(conn, "ALTER TABLE run_stats ADD COLUMN status TEXT DEFAULT 'ok'")
    _add_column_if_missing(conn, "ALTER TABLE run_stats ADD COLUMN error TEXT")
    # Migration: experience_years is filled in by core/experience.py after
    # saving — the minimum years of experience the posting appears to
    # require, parsed from title+description. Unlike skills/category, 0 is
    # a real, meaningful value here (fresher-friendly), so NULL alone can't
    # double as both "not processed yet" and "processed, nothing found" the
    # way skills' empty-string sentinel does. Convention: NULL = not
    # processed yet (what get_unexperienced() looks for); -1 = processed,
    # no experience requirement could be found in the text (see
    # core/experience.py); >=0 = an actual extracted minimum.
    _add_column_if_missing(conn, "ALTER TABLE jobs ADD COLUMN experience_years INTEGER")
    # Observed again by a successful fetch. Existing rows start with their
    # original discovery time; absence from a fetch is not proof of closure.
    _add_column_if_missing(conn, "ALTER TABLE jobs ADD COLUMN last_seen INTEGER")
    conn.execute("UPDATE jobs SET last_seen = first_seen WHERE last_seen IS NULL")
    conn.commit()


def job_id(job):
    """Prefer the ATS's own posting id (stable across URL/content edits);
    fall back to a hash of company+title+url only if no id is present."""
    if job.get("source_id"):
        return f"{job['company']}:{job['source_id']}"
    raw = f"{job['company']}|{job['title']}|{job['url']}"
    return hashlib.sha1(raw.encode()).hexdigest()


def load_existing_ids(conn):
    """Preloads every job id already in the db as an in-memory set — one
    query, then O(1) membership checks per fetched job in run.py, instead
    of a separate `SELECT 1 FROM jobs WHERE id = ?` round-trip per job
    (the previous is_new()-per-job pattern). Same reasoning as
    load_dedup_keys() below: with several thousand jobs fetched per run,
    that was several thousand individual query round-trips for something
    one bulk query already answers."""
    rows = conn.execute("SELECT id FROM jobs").fetchall()
    return {r[0] for r in rows}


def load_dedup_keys(conn):
    """Preloads dedup keys for every job ever saved (including dismissed
    ones), regardless of `dismissed` status — one query, then O(1) set
    lookups per fetched job in run.py, instead of a DB round-trip or
    fuzzy comparison per job. Catches reposts (same job, new ATS req id)
    that job_id() alone would treat as new.

    Deliberately NOT filtered to dismissed=0: dedup means "have we ever
    seen this posting", which is independent of whether the person marked
    it applied/not-interested. Filtering dismissed rows out here used to
    mean dismissing a job removed it from the dedup memory too — so if it
    got reposted under a new ATS req id (common, see module docstring),
    the repost would pass the dedup check as "new" and silently reappear,
    directly undermining what "dismiss" is supposed to mean. `dismissed`
    should only ever affect what's DISPLAYED (see api/data.py,
    which filters on it) — never whether something counts as
    previously seen.

    Calls dedup_key() rather than reconstructing the tuple format inline —
    the two MUST stay identical or preloaded and newly-computed keys
    silently stop matching."""
    rows = conn.execute("SELECT company, title, location, description FROM jobs").fetchall()
    return {dedup_key(company, title, location, description) for company, title, location, description in rows}


def save_job(conn, jid, job, source):
    # No per-row commit — run.py commits once per source so a large
    # run doesn't pay an fsync per insert.
    # `score` column kept in the schema for compatibility with existing
    # rows/db files but is no longer computed — resume match % is computed
    # live in the UI (core/matcher.py) instead of a static keyword score.
    observed_at = int(time.time())
    conn.execute(
        "INSERT OR IGNORE INTO jobs (id, company, title, location, url, "
        "description, source, score, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (jid, job["company"], job["title"], job.get("location") or "", job["url"],
         job.get("description") or "", source, 0, observed_at, observed_at),
    )


def mark_observed(conn, jid, observed_at):
    """Record a posting seen again by its stable source ID; caller batches commit."""
    conn.execute("UPDATE jobs SET last_seen = ? WHERE id = ?", (observed_at, jid))


def refresh_mastercard_from_workday(conn, jid, job):
    """Replace a matching legacy Phenom row with its richer Workday version."""
    if not job.get("description"):
        return False
    cur = conn.execute(
        """UPDATE jobs SET title = ?, location = ?, url = ?, description = ?,
               source = 'mastercard_workday', category = NULL, skills = NULL,
               experience_years = NULL
           WHERE id = ? AND company = 'mastercard' AND source = 'phenom'""",
        (job["title"], job["location"], job["url"], job["description"], jid),
    )
    return cur.rowcount > 0


def refresh_atlassian_job(conn, jid, job):
    """Correct saved Atlassian links and locations without changing row identity."""
    old = conn.execute(
        "SELECT title, location, url, description FROM jobs WHERE id = ? AND source = 'atlassian'",
        (jid,),
    ).fetchone()
    if old is None:
        return False
    new = (job["title"], job.get("location") or "", job["url"], job.get("description") or "")
    if old == new:
        return False
    reprocess = old[0] != new[0] or old[3] != new[3]
    conn.execute(
        """UPDATE jobs SET title = ?, location = ?, url = ?, description = ?,
               category = CASE WHEN ? THEN NULL ELSE category END,
               skills = CASE WHEN ? THEN NULL ELSE skills END,
               experience_years = CASE WHEN ? THEN NULL ELSE experience_years END
           WHERE id = ?""",
        (*new, reprocess, reprocess, reprocess, jid),
    )
    return True


def mark_dismissed(conn, jid, dismissed=True):
    """Used by the UI's remove button. Committed
    immediately (not batched) since it's a single interactive click, not
    part of a bulk run.py pass."""
    conn.execute("UPDATE jobs SET dismissed = ? WHERE id = ?", (1 if dismissed else 0, jid))
    conn.commit()


def mark_dismissed_bulk(conn, job_ids):
    """Bulk version of mark_dismissed() — one executemany() call instead
    of one UPDATE per job. Used by the UI's 'dismiss all jobs below match
    threshold' button, which can affect hundreds/thousands of rows at
    once; looping individual mark_dismissed() calls would mean that many
    separate commits for no benefit. Returns the number of rows affected."""
    if not job_ids:
        return 0
    conn.executemany("UPDATE jobs SET dismissed = 1 WHERE id = ?", [(jid,) for jid in job_ids])
    conn.commit()
    return len(job_ids)


def get_unclassified(conn):
    """Rows with category IS NULL — either never classified, or saved
    before core/classify.py existed. Returns (id, title, description)
    tuples ready to pass into classify_jobs()."""
    return conn.execute(
        "SELECT id, title, description FROM jobs WHERE category IS NULL"
    ).fetchall()


def update_categories(conn, id_category_pairs):
    """id_category_pairs: list of (job_id, category) tuples. Committed
    immediately — this runs once per run.py pass right after classification,
    not per-row, so a single commit here is fine."""
    conn.executemany(
        "UPDATE jobs SET category = ? WHERE id = ?",
        [(category, jid) for jid, category in id_category_pairs],
    )
    conn.commit()


def get_unskilled(conn):
    """Rows with skills IS NULL — never had extract_skills() run on them
    yet. Returns (id, title, description) tuples ready to pass into
    core.skills.extract_skills()."""
    return conn.execute(
        "SELECT id, title, description FROM jobs WHERE skills IS NULL"
    ).fetchall()


def update_skills(conn, id_skills_pairs):
    """id_skills_pairs: list of (job_id, comma_separated_skills_string)."""
    conn.executemany(
        "UPDATE jobs SET skills = ? WHERE id = ?",
        [(skills, jid) for jid, skills in id_skills_pairs],
    )
    conn.commit()


def get_custom_skills(conn):
    """Returns the set of user-added custom skill keywords (via API endpoints). Passed into core.skills.build_patterns() to extend the
    built-in SKILLS list wherever skill extraction happens."""
    rows = conn.execute("SELECT skill FROM custom_skills").fetchall()
    return {r[0] for r in rows}


def add_custom_skill(conn, skill):
    """Adds one custom skill keyword. Lowercased/stripped before storing —
    core.skills.build_patterns() does its own case-insensitive dedup
    against the built-in list, but normalizing here too keeps the stored
    table itself free of near-duplicate casing variants. Returns False
    (no-op) for an empty/whitespace-only skill."""
    skill = skill.strip().lower()
    if not skill:
        return False
    conn.execute("INSERT OR IGNORE INTO custom_skills (skill) VALUES (?)", (skill,))
    conn.commit()
    return True


def remove_custom_skill(conn, skill):
    conn.execute("DELETE FROM custom_skills WHERE skill = ?", (skill.strip().lower(),))
    conn.commit()


def get_resume_skill_override(conn, resume_key):
    """Returns the saved corrected skill set for this resume (a set of
    strings), or None if no correction has ever been saved for it — None
    is the signal to the caller to fall back to the raw
    auto-extracted skills, distinct from "saved as an empty set" (someone
    deliberately clearing every skill)."""
    row = conn.execute(
        "SELECT skills FROM resume_skill_overrides WHERE resume_key = ?", (resume_key,)
    ).fetchone()
    if row is None:
        return None
    return set(row[0].split(",")) if row[0] else set()


def save_resume_skill_override(conn, resume_key, skills):
    """skills: the FULL corrected set (not a delta) — replaces whatever
    was saved before for this resume_key entirely."""
    skills_str = ",".join(sorted(skills))
    conn.execute(
        "INSERT INTO resume_skill_overrides (resume_key, skills) VALUES (?, ?) "
        "ON CONFLICT(resume_key) DO UPDATE SET skills = excluded.skills",
        (resume_key, skills_str),
    )
    conn.commit()


def reset_skills(conn):
    """Sets skills back to NULL for every row, so the next process_backlog()
    pass (or --process-only / --reprocess-skills) re-derives it for the
    WHOLE dataset — needed because adding a new custom skill via the UI
    doesn't retroactively apply to jobs already processed under the OLD
    skill list; get_unskilled() only picks up rows where skills IS NULL,
    same reasoning as reset_experience_years() above. Only touches
    skills — category/experience_years are left alone. Call via
    `python run.py --reprocess-skills`."""
    cur = conn.execute("UPDATE jobs SET skills = NULL")
    conn.commit()
    return cur.rowcount


def get_unexperienced(conn):
    """Rows with experience_years IS NULL — never had
    core.experience.extract_min_experience() run on them yet. Returns
    (id, title, description) tuples. See init_db()'s migration comment for
    why NULL (not-yet-processed) and -1 (processed, nothing found) are
    distinct sentinels here, unlike skills' single NULL convention."""
    return conn.execute(
        "SELECT id, title, description FROM jobs WHERE experience_years IS NULL"
    ).fetchall()


def get_unprocessed(conn):
    """Single-scan replacement for calling get_unclassified()/
    get_unskilled()/get_unexperienced() separately — each did its own full
    WHERE-column-IS-NULL table scan; this does one scan checking all three
    columns at once and lets the caller (run.py) branch in Python on which
    of category/skills/experience_years a given row is still missing.
    Returns (id, title, description, category, skills, experience_years)
    tuples for every row missing at least one of the three; the caller
    checks each field for None individually since a row can be missing
    just one of them (e.g. classified already but not yet skill-extracted)."""
    return conn.execute(
        "SELECT id, title, description, category, skills, experience_years FROM jobs "
        "WHERE category IS NULL OR skills IS NULL OR experience_years IS NULL"
    ).fetchall()


def update_experience(conn, id_experience_pairs):
    """id_experience_pairs: list of (job_id, years) tuples, where years is
    an int — the caller is responsible for passing -1 (not None) when
    extract_min_experience() found nothing, so these rows don't keep
    getting re-selected by get_unexperienced() on every future run."""
    conn.executemany(
        "UPDATE jobs SET experience_years = ? WHERE id = ?",
        [(years, jid) for jid, years in id_experience_pairs],
    )
    conn.commit()


def reset_experience_years(conn):
    """Sets experience_years back to NULL for every row, so the next
    process_backlog() pass (or --process-only) re-derives it for the
    WHOLE dataset under core/experience.py's current logic, not just
    newly-saved rows. Needed because get_unprocessed()/process_backlog()
    only ever touch rows where experience_years IS NULL — a row already
    processed under an OLDER, less accurate version of the extraction
    heuristic (e.g. before the required-vs-preferred distinction was
    added) stays stuck with that stale value forever otherwise, with no
    automatic way to pick up later improvements to the logic. Only
    touches experience_years — category/skills are left alone, so a
    reprocessing pass after this only re-runs the (cheap) experience
    extraction, not classification or skill extraction too. Call via
    `python run.py --reprocess-experience`."""
    cur = conn.execute("UPDATE jobs SET experience_years = NULL")
    conn.commit()
    return cur.rowcount


def record_stats(conn, run_id, platform, fetched, matched, saved, runtime_seconds, status="ok", error=None):
    conn.execute(
        "INSERT INTO run_stats (run_id, timestamp, platform, jobs_fetched, jobs_matched, "
        "jobs_saved, runtime_seconds, status, error) VALUES (?,?,?,?,?,?,?,?,?)",
        (run_id, int(time.time()), platform, fetched, matched, saved, runtime_seconds, status, error),
    )


def cleanup_old(conn, days=365):
    """Delete rows older than `days`. Not run automatically — call via
    Runs after normal collection; `python run.py --cleanup` also runs it explicitly."""
    cutoff = int(time.time()) - days * 86400
    cur = conn.execute("DELETE FROM jobs WHERE first_seen < ?", (cutoff,))
    conn.commit()
    return cur.rowcount


def prune_non_india(conn):
    """One-time cleanup for rows saved before the India-or-unknown save-time
    filter existed (run.py now skips these going forward, but doesn't touch
    what's already in the db). Deletes rows whose location confidently
    resolves to a non-India country; leaves unparseable/unknown locations
    alone, same rule as the save-time filter. Call via
    `python run.py --prune-non-india`."""
    rows = conn.execute("SELECT id, location FROM jobs").fetchall()
    to_delete = [(rid,) for rid, location in rows if parse_country(location) not in ("India", "Unknown")]
    if to_delete:
        conn.executemany("DELETE FROM jobs WHERE id = ?", to_delete)
        conn.commit()
    return len(to_delete)


def delete_by_source(conn, sources):
    """Delete every row whose `source` column matches any of the given
    values. Generic (not internshala-specific) so it's reusable for any
    future source removal — see run.py's --remove-internshala flag for the
    current use. Committed immediately: this is a deliberate, manual,
    one-time cleanup a person runs themselves, not part of a bulked
    run.py pass."""
    if not sources:
        return 0
    placeholders = ",".join("?" for _ in sources)
    cur = conn.execute(f"DELETE FROM jobs WHERE source IN ({placeholders})", tuple(sources))
    conn.commit()
    return cur.rowcount


def get_oracle_jobs_missing_description(conn):
    """Rows saved via fetchers/oracle.py before its detail-fetch existed —
    source='oracle' and description empty. job_id() builds oracle ids as
    "{company}:{req_id}", so the requisition id is recovered by stripping
    the company prefix rather than needing a separate stored column.
    Returns (job_id, company, req_id) tuples. Used by
    `run.py --refetch-oracle` to backfill without a full re-scrape."""
    rows = conn.execute(
        "SELECT id, company FROM jobs WHERE source = 'oracle' AND (description IS NULL OR description = '')"
    ).fetchall()
    result = []
    for jid, company in rows:
        prefix = f"{company}:"
        if jid.startswith(prefix):
            result.append((jid, company, jid[len(prefix):]))
    return result


def get_workday_jobs_missing_description(conn, company):
    """Rows saved via fetchers/workday.py for a specific company, with an
    empty description — either saved before fetch_details(_filter) was
    enabled for that company, or from a run where the detail-fetch failed.
    Unlike Oracle, Workday's stored source_id isn't the URL path, so the
    externalPath is recovered from the stored `url` column instead.
    Returns (job_id, title, url) tuples — title included so callers (see
    `run.py --refetch-workday`) can re-apply a company's
    fetch_details_filter instead of blindly refetching every empty row,
    which matters a lot for a large employer where "every empty row"
    is ~2000 rows and only a small title-matched subset is meant to ever
    get detail-fetched. Used to backfill without a full re-scrape."""
    return conn.execute(
        "SELECT id, title, url FROM jobs WHERE source = 'workday' AND company = ? "
        "AND (description IS NULL OR description = '')",
        (company,),
    ).fetchall()


def update_descriptions(conn, id_description_pairs):
    """id_description_pairs: list of (job_id, description) tuples."""
    conn.executemany(
        """UPDATE jobs SET description = ?, category = NULL, skills = NULL,
             experience_years = NULL
           WHERE id = ? AND COALESCE(description, '') != ?""",
        [(desc, jid, desc) for jid, desc in id_description_pairs if desc],
    )
    conn.commit()


def refresh_collected_description(conn, jid, job):
    """Refresh nonempty source content while retaining dismissal and timestamps."""
    description = job.get("description")
    if not description:
        return False
    cur = conn.execute(
        """UPDATE jobs SET description = ?, category = NULL, skills = NULL,
               experience_years = NULL
           WHERE id = ? AND COALESCE(description, '') != ?""",
        (description, jid, description),
    )
    return cur.rowcount > 0


def refresh_qualcomm_student(conn, jid, job):
    """Enrich a saved Qualcomm internship without resetting user state."""
    if not job.get("description"):
        return False
    cur = conn.execute(
        """UPDATE jobs SET description = ?, url = ?, source = 'qualcomm_students',
               category = NULL, skills = NULL, experience_years = NULL
           WHERE id = ? AND company = 'qualcomm' AND description != ?""",
        (job["description"], job["url"], jid, job["description"]),
    )
    return cur.rowcount > 0
