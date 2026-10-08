# Additional 20-company audit

Checked 8 October 2026. Off-campus eligibility and ₹8 LPA+ compensation are
**not guaranteed** by employer name. Counts precede role/experience filters.

## Connected: 17 companies

| Company | Official feed | India jobs | Full descriptions | Status |
| --- | --- | ---: | ---: | --- |
| SAP Labs India | [SAP India](https://jobs.sap.com/en/jobs/?country=India) | 4 | 4 | Complete search |
| Nutanix | [India jobs](https://careers.nutanix.com/en/jobs/?search=&country=India&pagesize=20#results) | 35 | 35 | Complete India search: 20 + 15 rows, 35 unique IDs |
| MathWorks | [Official RSS](https://www.mathworks.com/company/jobs/opportunities/rss.xml) | 31 | 31 | Complete returned feed; HTML search incomplete |
| Commvault | [Greenhouse](https://job-boards.greenhouse.io/commvault) | 15 | 15 | Complete board, India selected |
| Cadence Design Systems | [Workday](https://cadence.wd1.myworkdayjobs.com/External_Careers) | 196 | 196 | Complete India facet pagination |
| Analog Devices | [Workday](https://analogdevices.wd1.myworkdayjobs.com/External) | 105 | 105 | Complete India facet pagination |
| Amadeus Labs | [Workday](https://amadeus.wd502.myworkdayjobs.com/jobs) | 7 | 7 | Complete India search; old wd3 host incorrect |
| Micron Technology | [Careers](https://careers.micron.com/careers?location=India) | 309 | 309 | Complete PCSX search and JSON-LD details |
| Lowe's India | [India search](https://talent.lowes.com/in/en/search-results) | 46 | 46 | Complete India pagination and embedded job descriptions |
| Fanatics | [Official directory](https://www.fanaticsinc.com/join-our-team) | 10 | 10 | Four linked Greenhouse boards; India jobs in Commerce |
| Sigmoid Analytics | [Official openings](https://www.sigmoid.com/careers/current-openings/) | 30 | 30 | Linked Greenhouse board, India selected |
| MAQ Software | [Careers](https://maqsoftware.com/careers/) | 3 | 3 | Linked JobScore Atom feed |
| Siemens Healthineers | [Careers](https://www.siemens-healthineers.com/careers) | 13 | 13 | Linked Workday India search |
| Tredence Analytics | [Careers](https://www.tredence.com/careers/greatest-of-ai) | 20 | 20 | Linked RippleHire; all 58 global rows checked |
| Myntra | [Official jobs](https://jobs.myntra.com/home) | 45 | 45 | Complete public Spire search: 20 + 20 + 5 rows |
| MakeMyTrip | [Official jobs](https://careers.makemytrip.com/prod/jobs) | 29 | 29 | Complete first-party listing and full detail responses |

| UBS | [Official India search](https://jobs.ubs.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=searchResults&SearchType=linkquery&LinkID=15231#keyWordSearch=&locationSearch=India) | 29 | 29 | Anonymous BrassRing search and complete detail sections |

## Pending: 3 companies

These are research records, **not active collectors**.

| Company | Official page | Remaining issue |
| --- | --- | --- |
| Zupee | [Official site](https://www.zupee.com/) | `/careers/` returned 404; current openings link needed |
| Mercer Mettl | [Careers](https://mettl.com/careers/) | Directs applicants to LinkedIn/email; no independent feed found |
| NSE | [Jobs](https://www.nseindia.com/static/careers-at-nse/jobs) | Direct requests timed out; collector unverified |

## Code and operation

`fetchers/makemytrip.py` reads `/api/jobs` from the first-party careers site.
The complete `allJobs` array is returned in one response; Load More is a frontend
display control. `/api/jobDetails?jobId=...` supplies full encoded HTML under the
site's `job_decription` key. The official Darwinbox apply URL is checked against
the requested ID, while job cards link to first-party `/prod/opportunity/` pages.
Normal browser headers resolve the earlier Python request timeouts. Experience
fields are converted according to the explicit Years/Months unit. Stronger JD
requirements are preserved. Missing detail text yields partial status, and later
collections refresh saved descriptions while preserving dismissals.

`fetchers/myntra.py` resolves the public career workspace for `jobs.myntra.com`
through Spire's `/ies/v1/p/workspaceId` endpoint and pages the public
`/requisition/_search` response with the returned WorkspaceId header. No account
or login token is required. Each response must belong to that workspace. Full
descriptions are included in listings and were compared with the public detail
endpoint. Explicit country fields select India; metadata experience months are
converted to years and appended under Required Qualifications, preserving any
stronger requirement in the description. Mandatory/preferred skill flags remain
separate. Existing saved descriptions are refreshed on subsequent collection.

Lowe's details prefer the page's embedded `phApp.ddo.jobDetail.data.job.description`
JSON, checked against the requested job ID. Several JSON-LD blocks were empty
or introductory only. This JSON is parsed without executing JavaScript. Live
validation confirmed 46 unique India postings and 46 descriptions. Subsequent
collection refreshes existing Lowe's descriptions and derived experience/skills
while preserving first-seen timestamps and dismissals.

Nutanix requires standard browser request headers for its public server-rendered
search. Python's default headers returned the global first page despite query
parameters. The collector keeps `country=India` and `pagesize=20` on every page,
checks the reported total, rejects ignored country filters, and fetches full
JSON-LD descriptions. Live verification returned 35/35 unique India postings
with 35/35 descriptions.

`fetchers/career_html.py` implements Nutanix HTML, MathWorks RSS, MAQ Atom,
SAP public Next.js listing data, Micron PCSX, and Lowe's India Phenom search.
Structured detail text is used rather than description teasers. `tredence.py`
uses public RippleHire parameters (`search=*:*`, zero-based pages, public site
selector from the official URL), verifies global pagination, and selects known
Indian offices. Generic remote/unknown locations are not inferred to be India.
Config registers four Workday boards and six Greenhouse boards. Fanatics' four
businesses represent one requested company. Workday now retains requirements
after character 10,000. Interrupted listings and missing details report partial.

Next `Start Job Intel.cmd` / `python run.py` includes these collectors. Live
validation did not modify saved jobs, resumes, or dismissals. The original
75-company manifest retains its original scope; this is a separate batch.


UBS: `fetchers/ubs.py` creates an anonymous BrassRing session, searches India,
checks the reported total and unique IDs, and retrieves each active job's full
detail sections, including skills and experience. Country and job identity are
verified; city comes from detail fields. Pagination and missing details report
partial results. Session tokens are obtained at runtime and never saved.
Existing saved descriptions refresh while retaining dismissals.

UBS also includes the supplied second board (`siteid=5131`, `LinkID=15232`).
Live verification returned four India CA Intern postings with four full descriptions.
Both boards are collected independently; shared requisition IDs are deduplicated,
and a failed board makes the combined collection partial. The original board
reported 29 jobs in the prior check; the second board adds four distinct IDs.
