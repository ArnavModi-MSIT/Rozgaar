"""Interpret local collector history without treating a failed fetch as zero jobs."""

from collections import defaultdict
import sqlite3
import time


def configured_company_sources():
    """Inventory only. No imports of fetchers and no network requests."""
    import backend.config as config
    result = defaultdict(set)
    groups = {
        "standard": ("GREENHOUSE", "LEVER", "ASHBY"), "oracle": ("ORACLE",),
        "phenom": ("PHENOM",), "workday": ("WORKDAY",), "eightfold": ("EIGHTFOLD",),
        "successfactors": ("SUCCESSFACTORS",), "icims": ("ICIMS",),
        "smartrecruiters": ("SMARTRECRUITERS",), "workable": ("WORKABLE",),
        "ainterviews": ("AINTERVIEWS",), "indiamart": ("INDIAMART",),
        "workday_india": ("WORKDAY_INDIA",), "workday_students": ("WORKDAY_STUDENTS",),
        "employer_portals": ("EMPLOYER_PORTALS",), "google_careers": ("GOOGLE_CAREERS",),
    }
    for platform, names in groups.items():
        for name in names:
            for cfg in getattr(config, name, []):
                company = cfg if isinstance(cfg, str) else cfg.get("company") or cfg.get("company_id")
                if company:
                    result[company].add(platform)
    dedicated = {
        "netapp": "netapp", "swissre": "swissre", "ea": "ea", "pwc": "pwc",
        "ubs": "ubs", "makemytrip": "makemytrip", "myntra": "myntra", "tredence": "tredence",
        "sap": "sap", "lowes": "lowes", "nutanix": "nutanix", "mathworks": "mathworks",
        "maqsoftware": "maqsoftware", "micron": "micron", "qualcomm_students": "qualcomm",
        "morgan_stanley_students": "morganstanley", "unitedhealthgroup": "unitedhealthgroup",
        "zepto": "zepto", "hrt": "hrt", "bloomberg": "bloomberg", "linkedin_company": "linkedin_company",
        "netflix": "netflix", "automattic": "automattic", "zerodha": "zerodha", "amd": "amd",
        "booking": "booking", "target": "target", "tesco": "tesco", "juspay": "juspay",
        "mediatek": "mediatek", "millennium": "millennium", "paypal": "paypal",
        "blackrock": "blackrock", "intuit": "intuit", "rippling": "rippling", "deshaw": "deshaw",
        "quadeye": "quadeye", "zs": "zs", "swiggy": "swiggy", "tower_research": "towerresearchcapital",
        "deloitte": "deloitte", "mastercard_workday": "mastercard", "amazon": "amazon",
        "atlassian": "atlassian", "expedia": "expedia", "apple": "apple", "goldman_sachs": "goldman_sachs",
        "deutsche_bank": "deutsche_bank", "bank_of_america": "Bank of America", "barclays": "barclays",
        "flipkart": "flipkart", "meta": "meta", "uber": "uber",
    }
    for platform, company in dedicated.items():
        result[company].add(platform)
    return dict(result)


def record_company_run(conn, run_id, platform, jobs=(), *, status="ok", error=""):
    """Record observed counts. Legacy platform results remain explicitly unverified."""
    from backend.core.location import is_india_or_unknown, is_smartrecruiters_india_location, parse_country
    companies = {company for company, sources in configured_company_sources().items() if platform in sources}
    grouped = defaultdict(list)
    for job in jobs:
        grouped[job["company"]].append(job)
    outcomes = getattr(jobs, "companies", {})
    companies.update(grouped)
    companies.update(outcomes)
    for company in companies:
        rows = grouped[company]
        accepted = [job for job in rows if is_india_or_unknown(job.get("location"))
                    and (platform != "smartrecruiters" or is_smartrecruiters_india_location(job.get("location")))
                    and (company != "databricks" or parse_country(job.get("location")) == "India")]
        outcome = outcomes.get(company)
        company_status = outcome["status"] if outcome else (status if status in {"failed", "skipped", "partial"} else "unverified")
        reason = outcome.get("error", "") if outcome else error
        if not outcome and status == "ok":
            reason = "Platform returned successfully; company completeness is unverified."
        conn.execute("""INSERT OR REPLACE INTO company_runs VALUES (?,?,?,?,?,?,?,?,?)""",
            (run_id, int(time.time()), company, platform, company_status, len(rows), len(accepted),
             sum(not (job.get("description") or "").strip() for job in accepted), reason[:500]))


def dashboard(conn):
    """Latest company/platform observations plus inventory; no scraping on page load."""
    import backend.config as config
    conn.row_factory = sqlite3.Row
    latest = {}
    for row in conn.execute("""SELECT * FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY company, platform ORDER BY timestamp DESC, run_id DESC) AS sequence
        FROM company_runs) WHERE sequence = 1"""):
        latest.setdefault((row["company"], row["platform"]), dict(row))
    stored = {row["company"]: dict(row) for row in conn.execute("""SELECT company, COUNT(*) AS stored,
        SUM(CASE WHEN posting_status = 'closed' THEN 1 ELSE 0 END) AS closed,
        MAX(last_seen) AS last_seen FROM jobs GROUP BY company""")}
    inventory = configured_company_sources()
    keys = {(company, platform) for company, sources in inventory.items() for platform in sources} | set(latest)
    companies = []
    for company, platform in sorted(keys):
        observation = latest.get((company, platform), {})
        companies.append({"company": company, "name": config.DISPLAY_NAMES.get(company, company.title()),
            "platform": platform, "configured": platform in inventory.get(company, ()),
            "status": observation.get("status", "not run"), "timestamp": observation.get("timestamp"),
            "fetched": observation.get("fetched"), "india_or_unknown": observation.get("india_or_unknown"),
            "missing_descriptions": observation.get("missing_descriptions"), "error": observation.get("error", ""),
            **stored.get(company, {"stored": 0, "closed": 0, "last_seen": None})})
    history = [dict(row) for row in conn.execute("SELECT * FROM run_stats ORDER BY timestamp DESC, id DESC")]
    companies.sort(key=lambda item: (item["name"].casefold(), item["platform"]))
    return {"companies": companies, "platforms": summarize(history, {"workable"} if not config.WORKABLE else ()),
            "note": "Counts reflect collector observations, not a completeness guarantee. No missing posting is automatically closed. 'not run' means no per-company history since this update."}


def summarize(rows, disabled_platforms=()):
    """Return one health summary per platform from newest-first run_stats rows."""
    groups = defaultdict(list)
    for row in rows:
        groups[row["platform"]].append(row)

    summaries = []
    for platform, history in groups.items():
        history.sort(key=lambda row: (row["timestamp"], row["id"]), reverse=True)
        latest = history[0]
        prior_success = [
            row["jobs_fetched"] for row in history[1:]
            if (row["status"] or "ok") == "ok" and row["jobs_fetched"] > 0
        ][:7]
        baseline = sum(prior_success) / len(prior_success) if len(prior_success) >= 3 else None
        latest_success = next((row["timestamp"] for row in history if (row["status"] or "ok") == "ok"), None)

        if platform in disabled_platforms:
            health = "not configured"
        elif latest["status"] in {"failed", "partial", "skipped"}:
            health = latest["status"]
        elif latest["jobs_fetched"] == 0:
            health = "zero after history" if baseline is not None and baseline >= 10 else "zero"
        elif baseline is not None and baseline >= 10 and latest["jobs_fetched"] < 0.3 * baseline:
            health = "large drop"
        else:
            health = "ok"

        summaries.append({
            "platform": platform,
            "health": health,
            "latest": latest,
            "last_success": latest_success,
            "baseline": baseline,
        })
    return sorted(summaries, key=lambda item: (item["health"] == "ok", item["platform"]))
