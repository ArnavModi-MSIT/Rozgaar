# Career source discovery

`scripts/career/discover_sources.py` finds public ATS feeds for the names in
`CAREER_CANDIDATES_20261102.json` (171 employers known for strong India early-career hiring that are not
yet configured). Names, not links, are the input; being on the list says nothing verified about pay or
fresher eligibility.

Run from the repository root on a machine with internet access:

```powershell
& '.\runtime\python\Scripts\python.exe' -m scripts.career.discover_sources
```

It tries slug variants of each name on public Greenhouse, Lever, Ashby, SmartRecruiters and Workable
endpoints and keeps a board only when it lists a posting with positive India evidence. Nothing is saved
to the career database. Output:

- `CAREER_DISCOVERY_20261102.json`: found boards (ATS, slug, India posting count, sample titles), names not found, names already configured.
- `CAREER_DISCOVERY_20261102.md`: the same as a table, plus the **not found** list for which careers links are needed.

Requests are spaced per host. A rate limit (HTTP 429), server error or timeout is never counted as "not found": those names are listed under **Retry needed**, and `--retry` probes only them, keeping earlier results and any `"skip"` edits.

Review the sample titles: a slug can belong to an unrelated company. Set `"skip": true` on any wrong
row in the JSON, then register the rest:

```powershell
& '.\runtime\python\Scripts\python.exe' -m scripts.career.discover_sources --apply
```

`--apply` rewrites `backend/config/career_discovered.py` (idempotent). Greenhouse, Lever and Ashby rows
are India-scoped like the other expansion batches. Employers on Workday, Oracle, Phenom, iCIMS, Eightfold
or a custom portal are not found by this tool; give their careers links to add them by hand.

## Browser-verified batch, 2 November 2026

`backend/config/career_browser_20261102.py` holds employers found by opening their careers pages in a
browser and calling the public listing API from the employer's own origin. Observed that day:

| Employer | System | Observation |
|---|---|---|
| Intercontinental Exchange | Jibe (`kind: jibe`) | 48 India postings with full descriptions; client code `ice` |
| CME Group | Workday (`cmegroup`, `wd1`, `cme_careers`) | 18 India postings, Bengaluru |
| Nomura | SuccessFactors | 291 postings, Mumbai in the sample; serves 100 rows per page; the SuccessFactors adapter now follows the site's own total instead of assuming 25 rows per page |
| Synopsys | TalentBrew (`kind: talentbrew`, org 44408) | 201 unique India postings across 14 pages, descriptions in `.ats-description`; the site reports 203 and 231 in different views, so counts differ slightly |
| Moody's | TalentBrew (org 49841) | 37 unique India postings; some locations lack the word India (e.g. Bangalore, Karnataka), handled by the anchored-city rule |
| Aon | Jibe (`kind: jibe`, no client code) | 20 India postings with descriptions; job pages at `/jobs/<slug>` resolve |
| Marsh McLennan | Phenom (`careers.marsh.com`, refNum `MAMCGLOBAL`) | 70 India of 1,932 global; the Phenom fetcher reads all global rows, descriptions are teasers only |
| Genpact | Workday (`genpact`, `wd108`, `External_Careers`) | India-filtered search returns Bengaluru, Noida and Gurugram roles; very large, so collection is slow |
| Macquarie | Avature (`kind: avature`, tenant filter `10671=[871433]`) | 77 India postings (Gurugram 45, Hyderabad 30, Mumbai 2); the server caps pages at 9 rows, so the adapter advances by rows returned |
| KPMG Global Services | Oracle Cloud (`CX_3`) | 523 India postings of 524 |
| Hexaware | Oracle Cloud (`CX_1`) | 109 India postings of 255 |
| Vodafone Idea | SuccessFactors | 332 postings, 7 rows per page |
| Capgemini | Own JSON API (`kind: capgemini`, `cg-jobstream-api.azurewebsites.net`) | 634 unique India postings with descriptions |
| LeadSquared | Darwinbox | 13 India postings, some with empty descriptions |
| Delhivery | Darwinbox | 7 postings (6 India); small board |
| Schneider Electric | Jibe | 584 returned, 573 India; the 11 foreign rows make each run report partial. Tags include Fresh Graduate and Graduate Program |
| Eaton | Eightfold | 203 India postings, including apprentice programmes |
| bp | Workday (`bpinternational`, `wd3`, `bpCareers`) | 31 India matches |
| Cummins | Oracle Cloud (`CX_1`) | 156 India postings of 1,188 |
| EY | SuccessFactors under `/ey/search/` with `locationsearch=India` | 2,593 India postings; detail fetching is slow. Locations like `Bengaluru, KA, IN, 560016` read as the US, so `country_scoped` rewrites them to `Bengaluru, India` |
| Wipro | SuccessFactors RMK (`jobLocationCountry=India`, `location_style: city_country`) | 5,444 India of 6,885; reads the newest 1,000 only (`RMK_MAX_PAGES`) |
| HCLTech | SuccessFactors RMK (`custCountryRegion=India`) | 12,676 India of 15,180; reads the newest 1,000 only; some postings appear twice |
| Urban Company | Own API (`kind: urbancompany`, POST `getAllJobs`) | 10 postings, all India, descriptions included |
| McKinsey & Company | Own API (`kind: mckinsey`, gateway job search) | 49 postings open in India; global roles keep their India cities only |

Checked and not usable with a generic adapter: Vanguard, Citadel Securities and Equifax (custom sites),
Schwab (TalentBrew, not yet checked with the new adapter), MSCI (classic iCIMS portal). Verisk's site refused the browser.

## Workday batch, 7 November 2026

`backend/config/career_browser_20261107.py` holds 20 Workday employers found by reading each tenant's `robots.txt` (a valid tenant answers 200 with its site names, an unknown one 422), then calling the public CXS listing. Each was run through the real `workday_india` collector the same day; descriptions were present on every posting. A `partial` status means some multi-location postings were dropped because their detail page was not India (the adapter's country check), not that the board failed.

| Employer | Site | India postings collected |
|---|---|---|
| Cigna | `cigna` / `cignacareers` | 102 |
| MUFG | `mufgub` / `MUFG-Careers` | 203 (partial) |
| Ameriprise Financial | `ameriprise` / `Ameriprise` | 48 |
| Wolters Kluwer | `wk` / `External` | 54 |
| Sabre | `sabre` / `SabreJobs` | 35 |
| Genesys | `genesys` / `Genesys` | 12 |
| Clarivate | `clarivate` / `Clarivate_Careers` | 48 (partial; city-pattern facet) |
| Invesco | `invesco` / `IVZ` | 47 (Hyderabad only; pattern facet) |
| Trellix | `trellix` / `EnterpriseCareers` | 10 |
| Prudential Financial | `prudential` / `prudential` | 30 (partial) |
| FICO | `fico` / `External` | 5 |
| Finastra | `finastra` / `FINC` | 35 |
| Global Payments | `tsys` / `TSYS` | 51 (partial; pattern facet) |
| Vanguard | `vanguard` / `vanguard_external` | 79 (Hyderabad) |
| Danaher | `danaher` / `DanaherJobs` | 118 (partial) |
| 3M | `3m` / `Search` | 86 (partial) |
| Novartis | `novartis` / `Novartis_Careers` | 142 (partial) |
| GSK | `gsk` / `GSKCareers` | 190 |
| Philips | `philips` / `jobs-and-careers` | 65 (partial) |
| Rockwell Automation | `rockwellautomation` / `External_Rockwell_Automation` | 52 |

Found but not added this round (Workday, India postings seen): Sanofi 65, Pfizer 26, GE HealthCare ~180 (mixed location labels), AstraZeneca 27, MSD 38, Rockwell early careers 3, Franklin Templeton (no India facet). Truist, Elevance, Pru/PGIM, Intapp and Temenos showed no India location.

## Checked in the 49-link review (2 November): not added

- **Reachable, checked, and not worth an adapter now:** Axis Bank (RippleHire, 9,581 mostly branch roles, empty list descriptions), CitiusTech (RippleHire, 38 postings, no descriptions in the list), Indegene (SuccessFactors RMK, 19 postings including a test job), Zoho (public API returns only a few openings), Moglix (Flexiele, signed requests).
- **Needs a bigger change:** Coforge (Zwayam, 172 openings). It needs the PowerShell HTTP/2 helper that the Info Edge fetcher uses, generalised past its hard-coded company id.
- **Custom or unidentified:** EPAM, Merkle, Persistent, Pine Labs, Brillio, GlobalLogic, Shiprocket, Policybazaar, Nykaa, Zetwerk, Infra.Market, NoBroker, Kissflow, Keka, CRISIL, TresVista, Oliver Wyman, Cognizant, OfBusiness, Jio, Mu Sigma, WNS, Nagarro (its SmartRecruiters board is empty).
- **Blocked or failed:** eClerx and M2P Fintech (bot challenge), IDFC FIRST Bank (certificate does not match the address), Magicbricks (blocked by the browser's safety restrictions), Apna (Workable answers HTTP 429 from this computer), Chargebee (page timed out).
