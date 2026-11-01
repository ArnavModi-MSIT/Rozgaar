# 30 October 2026: 100-employer target check

All 100 supplied names were checked against the current inventory and public careers pages. **27 new sources registered: 25 with India listings and 2 valid empty India monitors. One alias already connected; 72 remain unresolved.** The inventory rises from 292 to **319** company/display-name entries.

The connected feeds returned **1,053 India listings** in this read-only check. All stored text fields are nonempty, but **one Clear posting has no source JD and only experience metadata**; that source correctly reports partial status. Nonempty text does not establish description completeness, suitable experience, current student eligibility or a relevant vacancy. These are all-role employer feeds, not a list of fresher vacancies.

The input file is a screening list. Its evidence labels (13 D, 52 E, 35 P) are preserved in [the complete audit manifest](CAREER_TARGETS_20261030.json); salary research was not reverified. No feed is classified as paying every fresher INR 8 LPA or more. All 100 rows, discovery links, outcomes and blockers are recorded in that manifest.

## Connected feeds

| Target | Company | Collector | India listings | Nonempty stored text | Notes |
|---:|---|---|---:|---:|---|
| 1 | [Medpace](https://careers.medpace.com/jobs) | `employer_portals` | 53 | 53 |  |
| 2 | [YipitData](https://job-boards.greenhouse.io/yipitdatajobs) | `greenhouse` | 10 | 10 |  |
| 3 | [Beghou Consulting](https://jobs.lever.co/beghouconsulting) | `lever` | 41 | 41 |  |
| 4 | [Delphi Consulting](https://job-boards.greenhouse.io/delphiconsulting) | `greenhouse` | 11 | 11 |  |
| 6 | [United Airlines](https://careers.united.com/us/en/c/digital-technology-jobs) | `employer_portals` | 19 | 19 | India-wide feed; 13 Digital Technology roles plus six other India roles. Full external employer body and qualifications. |
| 7 | [Nielsen](https://careers.smartrecruiters.com/TheNielsenCompany) | `smartrecruiters` | 47 | 47 |  |
| 12 | [Atlan](https://jobs.ashbyhq.com/atlan) | `ashby` | 5 | 5 |  |
| 13 | [Hevo Data](https://jobs.lever.co/hevodata) | `lever` | 51 | 51 |  |
| 14 | [o9 Solutions](https://o9solutions.wd5.myworkdayjobs.com/o9SolutionsExternal) | `workday_india` | 40 | 40 |  |
| 15 | [DataWeave](https://dataweave.com/in/careers) | `employer_portals` | 1 | 1 | Technical Architect; full HTML description, senior role. |
| 16 | [Epsilon](https://careers.publicisgroupe.com/epsilon/jobs) | `employer_portals` | 67 | 67 |  |
| 23 | [Boomi](https://job-boards.greenhouse.io/boomilp) | `greenhouse` | 0 | 0 | Valid feed; no India postings at verification. Included as an empty monitor, not a current opportunity. |
| 24 | [Qlik](https://careerhub.qlik.com/careers?location=India) | `employer_portals` | 9 | 9 |  |
| 26 | [Kissht](https://app1596.workline.hr/Cportal/GeneralOpening.aspx) | `employer_portals` | 276 | 276 | Partial: brief/placeholder JDs present; full returned text retained. |
| 33 | [Nium](https://jobs.lever.co/nium) | `lever` | 11 | 11 |  |
| 39 | [Moneyview](https://moneyview.darwinbox.in/ms/candidatev2/main/careers/allJobs) | `employer_portals` | 9 | 9 |  |
| 43 | [Clear (ClearTax)](https://clear.darwinbox.in/ms/candidatev2/main/careers/allJobs) | `employer_portals` | 15 | 15 | Partial: one posting has no source JD, only experience metadata. Nonempty is not completeness. |
| 47 | [Signzy](https://signzy.keka.com/careers/) | `employer_portals` | 17 | 17 |  |
| 48 | [Open Financial Technologies](https://openfinancial.keka.com/careers/) | `employer_portals` | 0 | 0 | Valid feed; no India postings at verification. Included as an empty monitor, not a current opportunity. |
| 50 | [Experian India](https://careers.smartrecruiters.com/Experian) | `smartrecruiters` | 33 | 33 |  |
| 51 | [PharmEasy](https://myhr.darwinbox.in/ms/candidatev2/main/careers/allJobs) | `employer_portals` | 8 | 8 |  |
| 62 | [Ninjacart](https://ninjacart.darwinbox.in/ms/candidatev2/main/careers/allJobs) | `employer_portals` | 5 | 5 |  |
| 78 | [Darwinbox](https://dbx.darwinbox.in/ms/candidatev2/main/careers/allJobs) | `employer_portals` | 18 | 18 |  |
| 85 | [WebEngage](https://webklipper.keka.com/careers/) | `employer_portals` | 20 | 20 |  |
| 93 | [Nokia India](https://fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs) | `employer_portals` | 128 | 128 |  |
| 94 | [Texas Instruments India](https://edbz.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/jobs) | `employer_portals` | 121 | 121 |  |
| 99 | [TransUnion CIBIL](https://transunion.wd5.myworkdayjobs.com/TransUnion) | `workday_india` | 38 | 38 | Broader TransUnion India group feed, not a dedicated TransUnion CIBIL board; CIBIL-specific vacancies not established. |

Greenhouse, Lever and Ashby checks used complete single-response public feeds and the production parser. SmartRecruiters, Darwinbox, Workday, Oracle, PCSX and Jibe checks paginated through the production adapters and fetched descriptions. Counts can change. The earlier 26 October batch remains separate and unchanged.

TransUnion uses the broader group India feed; do not interpret its 38 records as 38 CIBIL vacancies. Nokia and Texas Instruments use public Oracle feeds. Nielsen is separate from the existing NielsenIQ source.

## Already connected alias

Course5 Intelligence is C5i, verified against [C5i's rebrand notice](https://www.c5i.ai/wp-content/uploads/Course5_Intelligence_Unveils_New_Brand_Identity.pdf). The existing `c5i` source is reused, with no duplicate registration.

## Unresolved companies

An official page alone is not a completed integration. The following companies were **not registered**. A current India job-detail URL helps resolve sources; unsupported ATS integrations need adapter work. Access denials were not bypassed.

| Target | Company / discovered page | Remaining blocker |
|---:|---|---|
| 5 | [Inquizity](https://inquizity.com/careers-at-inquizity/) | Correct URL supplied; careers page, [sample detail](https://inquizity.com/operations-consultant-vacancy-page/) and normal public WordPress pages API return ModSecurity HTTP 406 to the local collector. Not registered. |
| 8 | [Anveshan](https://www.anveshan.farm/pages/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 9 | [Urban Harvest](https://urbanharvest.in/) | Employer identity/careers feed not established; Urban Harvest is an ambiguous name. |
| 10 | [Loyalty Juggernaut](https://www.loyaltyjuggernaut.com/careers) | Careers host did not resolve; need the intended employer's working official link. |
| 11 | [GoComet](https://www.gocomet.com/company/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 17 | [Merkle](https://www.merkle.com/en/careers/jobs.html) | Official Merkle job search found; dedicated brand scope and detail extraction not established. |
| 19 | [Impetus Technologies](https://www.impetus.com/careers/) | Official site links to impetus.cluster3.openings.co; this ATS needs a new adapter. |
| 20 | [Datametica](https://www.datametica.com/careers/) | Official careers request returned HTTP 406. |
| 21 | [RudderStack](https://www.rudderstack.com/careers/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 22 | [Informatica](https://www.salesforce.com/company/careers/jobs/?search=informatica&pagesize=20&bc=OTH#results) | Careers host redirects to Salesforce careers; Informatica-specific coverage through the existing Salesforce source is unverified. |
| 25 | [SAS Institute](https://www.sas.com/en_in/careers.html) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 27 | [Policybazaar](https://www.policybazaar.com/careers/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 28 | [BharatPe](https://bharatpe.com/career/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 29 | [Pine Labs](https://www.pinelabs.com/careers/open-jobs) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 30 | [Angel One](https://www.angelone.in/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 31 | [Bajaj Finance](https://www.bajajfinserv.in/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 32 | [M2P Fintech](https://m2pfintech.com/view-jobs/) | Careers request returned HTTP 404; no working listing/full-description feed established. |
| 34 | [Niyo Solutions](https://goniyo.com/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 35 | [Khatabook](https://khatabook.com/careers) | Official careers request failed (ReadTimeout); no working public feed established. |
| 36 | [KreditBee](https://www.kreditbee.in/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 37 | [Fibe](https://www.fibe.in/careers/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 38 | [INDmoney](https://www.indmoney.com/careers) | Careers request returned HTTP 403; no working listing/full-description feed established. |
| 40 | [smallcase](https://www.smallcase.com/404) | Official site points to a PyjamaHR board; no verified adapter for this ATS yet. |
| 41 | [Rupeek](https://www.rupeek.com/careers/) | Official careers request failed (ConnectionError); no working public feed established. |
| 42 | [MobiKwik](https://www.mobikwik.com/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 44 | [Yubi](https://www.go-yubi.com/careers/) | HTTP 403 from official careers page; not bypassed. |
| 45 | [OneCard (FPL Technologies)](https://www.fplabs.tech/careers/) | OneCard links to FPL Labs careers; returned redirect without a usable board. |
| 46 | [National Payments Corporation of India (NPCI)](https://www.npci.org.in/who-we-are/careers) | Official NPCI page returned HTTP 403; not bypassed. |
| 49 | [Lendingkart](https://www.lendingkart.com/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 52 | [CARS24](https://careers.cars24.com/) | Official CARS24 careers app found; public list/detail API not established. |
| 53 | [Dream11](https://www.dreamsports.group/lifeatdreamsports) | Official Dream Sports site links to jobs.lever.co/dreamsports, but that API returns HTTP 404. |
| 54 | [Zomato (Eternal)](https://www.eternal.com/careers/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 55 | [Urban Company](https://careers.urbancompany.com/) | Official careers app found; current list/detail API not established. |
| 56 | [ShareChat](https://sharechat.com/careers) | Official page reachable; attempted Lever/Ashby/Kula accounts unavailable. Need a current job-detail link. |
| 57 | [Delhivery](https://www.delhivery.com/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 58 | [Shadowfax](https://www.shadowfax.in/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 59 | [Shiprocket](https://www.shiprocket.in/careers/) | Official Shiprocket careers page returned HTTP 403; not bypassed. |
| 60 | [Rebel Foods](https://www.rebelfoods.com/career) | Careers request returned HTTP 500; no working listing/full-description feed established. |
| 61 | [Country Delight](https://countrydelight.in/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 63 | [Udaan](https://udaan.com/careers) | Official Udaan request timed out; attempted standard boards unavailable. |
| 64 | [Moglix](https://www.moglix.com/careers) | Careers request returned HTTP 404; no working listing/full-description feed established. |
| 65 | [Licious](https://www.licious.in:443/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 66 | [Nykaa](https://www.nykaa.com/careers) | Careers request returned HTTP 403; no working listing/full-description feed established. |
| 67 | [Purplle](https://www.purplle.com/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 68 | [Practo](https://practo.app.param.ai/jobs/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 69 | [Apollo 24/7](https://www.apollo247.com/careers) | Candidate Apollo 24/7 careers URL returned HTTP 404; current feed not established. |
| 70 | [Ather Energy](https://www.atherenergy.com/careers) | Official careers page returned HTTP 403; not bypassed. |
| 71 | [Ola Cabs](https://www.olacabs.com/careers) | Ola links to a TurboHire recruitment board; adapter not established. Shared board may include Ola Electric. |
| 72 | [Ola Electric](https://www.olaelectric.com/careers) | Ola Electric links to the Ola TurboHire board; brand-specific scope not established. |
| 73 | [ixigo](https://careers.ixigo.com/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 74 | [Yulu](https://www.yulu.bike/careers/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 75 | [BlackBuck (Zinka Logistics)](https://www.blackbuck.com/careers/) | Official request returned HTTP 502; attempted standard board unavailable. |
| 76 | [Chargebee](https://jobs.chargebee.com/) | Current official Chargebee page sends candidates to LinkedIn. The older jobs.chargebee.com site is reachable but current listing coverage not established. |
| 77 | [Capillary Technologies](https://www.capillarytech.com/careers/) | Official careers page returned HTTP 403; not bypassed. |
| 79 | [Exotel](https://exotel.com/about-us/careers/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 80 | [Gupshup](https://www.gupshup.ai:443/careers) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 81 | [Plivo](https://www.plivo.com/jobs/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 82 | [Zoho Corporation](https://www.zoho.com/careers/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 83 | [Clari](https://www.salesloft.com/company/careers) | Clari careers page redirects to Salesloft/combined company branding; current brand-specific board not verified. |
| 84 | [Tracxn](https://tracxn.com/careers) | Careers request returned HTTP 404; no working listing/full-description feed established. |
| 86 | [Netcore Cloud](https://netcore.ai/careers/) | Official page embeds careerpagenetcore.lovable.app; public list/detail feed not established. |
| 87 | [Yellow.ai](https://yellow.ai/wp-content/uploads/2023/04/Careers.png) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |
| 88 | [ADP](https://jobs.adp.com/) | Official ADP jobs page returned HTTP 403; not bypassed. |
| 89 | [EPAM Systems](https://www.epam.com/careers) | Official EPAM careers page returned HTTP 403; not bypassed. |
| 90 | [GlobalLogic](https://www.globallogic.com/careers/) | Custom official GlobalLogic listings found; complete India pagination/detail adapter not established. |
| 91 | [LTIMindtree](https://www.ltm.com/careers) | Official page links to LTM/RippleHire recruitment; public India feed not established. Published query tokens were not copied into source configuration. |
| 92 | [Persistent Systems](https://careers.persistent.com/) | Custom Persistent careers page found; list/detail adapter not established. |
| 95 | [Arm India](https://careers.arm.com/) | Official Arm TalentBrew site found; India pagination/detail adapter not established. |
| 96 | [Moody's](https://careers.moodys.com/en) | Official Moody's TalentBrew site found; India pagination/detail adapter not established. |
| 97 | [MSCI](https://careers.msci.com/) | Official MSCI site found; attempted /api/jobs unavailable; actual search API still needed. |
| 98 | [CRISIL](https://career.crisil.com/crisil/) | Official CRISIL site points to career.crisil.com/crisil (Zwayam); company-specific search identity not established. |
| 100 | [Bain & Company](https://www.bain.com/careers/) | Official page reachable; no validated supported listing/full-description feed established in this pass. Needs a current India job-detail link or a new adapter. |

## Implementation and verification

New declarations live in `backend/config/career_targets_20261030.py`. Registration extends existing inventories; it does not copy jobs into the database. The Jibe adapter validates India country, Medpace client identity, Epsilon brand, page totals, unique requisitions and full returned text. Empty or interrupted pages fail or report partial results rather than success. All new standard boards require positive India evidence.

Checks use no applicant endpoints, cookies, resume submission, or logged-in browser. Private HTTP snapshots and diagnostics remain under ignored `runtime/artifacts/expansion-20261030/`. Collection still starts only from the website.

### Inquizity follow-up, 30 October 2026

The user supplied the correct careers URL and an Operations Consultant detail link. The supplied screenshot and indexed page expose department tabs; any eventual adapter must include every tab, not just Consulting. Direct local GET checks for both pages and the ordinary public WordPress REST pages endpoint return HTTP 406 with an explicit Mod_Security message. The indexed descriptions are not a current runtime feed. Inquizity remains unresolved and is excluded from the 25 registered sources until permitted extraction can be verified. No browser profile, account, application or database state was changed.

### United Airlines follow-up, 30 October 2026

The user supplied the Digital Technology category URL and a count of 19. Live public search verified 19 India-wide roles, including 13 Digital Technology roles; the collector intentionally keeps all India categories, including Corporate analyst roles. Pagination uses the live total, not a hard-coded 19-job cap. All 19 unique requisitions returned nonempty full external employer descriptions plus qualifications (longest normalized body 7,217 characters). The adapter parses the public `phApp.ddo` JSON as data, verifies employer, requisition, title and country, and exports only standard public job fields. Search teasers, application URLs, internal HR/recruiter fields and account endpoints are not used.

[Follow-up checks for 20 targets](CAREER_RETRY_20_20261030.md)

### Kissht Workline follow-up

Verified 276 unique public openings, matching the supplied count. The public GetCurrentopening method returns the full list in one response; pagination in the UI is local. Only Kissht/India rows are accepted. The collector reads public posting pages, retains all returned JD/responsibilities/qualification/experience text, and reports partial status for brief or missing JDs. No candidate sign-in, resume posting or application endpoints are used. Some source JDs say only "As like ABM"; do not interpret the 276 nonempty fields as 276 complete descriptions.
