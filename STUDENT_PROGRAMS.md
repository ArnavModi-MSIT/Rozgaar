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
| Morgan Stanley | [Official page](https://www.morganstanley.com/people-opportunities/students-graduates/) | India Eightfold feed connected; separate student portal requires manual checking. |
| Salesforce | [Official page](https://www.salesforce.com/company/careers/university/) | Futureforce program page; existing Workday feed connected. |

Amazon: dedicated India `intern` search returned 3 postings, `apprentice` returned 0 at verification. Both searches paginate and deduplicate through the existing Amazon adapter; zero now does not disable a search. Other existing feeds were not exhaustively recollected during this change.

The student checkbox matches titles only (intern, internship, apprentice, apprenticeship, student, summer analyst, summer associate). It applies across all companies and keeps normal location, experience, resume-match and new-job filters. It can miss student eligibility mentioned only in descriptions. It does not treat all graduate full-time roles as current-student opportunities. Review enrollment, graduation year and required experience in the description.

Goldman Sachs and Morgan Stanley have separate student application routes: general collector coverage does not prove those routes are ingested. Their official pages remain directly accessible for manual review. Meta's supplied India internship search was checked through its public GraphQL endpoint: 0 internship rows versus 25 rows in the general India search. The existing unfiltered collector remains active and includes internship roles when published; no extra duplicate collector is needed. Global program pages do not establish India availability or an open application window.
