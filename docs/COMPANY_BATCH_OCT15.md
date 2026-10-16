# October 15 employer source audit

**106 requested: 63 connected, 43 skipped.** The names-only inventory now contains **228 companies**.

Updated October 16: the user-supplied MathCo PeopleStrong link is now connected. Its public API returned 31 global listings: 29 India and 2 US. All 29 India descriptions were retrieved, with explicit minimum/maximum experience preserved. The listing HTML returns HTTP 404 while the public vacancy API works; the collector uses that API. These 29 roles all parsed to a minimum above zero during this check, so the current fresher filter may hide them. The count is source coverage, not eligible fresher jobs.

This audit verifies career sources, not company-wide pay, workplace quality, fresher eligibility or a guaranteed ₹8 LPA offer. Evaluate the actual role and offer. The existing resume, India and experience filters still apply after collection.

Checks used official career pages, employer-controlled ATS boards, live listing responses and job descriptions. No application was submitted and these checks did not populate SQLite. Run `Start Job Intel.cmd` (or `python run.py` from `app/`) to collect the newly configured sources. `Open Job Intel.cmd` only opens saved results.

Counts are observations from October 15, 2026 and can change during pagination. A global total is explicitly labelled; it is not an India-job count. Workday rows labelled as sample checks were not fully detail-fetched in this audit. Eight representative Workday configurations were also run through complete collection attempts.

C5i follow-up (October 16): all three India tabs are fetched via the public WordPress city action with its freshly delivered nonce. Counts are checked per city and requisition IDs are deduplicated across tabs. All 12 unique job descriptions were retrieved from public detail pages, checking the requisition ID and title. The initial user count was 9; the observed API counts were 10/8/5. All 12 descriptions currently parse to positive experience requirements. Source `0/0` experience pairs are treated as unset placeholders, since Manager 1017 explicitly requires 5–12 years in its JD. If a city later reports additional pages, collection is marked partial rather than claimed complete.

PromptQL/Hasura follow-up (October 16): its public Gem board has 5 entries. The collector retains the Forward Deployed Analyst, Bangalore role with its full JD, which explicitly requires 5+ years. The three US-only roles are excluded using structured country codes. The general talent-community form is excluded because its description explicitly says it is for future interest. The source remains configured for future India vacancies; the current fresher filter hides the present experienced role. The JD states the official company is Hasura, doing business as PromptQL. No candidate/applicant endpoints are called.

Upstox follow-up (October 16): the first-party `service.upstox.com/content/open/v1/jobs/` response includes 55 rows, but only 17 have `post_on_careers_page=1`. The collector selects those published India IDs and matches them by ID/title against the full public Darwinbox listing (18 jobs). The extra Darwinbox-only listing and nonpublic rows are excluded. All 17 full descriptions were verified. Product Intern (CX) has no explicit numeric experience minimum; this remains unknown, not asserted zero. Its structured office location says Mumbai while the JD says Bangalore; source location metadata is retained, so verify the actual office before applying. Explicit source experience fields and numeric Experience headings are retained for the existing parser. No candidate/applicant endpoint is used.

## Connected

| Company | Source | Verification | Observed result |
| --- | --- | --- | --- |
| [Upstox](https://upstox.com/careers/) | upstox | Official published IDs joined to full Darwinbox JDs; October 16 | 17 India jobs; 17 full descriptions; includes Product Intern (CX) |
| [PromptQL (Hasura)](https://jobs.gem.com/promptql) | gem | Entire board plus both India-entry JDs; October 16 | 5 global entries: 3 US-only roles, 1 India vacancy, 1 talent-community form. Collector retains 1 India vacancy with full JD. |
| [C5i](https://www.c5i.ai/careers/) | c5i | All three India city tabs and full details; October 16 | Bengaluru 10, Gurugram 8, Mumbai 5: 12 unique jobs; 12 full descriptions |
| [MathCo](https://mathco-careers.peoplestrong.com/job/joblist) | peoplestrong | Complete paginated board; October 16 | 29 India jobs; 29 full descriptions; 2 US listings excluded |
| [Accenture](https://accenture.wd103.myworkdayjobs.com/AccentureCareers) | workday_india | India search and full-description sample | Reported total 2000 (India search); India JD sample read |
| [Acko](https://careers.kula.ai/acko) | kula | Complete board response | 16 India jobs; 16 descriptions |
| [Airbus](https://ag.wd3.myworkdayjobs.com/Airbus) | workday_india | India search and full-description sample | Reported total 236 (India search); India JD sample read |
| [Akamai Technologies](https://fa-extu-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs) | oracle | Complete board response | 24 India jobs; 24 descriptions |
| [ANZ](https://careers.anz.com/search/?q=&locationsearch=India) | successfactors | Complete board response | 22 India jobs; 22 descriptions |
| [Apollo Global Management](https://athene.wd5.myworkdayjobs.com/Apollo_Careers) | workday_india | Complete board response | 13 India jobs; 13 descriptions |
| [Baker Hughes](https://bakerhughes.wd5.myworkdayjobs.com/BakerHughes) | workday_india | Global listing and India full-description sample | Reported total 726 (global); India JD sample read |
| [Blackstone](https://blackstone.wd1.myworkdayjobs.com/Blackstone_Careers) | workday_india | Complete board response | 4 India jobs; 4 descriptions |
| [BNY](https://eofe.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/BNY-Careers/jobs) | oracle | Partial collection | 148 India jobs; 148 descriptions |
| [Boeing](https://boeing.wd1.myworkdayjobs.com/EXTERNAL_CAREERS) | workday_india | Partial collection | 6 India jobs; 6 descriptions |
| [Broadridge](https://broadridge.wd5.myworkdayjobs.com/Careers) | workday_india | India search and full-description sample | Reported total 38 (India search); India JD sample read |
| [Capital One](https://capitalone.wd12.myworkdayjobs.com/Capital_One) | workday_india | Complete board response | 18 India jobs; 18 descriptions |
| [Cashfree Payments](https://careers.kula.ai/cashfree) | kula | Complete board response | 30 India jobs; 30 descriptions |
| [Citi](https://citi.wd5.myworkdayjobs.com/2) | workday_india | India search and full-description sample | Reported total 939 (India search); India JD sample read |
| [CleverTap](https://careers.kula.ai/clevertap) | kula | Complete board response | 7 India jobs; 7 descriptions |
| [Cloudflare](https://job-boards.greenhouse.io/cloudflare) | greenhouse | Complete board response | 23 India jobs; 23 descriptions |
| [DBS Bank](https://dbs.wd3.myworkdayjobs.com/DBS_Careers) | workday_india | India search and full-description sample | Reported total 466 (India search); India JD sample read |
| [Druva](https://job-boards.greenhouse.io/druva) | greenhouse | Complete board response | 12 India jobs; 12 descriptions |
| [Eightfold AI](https://app.eightfold.ai/careers?location=India) | pcsx | Partial collection | 20 India jobs; 17 descriptions |
| [Elastic](https://job-boards.greenhouse.io/elastic) | greenhouse | Complete board response | 17 India jobs; 17 descriptions |
| [Evalueserve](https://lighthouse.darwinbox.com/ms/candidate/careers) | darwinbox | Complete board response | 13 India jobs; 13 descriptions |
| [ExxonMobil](https://jobs.exxonmobil.com/search/?q=&locationsearch=India) | successfactors | Partial collection | 185 India jobs; 16 descriptions |
| [FactSet](https://factset.wd108.myworkdayjobs.com/FactSetCareers) | workday_india | Complete board response | 22 India jobs; 22 descriptions |
| [Fi Money](https://jobs.lever.co/epifi) | lever | Verified empty board | 0 India jobs; 0 descriptions |
| [Fidelity Investments](https://fmr.wd1.myworkdayjobs.com/FidelityCareers) | workday_india | India search and full-description sample | Reported total 14 (India search); India JD sample read |
| [FIS](https://fis.wd5.myworkdayjobs.com/SearchJobs) | workday_india | Global listing and India full-description sample | Reported total 545 (global); India JD sample read |
| [Gartner](https://gartner.wd5.myworkdayjobs.com/EXT) | workday_india | India search and full-description sample | Reported total 37 (India search); India JD sample read |
| [GE Aerospace](https://geaerospace.wd5.myworkdayjobs.com/GE_ExternalSite) | workday_india | Global listing and India full-description sample | Reported total 628 (global); India JD sample read |
| [Harness](https://job-boards.greenhouse.io/harnessinc) | greenhouse | Complete board response | 8 India jobs; 8 descriptions |
| [HighRadius](https://job-boards.greenhouse.io/highradius) | greenhouse | Complete board response | 50 India jobs; 50 descriptions |
| [Honeywell](https://ibqbjb.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs) | oracle | Partial collection | 289 India jobs; 161 descriptions |
| [Icertis](https://iaaviz.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/Jobs-at-Icertis/jobs) | oracle | Complete board response | 24 India jobs; 24 descriptions |
| [Innovaccer](https://apply.workable.com/innovaccer-analytics) | workable | Complete board response | 45 India jobs; 45 descriptions |
| [IQVIA](https://iqvia.wd1.myworkdayjobs.com/IQVIA) | workday_india | India search and full-description sample | Reported total 53 (India search); India JD sample read |
| [JFrog](https://job-boards.greenhouse.io/jfrog) | greenhouse | Complete board response | 6 India jobs; 6 descriptions |
| [Jupiter Money](https://jupiter.keka.com/careers) | keka | Complete board response | 5 India jobs; 5 descriptions |
| [LatentView Analytics](https://latentview.darwinbox.in/ms/candidate/careers) | darwinbox | Complete board response | 10 India jobs; 10 descriptions |
| [MoEngage](https://moengage.hire.trakstar.com/) | trakstar | Complete board response | 18 India jobs; 18 descriptions |
| [Morningstar](https://morningstar.wd5.myworkdayjobs.com/Americas) | workday_india | India search and full-description sample | Reported total 11 (India search); India JD sample read |
| [Nasdaq](https://nasdaq.wd1.myworkdayjobs.com/Global_External_Site) | workday_india | India search and full-description sample | Reported total 34 (India search); India JD sample read |
| [NatWest Group](https://rbs.wd3.myworkdayjobs.com/RBS) | workday_india | Complete board response | 47 India jobs; 47 descriptions |
| [Northern Trust](https://ntrs.wd1.myworkdayjobs.com/northerntrust) | workday_india | India search and full-description sample | Reported total 93 (India search); India JD sample read |
| [Observe.AI](https://job-boards.greenhouse.io/observeai) | greenhouse | Complete board response | 4 India jobs; 4 descriptions |
| [Perfios](https://perfios.darwinbox.in/ms/candidate/careers) | darwinbox | Complete board response | 3 India jobs; 3 descriptions |
| [Porter](https://porter.darwinbox.in/ms/candidate/careers) | darwinbox | Partial collection | 45 India jobs; 32 descriptions |
| [Quantiphi](https://quantiphi.wd1.myworkdayjobs.com/Careers_at_Quantiphi) | workday_india | Complete board response | 42 India jobs; 42 descriptions |
| [Shell](https://shell.wd3.myworkdayjobs.com/ShellCareers) | workday_india | India search and full-description sample | Reported total 16 (India search); India JD sample read |
| [Slice](https://careers.kula.ai/slice) | kula | Complete board response | 36 India jobs; 36 descriptions |
| [Spinny](https://spinzone.darwinbox.in/ms/candidate/careers) | darwinbox | Complete board response | 5 India jobs; 5 descriptions |
| [State Street](https://statestreet.wd1.myworkdayjobs.com/Global) | workday_india | India search and full-description sample | Reported total 340 (India search); India JD sample read |
| [Sumo Logic](https://job-boards.greenhouse.io/sumologic) | greenhouse | Complete board response | 5 India jobs; 5 descriptions |
| [Thomson Reuters](https://thomsonreuters.wd5.myworkdayjobs.com/External_Career_Site) | workday_india | Partial collection | 36 India jobs; 36 descriptions |
| [ThoughtSpot](https://thoughtspot.wd5.myworkdayjobs.com/careers) | workday_india | Verified empty board | 0 India jobs; 0 descriptions |
| [Tiger Analytics](https://apply.workable.com/tiger-analytics) | workable | Complete board response | 4 India jobs; 4 descriptions |
| [UiPath](https://jobs.ashbyhq.com/uipath) | ashby | Complete board response | 7 India jobs; 7 descriptions |
| [Uniphore](https://uniphore.wd503.myworkdayjobs.com/Uniphore) | workday_india | India search and full-description sample | Reported total 4 (India search); India JD sample read |
| [Wells Fargo](https://wf.wd1.myworkdayjobs.com/WellsFargoJobs) | workday_india | India search and full-description sample | Reported total 98 (India search); India JD sample read |
| [Whatfix](https://whatfix101.hire.trakstar.com/) | trakstar | Complete board response | 27 India jobs; 27 descriptions |
| [Wingify](https://wingify.keka.com/careers) | keka | Complete board response | 19 India jobs; 19 descriptions |

### Partial sources and coverage limits

- Boeing returned six usable India records and one malformed listing without the usual detail path.
- BNY and Honeywell returned changing/repeated listing totals. The adapters flag incomplete counts; the 180-second Honeywell probe did not read all descriptions.
- Eightfold AI exposed full public JSON-LD descriptions for 17 of 20 accepted India listings during the check. The remaining descriptions were unavailable.
- Porter returned missing JD bodies for some vacancies. Available source experience metadata is retained, and the source is marked partial.
- ExxonMobil returned all 185 listing records in the final attempt, but only 16 full descriptions were available in the limited probe. Missing descriptions remain visible as a partial result, not a complete fetch.
- Thomson Reuters scoped results included foreign primary-country details. Only verified India options are accepted. Explicit India secondary locations are supported; city-only foreign-primary alternatives are not guessed.
- ThoughtSpot and Fi Money are connected valid empty boards. A zero result does not mean a request failed.
- Accenture reported 2,000 India results. This audit did not prove that its source count is uncapped or that every current Accenture vacancy is represented.
- Tiger Analytics uses the verified Workable board; complete coverage of every other Tiger recruiting channel is not established.
- A working feed does not prove a posting remains open indefinitely. There was no signed-in browser or application-submission test.

## Skipped — direct job-search or ATS links would help

These companies have no new active collector from this batch. A public careers homepage was often found; the blocker can be access, an old board, an unsupported portal or unverified listing/description coverage. A direct vacancy/search/ATS link is more useful than the same homepage.

| Company | Best career page found | Why skipped |
| --- | --- | --- |
| Angel One | [Career page](https://www.angelone.in/careers) | Official careers page found; a usable full vacancy feed was not verified. |
| Ather Energy | [Career page](https://careers.atherenergy.com/jobs) | Current search page found; delivered Next.js data contains header/footer content rather than a verified vacancy array. |
| Axtria | [Career page](https://www.axtria.com/axtria-careers/) | Official page links individual JazzHR/SuccessFactors requisitions; a complete public listing feed was not verified. |
| Bain & Company | [Career page](https://www.bain.com/careers/find-a-role/) | Public search and its custom search endpoint were found; pagination and full-description integration remain unverified. |
| BharatPe | [Career page](https://bharatpe.com/careers/) | Careers route served a general landing page; no matching current vacancy feed found. Bharat Petroleum is a different employer. |
| Blinkit | [Career page](https://blinkit.com/careers) | Careers request returned HTTP 403; no verified current corporate vacancy feed. |
| BNP Paribas | [Career page](https://www.bnpparibas.bank.in/en/work-with-us/apply-now/) | Group careers request returned HTTP 403. India careers link found, but a usable vacancy feed was not verified. |
| Cars24 | [Career page](https://www.cars24.com/careers/) | Official careers pages found; a complete current job feed was not verified. |
| Chargebee | [Career page](https://www.chargebee.com/company/careers/join-us/) | Current official Join Us links point to LinkedIn; guessed legacy Greenhouse/Workday feeds failed. LinkedIn aggregation stays removed. |
| CRISIL | [Career page](https://career.crisil.com/crisil/) | Custom careers portal found; no verified public listing/description feed. |
| EPAM Systems | [Career page](https://careers.epam.com/en/jobs/india) | Older careers request was blocked; new official India search found, but collection remains unverified. |
| Factspan Analytics | [Career page](https://www.factspan.com/current-opening-jobs/) | Current page embeds factspan.oorwin.ai; that portal needs a verified listing/description adapter. |
| HSBC | [Career page](https://portal.careers.hsbc.com/careers?location=India) | India page found, but the collector did not receive a usable public positions response. |
| IBM | [Career page](https://careers.ibm.com/en_US/careers) | Career search redirected to a blank HTTP 202 response; no usable current vacancy feed was verified. |
| INDmoney | [Career page](https://www.indmoney.com/careers) | Careers request returned HTTP 403; no verified alternative. Indel Money is a different employer. |
| Informatica | [Career page](https://www.informatica.com/about-us/careers.html) | Redirects to Salesforce careers. Salesforce is already configured; separate Informatica coverage was not verified. |
| Ixigo | [Career page](https://careers.ixigo.com/) | Official careers frontend found; public listing/description feed remains unverified. |
| Jio Platforms | [Career page](https://careers.jio.com/) | Official Jio careers portal found; complete category pagination and full descriptions remain unverified. |
| Kearney | [Career page](https://kearney.taleo.net/careersection/078/joblist.ftl) | Official careers access returned HTTP 403; Taleo board found, but collection is not verified. |
| Livspace | [Career page](https://careers.livspace.com/livspace/) | Official custom careers portal found; public listing/description integration remains unverified. |
| Macquarie Group | [Career page](https://recruitment.macquarie.com/en_US/careers) | Public Avature search found; complete India pagination and descriptions remain unverified. |
| McKinsey & Company | [Career page](https://www.mckinsey.com/careers/search-jobs?countries=India) | Initial careers request timed out; India search URL found, but complete listing/description collection remains unverified. |
| Mercedes-Benz Research and Development India | [Career page](https://www.mbrdi.co.in/careers/) | Official careers page found; an MBRDI-specific India vacancy feed was not verified. |
| Moody's | [Career page](https://careers.moodys.com/en/location/india-jobs/49841/1269750/2/1) | Official India TalentBrew search found; a complete collector was not verified. |
| MSCI | [Career page](https://careers.msci.com/job-search) | Custom search portal found; listing and full-description API integration remains unverified. |
| NoBroker | [Career page](https://www.nobroker.in/careers.php) | Specific careers page found; /careers returned general property content, and a vacancy feed remains unverified. |
| Nykaa | [Career page](https://careers.nykaa.com/) | Current Skima careers frontend found; its public listing/description integration remains unverified. |
| OfBusiness | [Career page](https://www.ofbcareers.com/) | Current careers site found after the old route returned HTTP 410; job-feed integration remains unverified. |
| Oliver Wyman | [Career page](https://careers.marsh.com/global/en/oliver-wyman) | Marsh careers hosts several brands; an Oliver Wyman-only India feed was not verified. |
| OneCard | [Career page](https://www.getonecard.app/careers/) | FPL careers page found; no verified current machine-readable vacancy feed. Similar-name OneCard sites were not substituted. |
| OYO | [Career page](https://www.oyorooms.com/careers/) | Old careers route redirected to hotel booking; no verified current recruitment portal. Similar-name OY India was not substituted. |
| Persistent Systems | [Career page](https://careers.persistent.com/jobslist) | Current custom jobs portal found; public listing/description integration remains unverified. |
| Pine Labs | [Career page](https://www.pinelabs.com/careers/open-jobs) | Official openings page found; full listing/description feed remains unverified. |
| Publicis Sapient | [Career page](https://careers.publicissapient.com/job-search) | Official search found; a Sapient-only feed and complete descriptions were not verified. Other Publicis brands were not substituted. |
| Schneider Electric | [Career page](https://careers.se.com/india?lang=en-US) | Careers/search requests returned HTTP 403; no usable public feed was verified. |
| SLB | [Career page](https://careers.slb.com/job-listing) | Official job-listing page found; complete India listing/description integration remains unverified. |
| smallcase | [Career page](https://smallcase.freshteam.com/jobs) | Freshteam board found; existing Lever slug failed and current Freshteam collection remains unverified. |
| Societe Generale | [Career page](https://careers.societegenerale.com/en/search?refinementList%5BjobLocation%5D%5B0%5D=IND) | Official India search found; custom search integration remains unverified. |
| Urban Company | [Career page](https://careers.urbancompany.com/jobs) | Current React job-search portal found; public listing/description integration remains unverified. |
| WebEngage | [Career page](https://webengage.sensehq.com/careers) | Current Sense portal found; its full listing/description feed is not integrated. |
| Yellow.ai | [Career page](https://yellow.ai/career/) | Current careers page found after the older /careers/ route failed; public vacancy feed remains unverified. |
| Zetwerk | [Career page](https://www.zetwerk.com/careers/) | Official page links Sense job pages; complete listing coverage and full-description integration remain unverified. |
| Zomato | [Career page](https://www.eternal.com/careers/) | Old Zomato1 SmartRecruiters board contains 2015-2016 postings, so it was rejected. A current Eternal/Zomato vacancy feed was not verified. |

## Implementation and checks

- `config.py`: only verified boards were enabled. Pending names were not registered as placeholder collectors.
- `fetchers/employer_portals.py`: shared Darwinbox, Keka, Kula, Trakstar, Oracle, SuccessFactors and PCSX adapters. They read public vacancy data, retain full available descriptions, select explicit India locations and report partial collections.
- Greenhouse: Cloudflare uses geographic metadata instead of its `In-Office` label. Observe.AI and JFrog use explicit office-country metadata for city-only locations.
- Ashby: UiPath uses its structured address country.
- Workable: current flat/array location formats are supported, India locations are selected and duplicate shortcodes are merged. Innovaccer uses `innovaccer-analytics`, not the old empty `innovaccer` board.
- Workday: four employer boards can overlap, with four detail workers per board. Detail workers reuse their own sessions. New feeds verify country metadata, keep explicit India secondary options, and close sessions after collection.
- Offline checks cover foreign-location rejection, pagination/count failures, empty-vs-failed responses, UTF-8 Kula text references, job identity, full qualification tails and source-specific country formats.
- Python compile check passed. Full offline suite: **247 tests passed**.
- The original 75-company manifests retain their original scope. This file and the JSON alongside it record the new request.
