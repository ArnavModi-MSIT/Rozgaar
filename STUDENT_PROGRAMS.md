# Student opportunity sources

Checked 2026-10-05. Program links are displayed in the React student directory, not inserted into SQLite as fake vacancies. Existing India collectors remain active.

| Company | Official student page | Coverage |
| --- | --- | --- |
| Google | [Official page](https://buildyourfuture.withgoogle.com/) | India intern/apprentice search already collected. |
| Microsoft | [Official page](https://careers.microsoft.com/v2/global/en/students) | India Intern and Entry searches already collected. |
| Amazon | [Official page](https://www.amazon.jobs/content/en/career-programs/university) | Dedicated India intern and apprentice searches collected. |
| NVIDIA | [Official page](https://www.nvidia.com/en-us/about-nvidia/careers/university-recruiting/) | Existing Workday feed; separate student portal coverage not verified. |
| Apple | [Official page](https://www.apple.com/careers/us/work-at-apple/students.html) | Existing India jobs feed; this program page is global. |
| Meta | [India internship search](https://www.metacareers.com/jobsearch/?offices[0]=Mumbai%2C%20India&offices[1]=Gurgaon%2C%20India&offices[2]=Bangalore%2C%20India&offices[3]=Hyderabad%2C%20India&offices[4]=New%20Delhi%2C%20India&roles[0]=Internship) | Existing all-role India feed covers the same five offices; checked internship search returned 0. |
| Goldman Sachs | [Official page](https://www.goldmansachs.com/careers/students/programs-and-internships/india/summer-analyst-program) | India 2027 Summer Analyst page specifies graduation in 2028; check separate campus applications manually. |
| JPMorgan Chase | [Official page](https://www.jpmorganchase.com/careers/explore-opportunities/students-and-graduates) | India Oracle feed connected; separate programs require manual checking. |
| Morgan Stanley | [Official page](https://www.morganstanley.com/careers/career-opportunities-search?opportunity=sg) | Separate student feed connected; India programs with descriptions collected. |
| Salesforce | [Official page](https://www.salesforce.com/company/careers/university/) | Futureforce program page; existing Workday feed connected. |

Amazon: dedicated India `intern` search returned 3 postings, `apprentice` returned 0 at verification. Both searches paginate and deduplicate through the existing Amazon adapter; zero now does not disable a search. Other existing feeds were not exhaustively recollected during this change.

The student checkbox matches titles only (intern, internship, apprentice, apprenticeship, student, summer analyst, summer associate, industrial trainee, co-op). It applies across all companies and keeps normal location, experience, resume-match and new-job filters. It can miss student eligibility mentioned only in descriptions. It does not treat all graduate full-time roles as current-student opportunities. Review enrollment, graduation year and required experience in the description.

Goldman Sachs campus application coverage remains unverified. Morgan Stanley's separate student feed is now registered: checked 2026-10-05, 99 global programs and 1 India program (20736, Financial Control Group Industrial Trainee Program, Mumbai). This is a source listing, not a claim of eligibility or a verified application deadline. Meta's supplied India internship search was checked through its public GraphQL endpoint: 0 internship rows versus 25 rows in the general India search. The existing unfiltered collector remains active and includes internship roles when published; no extra duplicate collector is needed. Global program pages do not establish India availability or an open application window.

## Additional 20 companies

Checked 2026-10-05. The directory now contains 30 searchable companies. Existing adapters remain active when student roles share the general board. Source probes did not write SQLite or submit applications. Title counts are discovery signals, not confirmed eligibility; see each listing check's scope in [STUDENT_SOURCE_AUDIT.json](STUDENT_SOURCE_AUDIT.json).

| Company | Official program or fallback page | Observed coverage / limitations |
| --- | --- | --- |
| Adobe | [Open page](https://careers.adobe.com/us/en/university) | India rows observed: 78; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. |
| Intuit | [Open page](https://www.intuit.com/careers/programs/internships/) | India rows observed: 27; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. |
| Stripe | [Open page](https://stripe.com/in/careers/emerging-talent) | India rows observed: 43; student titles: 2. Existing listing feed remains connected. Global program page; check India availability. |
| Databricks | [Open page](https://www.databricks.com/company/careers/university-recruiting) | India rows observed: 92; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. |
| Atlassian | [Open page](https://www.atlassian.com/company/careers/earlycareers) | India rows observed: 56; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. |
| Uber | [Open page](https://jobs.uber.com/en/teams/emerging-talent/?id=160) | India rows observed: 20; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. Direct program-page request returned 403; the listing feed responded. |
| Rubrik | [Open page](https://www.rubrik.com/company/careers) | India rows observed: 32; student titles: 3. Early Career section on official careers page; internship listings come from the existing Greenhouse board. Direct program-page request returned 403; the listing feed responded. |
| Snowflake | [Open page](https://careers.snowflake.com/university) | India rows observed: 11; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. |
| ServiceNow | [Open page](https://careers.servicenow.com/early-careers/) | India rows observed: 77; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. Direct program-page request returned 403; the listing feed responded. |
| Palo Alto Networks | [Open page](https://jobs.paloaltonetworks.com/en/early-in-career) | India rows observed: 161; student titles: 0. Existing India Workday feed responds. Internship button uses RippleMatch; that separate route remains manual review only. |
| PayPal | [Open page](https://careers.pypl.com/university-hiring/University-Overview/default.aspx) | India rows observed: 11; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. Direct program-page request returned 403; the listing feed responded. |
| Visa | [Open page](https://corporate.visa.com/en/careers/early-careers.html) | India rows observed: 2; student titles: 0. Added separate Visa Early Careers Workday board. Its 2 India roles currently have nonstudent titles; check eligibility. |
| Mastercard | [Open page](https://careers.mastercard.com/us/en/early-careers/internships) | India rows observed: 211; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. |
| American Express | [Open page](https://www.americanexpress.com/en-us/careers/student-programs/global-students-page.html) | India rows observed: 25; student titles: 3. Only the first India page was recounted. Apprenticeships may require completed graduation; check the description. |
| BlackRock | [Open page](https://careers.blackrock.com/students-and-graduates-apac) | India rows observed: 42; student titles: 0. APAC campus links use the same careers site; linked regional programs did not list India. |
| Arcesium | [Open page](https://www.arcesium.com/careers) | India rows observed: 25; student titles: 0. General careers fallback; dedicated student page not found. Existing Greenhouse board remains connected. |
| Qualcomm | [Open page](https://www.qualcomm.com/company/careers/internships-and-early-in-career-opportunities) | India rows observed: 583; student titles: 0. Eightfold descriptions are department summaries; review the full employer description before applying. |
| Walmart Global Tech | [Open page](https://careers.walmart.com/us/en/home/careers-areas/students) | India rows observed: 229; student titles: 1. Added complete India listing scan and student-title selection outside the narrow Global Tech query. Grad Intern - No Work Experience found. Program hub is US-focused. |
| Expedia Group | [Open page](https://careers.expediagroup.com/emerging-talent-and-careers/) | India rows observed: 21; student titles: 0. Existing descriptions are team summaries; review the full employer description before applying. Direct program-page request returned 403; the listing feed responded. |
| Bloomberg | [Open page](https://www.bloomberg.com/company/early-careers/) | India rows observed: 7; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. Direct program-page request returned 403; the listing feed responded. |

### Newly connected collection paths

- `workday_students`: separate `Visa_Early_Careers` board, linked from Visa's student page, with India facets and full descriptions. This board currently includes nonstudent titles; normal experience filters still apply.
- `workday_students`: Walmart's complete India listing pagination, followed by student-title selection and full descriptions only for selected jobs. This fills a gap in the old `Global Tech India` keyword search. Workday's `intern` text search also returned experienced roles because it searches descriptions; keyword hits are not treated as internships.
- Live new-collector check: status `ok`, 3 postings: 2 Visa board roles and Walmart requisition `R-2557935` (Grad Intern - No Work Experience), with descriptions. This is not a count of 3 student-eligible jobs.
- Both use existing company/requisition IDs to avoid duplicate saved rows. Failed requests, missing totals and missing descriptions differ from complete empty searches. Existing saved descriptions are not rewritten by these added feeds.

### Remaining gaps

- Palo Alto's internship button links to [RippleMatch](https://app.ripplematch.com/v2/public/company/palo-alto-networks?tl=298554f5). A generic public endpoint did not prove company filtering or current internship coverage; this route remains manual review only.
- Arcesium has a verified general board but no dedicated student page was found; a student-specific link would help.
- Qualcomm's Eightfold and Expedia's descriptions remain summaries. They cannot establish complete enrollment/eligibility requirements.
- Six program-page requests returned HTTP 403 (Uber, Rubrik, ServiceNow, PayPal, Expedia, Bloomberg). Their pages were found through indexed official sources and their separate listing feeds responded; inaccessible program pages are not described as scraped.
- American Express counts sampled the first India page. Legacy plain-list adapters do not prove completeness merely by returning a list; exact counts can change during pagination.
- Generic graduate full-time jobs are excluded from the student-title checkbox. Industrial trainee and co-op titles are now included. A title match does not prove suitability for a current college student. Normal experience, location, new-job and resume-match filters remain active.
