"""Sources found by scripts/career/discover_sources.py and approved with --apply.

Generated file: rows are written from docs/catalog/CAREER_DISCOVERY_20261102.json.
Registration does not imply fresher eligibility or pay; see docs/catalog/CAREER_DISCOVERY.md.
"""

SOURCES = [
 {
  "key": "unacademy",
  "name": "Unacademy",
  "group": "smartrecruiters",
  "career_url": "https://careers.smartrecruiters.com/unacademy"
 },
 {
  "key": "cars24",
  "name": "Cars24",
  "group": "smartrecruiters",
  "career_url": "https://careers.smartrecruiters.com/cars24"
 },
 {
  "key": "gainsight",
  "name": "Gainsight",
  "group": "ashby",
  "career_url": "https://jobs.ashbyhq.com/gainsight"
 },
 {
  "key": "koreai",
  "name": "Kore.ai",
  "group": "smartrecruiters",
  "career_url": "https://careers.smartrecruiters.com/koreai"
 },
 {
  "key": "pocketfm",
  "name": "Pocket FM",
  "group": "lever",
  "career_url": "https://jobs.lever.co/pocketfm"
 },
 {
  "key": "turing",
  "name": "Turing",
  "group": "greenhouse",
  "career_url": "https://job-boards.greenhouse.io/turing"
 },
 {
  "key": "interviewbit",
  "name": "Scaler",
  "group": "smartrecruiters",
  "career_url": "https://careers.smartrecruiters.com/interviewbit"
 },
 {
  "key": "newtonschool",
  "name": "Newton School",
  "group": "smartrecruiters",
  "career_url": "https://careers.smartrecruiters.com/newtonschool"
 },
 {
  "key": "figma",
  "name": "Figma",
  "group": "greenhouse",
  "career_url": "https://job-boards.greenhouse.io/figma"
 },
 {
  "key": "sophos",
  "name": "Sophos",
  "group": "lever",
  "career_url": "https://jobs.lever.co/sophos"
 },
 {
  "key": "gen-digital",
  "name": "Gen Digital",
  "group": "ashby",
  "career_url": "https://jobs.ashbyhq.com/gen-digital"
 },
 {
  "key": "zuora",
  "name": "Zuora",
  "group": "greenhouse",
  "career_url": "https://job-boards.greenhouse.io/zuora"
 },
 {
  "key": "anaplan",
  "name": "Anaplan",
  "group": "greenhouse",
  "career_url": "https://job-boards.greenhouse.io/anaplan"
 },
 {
  "key": "extremenetworks",
  "name": "Extreme Networks",
  "group": "lever",
  "career_url": "https://jobs.lever.co/extremenetworks"
 },
 {
  "key": "agoda",
  "name": "Agoda",
  "group": "greenhouse",
  "career_url": "https://job-boards.greenhouse.io/agoda"
 },
 {
  "key": "jumptrading",
  "name": "Jump Trading",
  "group": "greenhouse",
  "career_url": "https://job-boards.greenhouse.io/jumptrading"
 },
 {
  "key": "dnb",
  "name": "Dun & Bradstreet",
  "group": "lever",
  "career_url": "https://jobs.lever.co/dnb"
 },
 {
  "key": "clearwater",
  "name": "Clearwater Analytics",
  "group": "greenhouse",
  "career_url": "https://job-boards.greenhouse.io/clearwater"
 }
]

INDIA_BOARDS = {row["key"] for row in SOURCES if row["group"] in {"greenhouse", "lever", "ashby"}}


def register(namespace):
    for row in SOURCES:
        group = row["group"].upper()
        if group in {"GREENHOUSE", "LEVER", "ASHBY", "WORKABLE"}:
            namespace[group].append(row["key"])
        elif group == "SMARTRECRUITERS":
            namespace[group].append({"company_id": row["key"]})
        else:
            raise ValueError("unsupported discovered group: " + row["group"])
        namespace["DISPLAY_NAMES"][row["key"]] = row["name"]
