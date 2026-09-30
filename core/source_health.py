"""Interpret local collector history without treating a failed fetch as zero jobs."""

from collections import defaultdict


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
