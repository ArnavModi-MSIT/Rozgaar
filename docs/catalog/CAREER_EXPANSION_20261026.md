# 50-company career-source expansion — 26 October 2026

Added 50 employers to the career-page pipeline, increasing the configured company/display-name inventory from 231 to 281. These are public job feeds; no reader JSON, browser profile or career database was used in validation. Collection still starts manually from the website. Restart Rozgaar to load Python configuration changes.

**Pay and eligibility:** this is a broad monitoring expansion, not 50 certified fresher employers paying at least INR 8 LPA. Four additions have primary institution salary examples from the preceding research; seven have secondary historical placement leads; the remaining 39 have no verified fresher pay figure in this pass. Most feeds include experienced roles and nontechnical roles. Use the existing title/location/experience controls; inspect each job description. No salary floor is inferred for a posting that omits pay.

## Live verification scope

- Greenhouse, Lever and Ashby: actual existing adapters fetched the complete public board and retained positively identified India locations. At least one nonempty description was observed for every added board.
- Workday: queried live India facets, checked the first scoped page, then verified at least one detail country/secondary India location and nonempty full description. All scoped pages/details were not audited in this pass. The normal collector retains its pagination and detail fetching.
- SmartRecruiters and EXL: checked the first 100 global listing rows and at least one India detail with a nonempty description. Listed India counts are sample counts, not employer-wide totals.
- Generic Remote, unknown country and Indiana are excluded for the new standard boards. Explicit ATS country and secondary India locations are retained. Samsara uses a narrow Bengaluru office-code rule; Manhattan uses its exact Bangalore facet followed by detail-country checks.

A successful request and nonempty text do not prove complete source coverage, correct fresher eligibility or an available offer. Raw validation output is kept privately in `runtime/artifacts/expansion_validation.json`.

| Company | Source / official board | India listing evidence | Sample description | Graduate pay evidence |
|---|---|---|---|---|
| 6sense | [greenhouse](https://job-boards.greenhouse.io/6sense) | 11 returned by adapter | 4,307 characters | Not verified; monitor only |
| Abnormal AI | [greenhouse](https://job-boards.greenhouse.io/abnormalsecurity) | 12 returned by adapter | 4,591 characters | Not verified; monitor only |
| Acceldata | [lever](https://jobs.lever.co/acceldata) | 14 returned by adapter | 5,271 characters | [Historical 15 LPA package](https://hbtu.ac.in/placement/Placement-details-2025-26.pdf) |
| Alteryx | [workday_india](https://alteryx.wd108.myworkdayjobs.com/AlteryxCareers) | 3 reported by scoped search; first page sampled | 3,318 characters | Not verified; monitor only |
| Applied Materials | [workday_india](https://amat.wd1.myworkdayjobs.com/External) | 176 reported by scoped search; first page sampled | 3,463 characters | [Secondary historical lead: 16.3 LPA CTC](https://github.com/anxkhn/placement-data-2025) |
| Aptiv | [workday_india](https://aptiv.wd5.myworkdayjobs.com/Aptiv_Careers) | 145 reported by scoped search; first page sampled | 3,909 characters | [Secondary historical lead: 8.5 LPA CTC](https://github.com/anxkhn/placement-data-2025) |
| AQR Capital Management | [greenhouse](https://job-boards.greenhouse.io/aqr) | 13 returned by adapter | 2,984 characters | [Secondary historical lead: 31.61 LPA CTC](https://github.com/anxkhn/placement-data-2025) |
| Arista Networks | [smartrecruiters](https://careers.smartrecruiters.com/AristaNetworks) | 12 in first 100 global rows | 3,747 characters | [Historical 28 LPA CTC (2024)](https://www.amrita.edu/school/computing/amritapuri/placements/) |
| BitGo | [greenhouse](https://job-boards.greenhouse.io/bitgo) | 7 returned by adapter | 4,565 characters | [Secondary historical lead: 35 LPA CTC](https://github.com/anxkhn/placement-data-2025) |
| Celigo | [greenhouse](https://job-boards.greenhouse.io/celigo) | 2 returned by adapter | 7,247 characters | Not verified; monitor only |
| ClickHouse | [ashby](https://jobs.ashbyhq.com/clickhouse) | 10 returned by adapter | 5,652 characters | Not verified; monitor only |
| Cognite | [greenhouse](https://job-boards.greenhouse.io/cognite) | 13 returned by adapter | 12,674 characters | Not verified; monitor only |
| ConnectWise | [greenhouse](https://job-boards.greenhouse.io/connectwise) | 13 returned by adapter | 5,108 characters | Not verified; monitor only |
| Coursera | [greenhouse](https://job-boards.greenhouse.io/coursera) | 6 returned by adapter | 4,736 characters | Not verified; monitor only |
| Deliveroo | [greenhouse](https://job-boards.greenhouse.io/deliveroo) | 6 returned by adapter | 5,442 characters | Not verified; monitor only |
| Duolingo | [greenhouse](https://job-boards.greenhouse.io/duolingo) | 1 returned by adapter | 5,365 characters | Not verified; monitor only |
| ElevenLabs | [ashby](https://jobs.ashbyhq.com/elevenlabs) | 9 returned by adapter | 4,902 characters | Not verified; monitor only |
| EXL | [oracle](https://fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/jobs) | 78 in first 100 global rows | 1,229 characters | [Historical 10 LPA package](https://hbtu.ac.in/placement/Placement-details-2025-26.pdf) |
| Fivetran | [greenhouse](https://job-boards.greenhouse.io/fivetran) | 24 returned by adapter | 7,319 characters | Not verified; monitor only |
| FNZ | [workday_india](https://fnz.wd3.myworkdayjobs.com/fnz_careers) | 45 reported by scoped search; first page sampled | 8,649 characters | Not verified; monitor only |
| HackerRank | [greenhouse](https://job-boards.greenhouse.io/hackerrank) | 18 returned by adapter | 3,597 characters | [Secondary historical lead: 25 LPA CTC](https://github.com/anxkhn/placement-data-2025) |
| Hewlett Packard Enterprise | [workday_india](https://hpe.wd5.myworkdayjobs.com/WFMathpe) | 411 reported by scoped search; first page sampled | 7,378 characters | [Historical 8 LPA CTC](https://img.amizone.net/AzureFileHandler.ashx?FileName=amizonefiles%2FPlacementPdf%2FPlacement_079769.pdf) |
| Jumio | [greenhouse](https://job-boards.greenhouse.io/jumio) | 7 returned by adapter | 3,590 characters | Not verified; monitor only |
| Manhattan Associates | [workday_india](https://manh.wd5.myworkdayjobs.com/External) | 5 reported by scoped search; first page sampled | 10,880 characters | Not verified; monitor only |
| Mindtickle | [lever](https://jobs.lever.co/mindtickle) | 17 returned by adapter | 7,464 characters | Not verified; monitor only |
| Mixpanel | [greenhouse](https://job-boards.greenhouse.io/mixpanel) | 4 returned by adapter | 7,528 characters | Not verified; monitor only |
| Narvar | [greenhouse](https://job-boards.greenhouse.io/narvar) | 1 returned by adapter | 6,390 characters | Not verified; monitor only |
| Netskope | [greenhouse](https://job-boards.greenhouse.io/netskope) | 20 returned by adapter | 4,688 characters | Not verified; monitor only |
| New Relic | [greenhouse](https://job-boards.greenhouse.io/newrelic) | 5 returned by adapter | 9,661 characters | Not verified; monitor only |
| NielsenIQ | [smartrecruiters](https://careers.smartrecruiters.com/NielsenIQ) | 22 in first 100 global rows | 5,953 characters | Not verified; monitor only |
| OneTrust | [greenhouse](https://job-boards.greenhouse.io/onetrust) | 23 returned by adapter | 7,781 characters | Not verified; monitor only |
| PubMatic | [greenhouse](https://job-boards.greenhouse.io/pubmatic) | 36 returned by adapter | 6,904 characters | [Secondary historical lead: 13 LPA CTC](https://github.com/anxkhn/placement-data-2025) |
| Q2 | [workday_india](https://q2ebanking.wd5.myworkdayjobs.com/Q2) | 15 reported by scoped search; first page sampled | 6,465 characters | Not verified; monitor only |
| Renesas Electronics | [smartrecruiters](https://careers.smartrecruiters.com/RenesasElectronics) | 8 in first 100 global rows | 7,489 characters | Not verified; monitor only |
| RingCentral | [workday_india](https://ringcentral.wd1.myworkdayjobs.com/RingCentral_Careers) | 13 reported by scoped search; first page sampled | 3,962 characters | Not verified; monitor only |
| Samsara | [greenhouse](https://job-boards.greenhouse.io/samsara) | 5 returned by adapter | 9,744 characters | Not verified; monitor only |
| SingleStore | [greenhouse](https://job-boards.greenhouse.io/singlestore) | 9 returned by adapter | 6,690 characters | Not verified; monitor only |
| Smarsh | [lever](https://jobs.lever.co/smarsh) | 4 returned by adapter | 4,727 characters | Not verified; monitor only |
| Starburst | [greenhouse](https://job-boards.greenhouse.io/starburst) | 5 returned by adapter | 5,084 characters | Not verified; monitor only |
| Tekion | [ashby](https://jobs.ashbyhq.com/tekion) | 70 returned by adapter | 4,621 characters | Not verified; monitor only |
| Thales | [workday_india](https://thales.wd3.myworkdayjobs.com/Careers) | 88 reported by scoped search; first page sampled | 3,188 characters | Not verified; monitor only |
| Toast | [greenhouse](https://job-boards.greenhouse.io/toast) | 20 returned by adapter | 6,601 characters | Not verified; monitor only |
| Trimble | [workday_india](https://trimble.wd1.myworkdayjobs.com/TrimbleCareers) | 24 reported by scoped search; first page sampled | 7,178 characters | Not verified; monitor only |
| Veeva Systems | [lever](https://jobs.lever.co/veeva) | 32 returned by adapter | 3,792 characters | Not verified; monitor only |
| Western Digital | [smartrecruiters](https://careers.smartrecruiters.com/WesternDigital) | 3 in first 100 global rows | 4,503 characters | Not verified; monitor only |
| Yugabyte | [greenhouse](https://job-boards.greenhouse.io/yugabyte) | 4 returned by adapter | 7,856 characters | Not verified; monitor only |
| Zendesk | [workday_india](https://zendesk.wd1.myworkdayjobs.com/Zendesk) | 15 reported by scoped search; first page sampled | 5,227 characters | Not verified; monitor only |
| Zenoti | [greenhouse](https://job-boards.greenhouse.io/zenoti) | 37 returned by adapter | 4,438 characters | [Secondary historical lead: 13.72 LPA CTC](https://github.com/anxkhn/placement-data-2025) |
| Zoom | [workday_india](https://zoom.wd5.myworkdayjobs.com/Zoom) | 9 reported by scoped search; first page sampled | 4,379 characters | Not verified; monitor only |
| ZoomInfo | [greenhouse](https://job-boards.greenhouse.io/zoominfo) | 13 returned by adapter | 5,834 characters | Not verified; monitor only |

## Maintenance

Validation: 533 unit/API tests passed; Python compile checks passed; release scan reported no findings. The localhost app loaded the new configuration with career collection idle. Live feed checks did not import jobs into SQLite.

`backend/config/career_expansion.py` owns the 50 declarations and display names. `backend/config/sources.py` registers them into existing collectors. `backend/fetchers/standard.py` applies positive India scope to the added standard boards. No database migration is needed.

Regenerate the complete inventory with `runtime/python/Scripts/python.exe -m scripts.career.company_inventory`.

Unresolved priority employers are recorded in [Career sources to find](CAREER_SOURCES_TO_FIND.md). Their names are not added as working sources merely to fill the target.

Secondary salary leads are user-contributed historical placement data, not employer pay bands. The source combines college/student/Reddit reports; role, year, base salary, bonus and stock must be independently verified. Four primary examples are also campus-specific historical offers, not universal salary promises.
