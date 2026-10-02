# Audit of the requested 75 companies

Live snapshot: 2 October 2026. Counts are before project title, experience and UI filters. This audit does not modify SQLite.

**72 companies have configured collectors; three remain unavailable.** `ok` means the collector completed its checks. `returned` means rows were received but the adapter has no completeness metadata. Neither status proves every vacancy is current. `partial` identifies an incomplete fetch or missing eligibility/description information.

Google and Microsoft retain the requested early-career filters. LinkedIn here means LinkedIn as an employer only. Its general job-board collector remains removed. Automattic remote jobs have unverified geographic eligibility. HRT and Zerodha had no confirmed India jobs.

| Company | Collector | Status | India jobs | India descriptions | Notes |
|---|---|---|---:|---:|---|
| Google | google_careers | ok | 26 | 26 (summary) |  |
| Meta | meta | ok | 24 | 24 (description) |  |
| Apple | apple | returned | 9 | 9 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Microsoft | eightfold | returned | 2 | 2 (summary) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Amazon | amazon | ok | 2360 | 2360 (description) |  |
| NVIDIA | workday | returned | 131 | 0 (none) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Netflix | netflix | ok | 7 | 7 (summary) |  |
| LinkedIn | linkedin_company | partial | 17 | 0 (none) | Public search does not expose a reliable total; descriptions unavailable |
| Databricks | greenhouse | returned | 94 | 94 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Stripe | greenhouse | returned | 5 | 5 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Airbnb | greenhouse | returned | 5 | 5 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Atlassian | atlassian | returned | 56 | 56 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Rubrik | greenhouse | returned | 32 | 32 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Broadcom | workday_india | ok | 70 | 70 (description) |  |
| Uber | uber | partial | 19 | 19 (description) | received 19 of 20 listings |
| Rippling | rippling | ok | 79 | 79 (description) |  |
| Roku | greenhouse | returned | 24 | 24 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Glean | greenhouse | returned | 23 | 23 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Snowflake | ashby | returned | 13 | 13 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Confluent | ashby | returned | 1 | 1 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Coinbase | greenhouse | returned | 11 | 11 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Salesforce | workday | returned | 45 | 45 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| ServiceNow | smartrecruiters | returned | 76 | 76 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Adobe | phenom | returned | 80 | 80 (summary) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Intuit | intuit | ok | 26 | 26 (description) |  |
| Palo Alto Networks | workday | returned | 152 | 152 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| CrowdStrike | workday_india | ok | 30 | 30 (description) |  |
| MongoDB | greenhouse | returned | 83 | 83 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Twilio | greenhouse | returned | 10 | 10 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Okta | greenhouse | returned | 111 | 111 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Pure Storage | greenhouse | returned | 84 | 84 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Cohesity | workday_india | ok | 15 | 15 (description) |  |
| Oracle / OCI | oracle | returned | 17 | 17 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Booking.com | booking | ok | 24 | 24 (description) |  |
| Indeed | â€” | unavailable | â€” | â€” (none) | Official careers endpoint returned HTTP 403; no working public feed confirmed. |
| Bloomberg | bloomberg | ok | 8 | 8 (description) |  |
| GitLab | greenhouse | returned | 28 | 28 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Automattic | automattic | partial | 0 | 0 (none) | Individual geographic eligibility is unspecified; review each description |
| Postman | workday_india | ok | 11 | 11 (description) |  |
| PayPal | paypal | ok | 10 | 10 (description) |  |
| Flipkart | flipkart | ok | 7 | 7 (description) |  |
| PhonePe | smartrecruiters | returned | 89 | 89 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Razorpay | greenhouse | returned | 17 | 17 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Swiggy | swiggy | ok | 75 | 75 (description) |  |
| Zomato | â€” | unavailable | â€” | â€” (none) | Official careers page accessible but no vacancy feed found. Legacy Zomato1 SmartRecruiters postings dated 2015/2016 were rejected as stale. |
| Meesho | lever | returned | 57 | 57 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| CRED | lever | returned | 8 | 8 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Groww | greenhouse | returned | 7 | 7 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Zepto | zepto | ok | 1 | 1 (description) | Public Darwinbox listing total verified; full JD returned. |
| Zerodha | zerodha | ok | 0 | 0 (none) |  |
| American Express | oracle | returned | 60 | 60 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Visa | workday | returned | 79 | 0 (none) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Mastercard | mastercard_workday | ok | 211 | 211 (description) |  |
| JPMorgan Chase | oracle | returned | 322 | 322 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Goldman Sachs | goldman_sachs | returned | 121 | 121 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Morgan Stanley | eightfold | returned | 118 | 118 (summary) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| BlackRock | blackrock | ok | 39 | 39 (description) |  |
| Arcesium | greenhouse | returned | 24 | 24 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| D. E. Shaw India | deshaw | ok | 72 | 72 (description) |  |
| Millennium | millennium | ok | 39 | 39 (summary) |  |
| Tower Research Capital | tower_research | ok | 13 | 13 (description) |  |
| Graviton Research Capital | greenhouse | returned | 14 | 14 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Quadeye | quadeye | ok | 13 | 13 (description) |  |
| AlphaGrep | greenhouse | returned | 7 | 7 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| WorldQuant | greenhouse | returned | 8 | 8 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Hudson River Trading | hrt | ok | 0 | 0 (none) |  |
| Citadel Securities | â€” | unavailable | â€” | â€” (none) | Official listing returned HTTP 403. |
| IMC Trading | greenhouse | returned | 16 | 16 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Optiver | greenhouse | returned | 4 | 4 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Squarepoint Capital | greenhouse | returned | 23 | 23 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Qube Research & Technologies | greenhouse | returned | 6 | 6 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Walmart Global Tech | workday | returned | 226 | 226 (description) | Fetcher has no completeness metadata; returned count does not prove full coverage. |
| Expedia Group | expedia | partial | 4 | 4 (summary) | listing request failed on page 5 |
| ZS Associates | zs | ok | 47 | 47 (description) |  |
| Qualcomm | eightfold | returned | 572 | 572 (summary) | Fetcher has no completeness metadata; returned count does not prove full coverage. |

## Repeat the audit

```powershell
python scripts/audit_company_sources.py
python scripts/audit_company_sources.py --only broadcom crowdstrike --seconds 240 --workers 4
```

The JSON records UTC check times, returned counts, unknown locations, duration and errors. Run only one audit process at a time because it writes one snapshot file. The Markdown table is a reviewed snapshot, not regenerated by the command.

## Unavailable sources

- Indeed employer: official careers endpoint returned 403.
- Citadel Securities: official vacancies endpoint returned 403.
- Zomato: Eternal careers has no discovered public vacancy feed. The accessible Zomato1 SmartRecruiters board contains 2015/2016 postings and was rejected as stale.

Zepto was connected on 2 October 2026 using the supplied Darwinbox URL. Its current opening is Manager I - Delivery Hub Manager in Bengaluru (operations, not a coding role).
