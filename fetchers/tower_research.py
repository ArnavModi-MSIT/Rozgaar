"""Tower Research's official Greenhouse board with city-only normalization."""
import re
from fetchers.standard import fetch_greenhouse
from fetchers.result import CollectionResult

CITIES = {
    "gurgaon": "India", "gurugram": "India", "gift city": "India",
    "new york": "United States", "chicago": "United States",
    "charleston": "United States", "las vegas": "United States", "miami": "United States",
    "london": "United Kingdom", "montreal": "Canada", "montréal": "Canada",
    "hong kong": "Hong Kong", "singapore": "Singapore", "shanghai": "China",
    "sydney": "Australia", "paris": "France", "amsterdam": "Netherlands",
    "grand cayman": "Cayman Islands",
}


def normalize_location(location):
    countries = {country for city, country in CITIES.items()
                 if re.search(r"\b" + re.escape(city) + r"\b", location, re.I)}
    # India first preserves postings offered in both India and overseas offices.
    ordered = sorted(countries, key=lambda value: (value != "India", value))
    return location + ("; " + "; ".join(ordered) if ordered else "")


def collect(deadline=None):
    jobs = fetch_greenhouse("towerresearchcapital")
    for job in jobs:
        job["location"] = normalize_location(job["location"])
    return CollectionResult(jobs)
