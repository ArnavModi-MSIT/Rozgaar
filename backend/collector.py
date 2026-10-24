"""
Job pipeline entrypoint: fetch every platform, dedupe, save postings into
jobs.db, then classify any unclassified rows into a category. India-scoped:
jobs confidently outside India are skipped at save time; jobs whose
location can't be determined are kept (never dropped just because we
couldn't parse it — see core/location.py is_india_or_unknown).

Dedup layers:
  1. job_id() — same ATS req id already seen (exact, cheap)
  2. dedup_key() — matching title, city, full description and posting URL
     under a different source ID (see core/dedup.py)

Run:  python run.py                    (single pass, run manually whenever you want)
      python run.py --process-only     (skip fetching — just run classification/
                                          skills/experience extraction on whatever's
                                          already in jobs.db and still unprocessed;
                                          useful for backfilling after adding a new
                                          extraction feature without a full re-fetch)
      python run.py --reprocess-experience  (force re-derive experience_years for
                                          EVERY job, not just unprocessed ones — use
                                          after core/experience.py's logic changes,
                                          since already-processed rows otherwise keep
                                          whatever value an older version computed
                                          forever; category/skills untouched)
      python run.py --reprocess-skills (force re-extract skills for EVERY job —
                                          use after adding a custom skill keyword
                                          via the UI, since already-processed rows
                                          otherwise never pick up new keywords;
                                          category/experience_years untouched)
      python run.py --cleanup          (delete rows older than 365 days)
      python run.py --prune-non-india  (one-time: delete existing non-India rows)
      python run.py --refetch-oracle   (one-time: backfill missing Oracle descriptions)
      python run.py --refetch-workday <company>  (one-time: backfill missing Workday
                                                    descriptions for one company, e.g. fractal)
      python run.py --remove-internshala  (one-time: delete existing Internshala rows —
                                             source no longer fetched, see fetchers/)
      python run.py --remove-adzuna    (one-time: delete existing Adzuna rows —
                                          source no longer fetched, see fetchers/)
"""

import logging
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

import backend.config as config
from backend.core.source_health import record_company_run
from backend.core.storage import refresh_workday_location
from backend.core.classify import classify_jobs
from backend.core.run_lock import collection_lock
from pathlib import Path
from backend.core.collector import PLATFORMS
from backend.core.dedup import dedup_key
from backend.core.experience import extract_min_experience
from backend.core.location import is_india_or_unknown, is_smartrecruiters_india_location, parse_country
from backend.core.skills import build_patterns, extract_skills
from backend.core.storage import cleanup_old, delete_by_source, get_custom_skills, get_oracle_jobs_missing_description, get_unprocessed, get_workday_jobs_missing_description, init_db, job_id, load_dedup_keys, load_existing_ids, mark_observed, prune_non_india, record_stats, refresh_atlassian_job, refresh_mastercard_from_workday, refresh_qualcomm_student, refresh_collected_description, reset_experience_years, reset_skills, save_job, update_categories, update_descriptions, update_experience, update_skills
from backend.fetchers.oracle import fetch_requisition_detail
from backend.fetchers.workday import fetch_job_detail

log = logging.getLogger("jobbot")

from raambaad.paths import CAREER_DB
DB_PATH = str(CAREER_DB)
# Fresh clones won't have db/ at all — git never tracks empty directories,
# and .gitignore excludes the .db files themselves (personal data, not
# shared). Without this, sqlite3.connect() fails outright on anyone's
# very first run with "unable to open database file".
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

# Every fetcher already accepts a `deadline` (an absolute time.monotonic()
# timestamp) and stops paginating once past it — but run() used to call
# every platform with deadline=None, so none of that plumbing actually did
# anything: a platform with a bug (or just an unusually large posting
# count) could run indefinitely and hold up the whole run. One shared
# deadline, computed once right before all platforms are submitted, caps
# the whole fetch phase without slowing down anything that finishes
# normally — it's a ceiling checked inside each platform's own pagination
# loop, not a throttle. 600s (10 min) default sits comfortably above the
# slowest platform's documented normal runtime (Workday: ~211s for 6
# companies, Akamai-rate-limited) — override via RUN_DEADLINE_SECONDS if
# your company list grows enough to need more headroom.
RUN_DEADLINE_SECONDS = float(os.environ.get("RUN_DEADLINE_SECONDS", 600))


def process_backlog(conn):
    """Runs classification/skill-extraction/experience-extraction on every
    row still missing at least one of the three (see get_unprocessed()).
    Pulled out of run() into its own function so it can also be called
    directly via --process-only, without paying for a full network
    fetch first — useful for backfilling a newly-added extraction feature
    (e.g. core/experience.py) against an existing jobs.db without waiting
    on every platform to re-fetch."""
    # Loaded once per call (not per-job) — user-added custom skills (via
    # API endpoints) extend the built-in SKILLS list for every
    # extraction below.
    skill_patterns = build_patterns(get_custom_skills(conn))

    rows = get_unprocessed(conn)
    if not rows:
        return
    to_classify_ids, to_classify_texts = [], []
    to_skill = []
    to_experience = []
    for jid, title, desc, category, skills, exp_years in rows:
        if category is None:
            to_classify_ids.append(jid)
            to_classify_texts.append((title, desc))
        if skills is None:
            to_skill.append((jid, title, desc))
        if exp_years is None:
            to_experience.append((jid, title, desc))

    if to_classify_ids:
        log.info("classifying %d job(s)...", len(to_classify_ids))
        try:
            categories = classify_jobs(to_classify_texts)
            update_categories(conn, list(zip(to_classify_ids, categories)))
            log.info("classification done")
        except Exception as e:
            # Isolated from skills/experience below on purpose — a failure
            # here (the ML step, most likely to hit an edge case) used to
            # silently abort the whole function before skills/experience
            # ever ran, since all three were one unguarded sequential
            # block. Cheap regex extraction shouldn't be held hostage by
            # the embedding step failing.
            log.exception("classification failed, continuing to skills/experience: %s", e)

    if to_skill:
        log.info("extracting skills for %d job(s)...", len(to_skill))
        try:
            pairs = [
                (jid, ",".join(sorted(extract_skills(f"{title} {desc or ''}", patterns=skill_patterns))))
                for jid, title, desc in to_skill
            ]
            update_skills(conn, pairs)
            log.info("skill extraction done")
        except Exception as e:
            log.exception("skill extraction failed, continuing to experience: %s", e)

    if to_experience:
        # -1 (not None) is written for jobs where nothing could be
        # found, so those rows don't get re-selected by
        # get_unprocessed() on every future run (see storage.py's
        # migration comment for why NULL and -1 are kept as
        # distinct sentinels here, unlike skills' single-NULL
        # approach).
        log.info("extracting experience requirements for %d job(s)...", len(to_experience))
        try:
            pairs = []
            for jid, title, desc in to_experience:
                years = extract_min_experience(desc or "")
                pairs.append((jid, years if years is not None else -1))
            update_experience(conn, pairs)
            log.info("experience extraction done")
        except Exception as e:
            log.exception("experience extraction failed: %s", e)


def run():
    with collection_lock(Path(DB_PATH).with_name(".collection.lock")):
        return _run()


def _run():
    if os.environ.get("JOB_INTEL_OFFLINE") == "1":
        raise RuntimeError("JOB_INTEL_OFFLINE=1 disables collection; use --process-only for saved jobs")
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        dedup_keys = load_dedup_keys(conn)  # loaded once, updated in-memory as we go
        existing_ids = load_existing_ids(conn)  # same pattern — one query
        # instead of a per-job "SELECT 1 FROM jobs WHERE id = ?" round-trip
        run_id = int(time.time() * 1000)  # milliseconds, not seconds — two runs
        # started in the same second would otherwise share a run_id and get
        # merged together in stats.py's grouping.
        fetched = saved = skipped = reposts = non_india = 0
        platforms_run = []

        # Platforms are fetched CONCURRENTLY — previously strictly serial,
        # one at a time, "so per-platform stats can be recorded." But stats
        # only need to be RECORDED per platform, not FETCHED per platform;
        # nothing about them requires platform N to finish before platform
        # N+1 starts. This is the exact same pattern every individual
        # fetcher already uses internally (fetchers/oracle.py, phenom.py,
        # etc. — ThreadPoolExecutor, submit every task upfront, iterate in
        # submission order calling .result()) — just applied one level up,
        # across platforms instead of within one. Workday alone is
        # documented at 211s for 6 companies (Akamai rate-limiting) and was
        # sitting in the same serial chain as every fast platform — this
        # was the single biggest lever on total run time. DB writes
        # themselves stay fully sequential below (only the network fetch
        # overlaps), so there's no sqlite3 thread-safety concern at all.
        with ThreadPoolExecutor(max_workers=len(PLATFORMS)) as pool:
            # One shared deadline for every platform — see RUN_DEADLINE_SECONDS
            # above. Computed here (not earlier) so the budget starts from
            # the moment fetching actually begins, not from process startup.
            deadline = time.monotonic() + RUN_DEADLINE_SECONDS
            # start captured per-platform at submission (not inside the
            # fetch call) so runtime_seconds below still reflects each
            # platform's own fetch duration, same meaning as before —
            # threads run genuinely concurrently, so a fast platform's
            # future still resolves quickly regardless of a slow platform
            # (e.g. Workday) still running in another thread.
            submitted = [(name, time.monotonic(), pool.submit(fn, deadline)) for name, fn in PLATFORMS]

            for platform_name, platform_start, future in submitted:
                p_fetched = p_saved = 0
                try:
                    jobs = future.result()
                except Exception as e:
                    log.exception("platform '%s' failed: %s", platform_name, e)
                    # Still record a stats row (status='failed') instead of
                    # skipping it — otherwise this platform's row is just
                    # absent from run_stats, indistinguishable from "returned
                    # 0 jobs" when reviewing history later.
                    record_stats(conn, run_id, platform_name, 0, 0, 0,
                                 round(time.monotonic() - platform_start, 2),
                                 status="failed", error=str(e)[:300])
                    record_company_run(conn, run_id, platform_name, status="failed", error=str(e))
                    conn.commit()
                    continue
                if getattr(jobs, "status", "ok") != "skipped":
                    platforms_run.append(platform_name)
                for job in jobs:
                    fetched += 1
                    p_fetched += 1
                    jid = job_id(job)
                    if platform_name == "workday" and jid in existing_ids:
                        # Persist foreign corrections before the save-time
                        # country gate so old placeholder rows stop leaking.
                        refresh_workday_location(conn, jid, job.get("location"))
                    if platform_name == "atlassian" and jid in existing_ids:
                        # Correct legacy blank locations before the country
                        # gate, so known US postings stop appearing in the UI.
                        mark_observed(conn, jid, int(time.time()))
                        refresh_atlassian_job(conn, jid, job)
                    if ((platform_name == "smartrecruiters" and not is_smartrecruiters_india_location(job.get("location")))
                            or (job.get("company") == "databricks" and parse_country(job.get("location")) != "India")
                            or not is_india_or_unknown(job.get("location"))):
                        non_india += 1
                        continue
                    if jid in existing_ids:
                        if platform_name in {"standard", "successfactors", "deloitte", "lowes", "myntra", "makemytrip", "ubs", "pwc", "ea", "swissre", "netapp", "workable", "workday_india", "workday", "eightfold", "employer_portals", "oracle", "icims"}:
                            refresh_collected_description(conn, jid, job)
                        if platform_name != "atlassian":
                            mark_observed(conn, jid, int(time.time()))
                        if platform_name == "qualcomm_students":
                            refresh_qualcomm_student(conn, jid, job)
                        if platform_name == "mastercard_workday":
                            refresh_mastercard_from_workday(conn, jid, job)
                        dedup_keys.setdefault(dedup_key(job["company"], job["title"], job.get("location"), job.get("description"), job.get("url")), set()).add(jid)
                        skipped += 1
                        continue
                    key = dedup_key(job["company"], job["title"], job.get("location"), job.get("description"), job.get("url"))
                    if key[3] and key[4] and key in dedup_keys:
                        for previous_id in dedup_keys[key]:
                            mark_observed(conn, previous_id, int(time.time()))
                        reposts += 1
                        continue
                    save_job(conn, jid, job, platform_name)
                    existing_ids.add(jid)
                    dedup_keys.setdefault(key, set()).add(jid)
                    saved += 1
                    p_saved += 1
                # jobs_matched kept equal to jobs_fetched in run_stats — no separate
                # filter step anymore, but stats.py's schema/queries still expect
                # the column, so this avoids touching that file too.
                record_stats(conn, run_id, platform_name, p_fetched, p_fetched, p_saved,
                             round(time.monotonic() - platform_start, 2),
                             status=getattr(jobs, "status", "ok"),
                             error=getattr(jobs, "error", "")[:300] or None)
                record_company_run(conn, run_id, platform_name, jobs,
                                   status=getattr(jobs, "status", "ok"), error=getattr(jobs, "error", ""))
                # Release SQLite's write lock before waiting for the next
                # network future. The UI can dismiss jobs during collection.
                conn.commit()

        # --- Classification / skills / experience --------------------------------
        # One combined scan (get_unprocessed) instead of three separate
        # full-table scans (get_unclassified/get_unskilled/get_unexperienced) —
        # each row is checked against all three columns at once, then
        # branched in Python. First run after adding any of these features
        # processes the full backlog (slow, one-time); every run after that
        # only processes whatever's still missing one of the three. See
        # process_backlog() above — also callable standalone via
        # --process-only.
        process_backlog(conn)

        # --- Cleanup ---------------------------------------------------------------
        # Runs automatically every pass now (was --cleanup-only before) —
        # jobs.db grew unbounded otherwise, which slowly degrades every
        # query in this file and in api/data.py. Same 365-day default as the
        # manual flag; harmless/cheap to run every time since it's a single
        # indexed-by-nothing DELETE on last_seen, small relative to the
        # fetch/classify work already done this run.
        removed = cleanup_old(conn)
        if removed:
            log.info("cleanup: removed %d row(s) older than 365 days", removed)

        log.info(
            "platforms=%s fetched=%d saved=%d already_seen=%d reposts_skipped=%d non_india_skipped=%d",
            ",".join(platforms_run), fetched, saved, skipped, reposts, non_india,
        )
    finally:
        # Runs even if something above raised — a crash mid-run (e.g. a bug
        # in classification or an unhandled fetcher error) used to leave
        # the connection open, which under WAL mode can leave stale locks
        # around for the next run.
        conn.close()


if __name__ == "__main__":
    import sys
    if os.environ.get("JOB_INTEL_OFFLINE") == "1" and any(
        arg.startswith("--refetch-") for arg in sys.argv[1:]
    ):
        raise RuntimeError("JOB_INTEL_OFFLINE=1 disables source refetch commands")
    # Windows' default console encoding (cp1252) can't print some Unicode
    # characters in job titles (narrow no-break spaces, en dashes, etc.).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if "--process-only" in sys.argv:
        conn = sqlite3.connect(DB_PATH)
        try:
            init_db(conn)  # ensures any new columns (e.g. experience_years) exist
            process_backlog(conn)
        finally:
            conn.close()
        log.info("process-only: done")
    elif "--reprocess-experience" in sys.argv:
        conn = sqlite3.connect(DB_PATH)
        try:
            init_db(conn)
            reset = reset_experience_years(conn)
            log.info("reprocess-experience: reset %d row(s), re-extracting under current logic...", reset)
            process_backlog(conn)
        finally:
            conn.close()
        log.info("reprocess-experience: done")
    elif "--reprocess-skills" in sys.argv:
        conn = sqlite3.connect(DB_PATH)
        try:
            init_db(conn)
            reset = reset_skills(conn)
            log.info("reprocess-skills: reset %d row(s), re-extracting under current skill list...", reset)
            process_backlog(conn)
        finally:
            conn.close()
        log.info("reprocess-skills: done")
    elif "--cleanup" in sys.argv:
        conn = sqlite3.connect(DB_PATH)
        removed = cleanup_old(conn)
        conn.close()
        log.info("cleanup: removed %d rows older than 365 days", removed)
    elif "--prune-non-india" in sys.argv:
        conn = sqlite3.connect(DB_PATH)
        removed = prune_non_india(conn)
        conn.close()
        log.info("prune: removed %d non-India rows", removed)
    elif "--remove-internshala" in sys.argv:
        conn = sqlite3.connect(DB_PATH)
        # All three historical labels: 'internshala' (pre-split, before
        # internshala_jobs/internshala_internships existed as separate
        # sources) plus both post-split ones — covers a db regardless of
        # how old it is / whether --relabel-internshala ever ran on it.
        removed = delete_by_source(conn, ["internshala", "internshala_jobs", "internshala_internships"])
        conn.close()
        log.info("remove-internshala: deleted %d row(s)", removed)
    elif "--remove-adzuna" in sys.argv:
        conn = sqlite3.connect(DB_PATH)
        removed = delete_by_source(conn, ["adzuna"])
        conn.close()
        log.info("remove-adzuna: deleted %d row(s)", removed)
    elif "--refetch-oracle" in sys.argv:
        conn = sqlite3.connect(DB_PATH)
        rows = get_oracle_jobs_missing_description(conn)
        log.info("refetching descriptions for %d oracle job(s)...", len(rows))
        def _oracle_base(c):
            datacenter = c.get("datacenter")
            if datacenter:
                return f"https://{c['tenant']}.fa.{datacenter}.oraclecloud.com"
            return f"https://{c['tenant']}.fa.oraclecloud.com"

        base_by_company = {c["company"]: _oracle_base(c) for c in config.ORACLE}
        updates = []
        for jid, company, req_id in rows:
            base = base_by_company.get(company)
            if not base:
                continue  # company no longer in config.ORACLE — skip, nothing to refetch against
            desc = fetch_requisition_detail(base, req_id)
            if desc:
                updates.append((jid, desc))
        if updates:
            update_descriptions(conn, updates)
            process_backlog(conn)
        conn.close()
        log.info("refetch: updated %d/%d oracle job description(s)", len(updates), len(rows))
    elif "--refetch-workday" in sys.argv:
        idx = sys.argv.index("--refetch-workday")
        if idx + 1 >= len(sys.argv):
            log.error("usage: python run.py --refetch-workday <company>  (e.g. fractal)")
            sys.exit(1)
        company = sys.argv[idx + 1]
        cfg = next((c for c in config.WORKDAY if c["company"] == company), None)
        if cfg is None:
            log.error("'%s' not found in config.WORKDAY", company)
            sys.exit(1)
        conn = sqlite3.connect(DB_PATH)
        rows = get_workday_jobs_missing_description(conn, company)
        detail_filter = cfg.get("fetch_details_filter")
        if detail_filter is not None:
            before = len(rows)
            rows = [(jid, title, url) for jid, title, url in rows if detail_filter.search(title)]
            log.info("workday refetch %s: %d/%d rows match fetch_details_filter", company, len(rows), before)
        log.info("refetching descriptions for %d workday job(s) (%s)...", len(rows), company)
        base = f"https://{cfg['tenant']}.{cfg['wd_server']}.myworkdayjobs.com"
        site_prefix = f"{base}/en-US/{cfg['site']}"
        referer = f"{base}/en-US/{cfg['site']}"
        updates = []
        for jid, title, url in rows:
            if not url.startswith(site_prefix):
                continue  # unexpected url shape — skip rather than guess
            ext_path = url[len(site_prefix):]
            desc = fetch_job_detail(base, cfg["tenant"], cfg["site"], ext_path, referer)
            if desc:
                updates.append((jid, desc))
        if updates:
            update_descriptions(conn, updates)
            process_backlog(conn)
        conn.close()
        log.info("refetch: updated %d/%d workday job description(s)", len(updates), len(rows))
    else:
        try:
            run()
        except KeyboardInterrupt:
            log.info("interrupted by user")
