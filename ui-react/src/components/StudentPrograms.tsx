import { useState } from "react";

// Program links are navigation, not fabricated vacancy records.
const programs = [
  {
    "company": "Google",
    "url": "https://buildyourfuture.withgoogle.com/",
    "note": "India intern/apprentice search already collected."
  },
  {
    "company": "Microsoft",
    "url": "https://careers.microsoft.com/v2/global/en/students",
    "note": "India Intern and Entry searches already collected."
  },
  {
    "company": "Amazon",
    "url": "https://www.amazon.jobs/content/en/career-programs/university",
    "note": "Dedicated India intern and apprentice searches collected."
  },
  {
    "company": "NVIDIA",
    "url": "https://www.nvidia.com/en-us/about-nvidia/careers/university-recruiting/",
    "note": "Existing Workday feed; separate student portal coverage not verified."
  },
  {
    "company": "Apple",
    "url": "https://www.apple.com/careers/us/work-at-apple/students.html",
    "note": "Existing India jobs feed; this program page is global."
  },
  {
    "company": "Meta",
    "url": "https://www.metacareers.com/jobsearch/?offices[0]=Mumbai%2C%20India&offices[1]=Gurgaon%2C%20India&offices[2]=Bangalore%2C%20India&offices[3]=Hyderabad%2C%20India&offices[4]=New%20Delhi%2C%20India&roles[0]=Internship",
    "note": "India internship search; existing all-role India feed includes these offices. No internships returned when checked."
  },
  {
    "company": "Goldman Sachs",
    "url": "https://www.goldmansachs.com/careers/students/programs-and-internships/india/summer-analyst-program",
    "note": "India 2027 Summer Analyst page currently specifies graduation in 2028; check campus applications manually."
  },
  {
    "company": "JPMorgan Chase",
    "url": "https://www.jpmorganchase.com/careers/explore-opportunities/students-and-graduates",
    "note": "India Oracle feed connected; separate programs require manual checking."
  },
  {
    "company": "Morgan Stanley",
    "url": "https://www.morganstanley.com/careers/career-opportunities-search?opportunity=sg",
    "note": "Separate student feed connected with descriptions; only India programs are saved."
  },
  {
    "company": "Salesforce",
    "url": "https://www.salesforce.com/company/careers/university/",
    "note": "Futureforce program page; existing Workday feed connected."
  },
  {
    "company": "Adobe",
    "url": "https://careers.adobe.com/us/en/university",
    "note": "India rows observed: 78; student titles: 0. Existing listing feed remains connected. Global program page; check India availability."
  },
  {
    "company": "Intuit",
    "url": "https://www.intuit.com/careers/programs/internships/",
    "note": "India rows observed: 27; student titles: 0. Existing listing feed remains connected. Global program page; check India availability."
  },
  {
    "company": "Stripe",
    "url": "https://stripe.com/in/careers/emerging-talent",
    "note": "India rows observed: 43; student titles: 2. Existing listing feed remains connected. Global program page; check India availability."
  },
  {
    "company": "Databricks",
    "url": "https://www.databricks.com/company/careers/university-recruiting",
    "note": "India rows observed: 92; student titles: 0. Existing listing feed remains connected. Global program page; check India availability."
  },
  {
    "company": "Atlassian",
    "url": "https://www.atlassian.com/company/careers/earlycareers",
    "note": "India rows observed: 56; student titles: 0. Existing listing feed remains connected. Global program page; check India availability."
  },
  {
    "company": "Uber",
    "url": "https://jobs.uber.com/en/teams/emerging-talent/?id=160",
    "note": "India rows observed: 20; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. Direct program-page request returned 403; the listing feed responded."
  },
  {
    "company": "Rubrik",
    "url": "https://www.rubrik.com/company/careers",
    "note": "India rows observed: 32; student titles: 3. Early Career section on official careers page; internship listings come from the existing Greenhouse board. Direct program-page request returned 403; the listing feed responded."
  },
  {
    "company": "Snowflake",
    "url": "https://careers.snowflake.com/university",
    "note": "India rows observed: 11; student titles: 0. Existing listing feed remains connected. Global program page; check India availability."
  },
  {
    "company": "ServiceNow",
    "url": "https://careers.servicenow.com/early-careers/",
    "note": "India rows observed: 77; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. Direct program-page request returned 403; the listing feed responded."
  },
  {
    "company": "Palo Alto Networks",
    "url": "https://jobs.paloaltonetworks.com/en/early-in-career",
    "note": "India rows observed: 161; student titles: 0. Existing India Workday feed responds. Internship button uses RippleMatch; that separate route remains manual review only."
  },
  {
    "company": "PayPal",
    "url": "https://careers.pypl.com/university-hiring/University-Overview/default.aspx",
    "note": "India rows observed: 11; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. Direct program-page request returned 403; the listing feed responded."
  },
  {
    "company": "Visa",
    "url": "https://corporate.visa.com/en/careers/early-careers.html",
    "note": "India rows observed: 2; student titles: 0. Added separate Visa Early Careers Workday board. Its 2 India roles currently have nonstudent titles; check eligibility."
  },
  {
    "company": "Mastercard",
    "url": "https://careers.mastercard.com/us/en/early-careers/internships",
    "note": "India rows observed: 211; student titles: 0. Existing listing feed remains connected. Global program page; check India availability."
  },
  {
    "company": "American Express",
    "url": "https://www.americanexpress.com/en-us/careers/student-programs/global-students-page.html",
    "note": "India rows observed: 25; student titles: 3. Only the first India page was recounted. Apprenticeships may require completed graduation; check the description."
  },
  {
    "company": "BlackRock",
    "url": "https://careers.blackrock.com/students-and-graduates-apac",
    "note": "India rows observed: 42; student titles: 0. APAC campus links use the same careers site; linked regional programs did not list India."
  },
  {
    "company": "Arcesium",
    "url": "https://www.arcesium.com/careers",
    "note": "India rows observed: 25; student titles: 0. General careers fallback; dedicated student page not found. Existing Greenhouse board remains connected."
  },
  {
    "company": "Qualcomm",
    "url": "https://careers.qualcomm.com/careers?domain=qualcomm.com&start=0&location=india&sort_by=distance&filter_include_remote=0&filter_include_relocation=0&filter_seniority=Intern",
    "note": "Dedicated India Intern search connected: 2 internships for 2027 (hardware and software), with full descriptions. Check enrollment and graduation requirements."
  },
  {
    "company": "Walmart Global Tech",
    "url": "https://careers.walmart.com/us/en/home/careers-areas/students",
    "note": "India rows observed: 229; student titles: 1. Added complete India listing scan and student-title selection outside the narrow Global Tech query. Grad Intern - No Work Experience found. Program hub is US-focused."
  },
  {
    "company": "Expedia Group",
    "url": "https://careers.expediagroup.com/emerging-talent-and-careers/",
    "note": "India rows observed: 21; student titles: 0. Existing descriptions are team summaries; review the full employer description before applying. Direct program-page request returned 403; the listing feed responded."
  },
  {
    "company": "Bloomberg",
    "url": "https://www.bloomberg.com/company/early-careers/",
    "note": "India rows observed: 7; student titles: 0. Existing listing feed remains connected. Global program page; check India availability. Direct program-page request returned 403; the listing feed responded."
  }
];

export default function StudentPrograms() {
  const [query, setQuery] = useState("");
  const visible = programs.filter(p => p.company.toLowerCase().includes(query.trim().toLowerCase()));
  return <details className="rounded-md border border-gray-200 p-4 mb-4 text-sm">
    <summary className="cursor-pointer font-semibold">Student programs — {programs.length} companies</summary>
    <p className="text-gray-500 my-3">Official program links, checked 5 October 2026. Counts describe source postings observed at that check, not eligibility; some checks sampled a page. Some pages are global: review India locations, enrollment and graduation year. A program page does not mean applications are open.</p>
    <input className="w-full border border-gray-300 rounded px-3 py-2 mb-3" aria-label="Find a student program company" placeholder="Find a company…" value={query} onChange={e => setQuery(e.target.value)} />
    <ul className="grid sm:grid-cols-2 gap-3">{visible.map(p => <li className="rounded border border-gray-100 p-3" key={p.company}>
      <a className="underline font-medium" href={p.url} target="_blank" rel="noreferrer">{p.company}</a>
      <span className="block text-gray-500 mt-1">{p.note}</span>
    </li>)}</ul>
    {visible.length === 0 && <p className="text-gray-500">No matching company.</p>}
  </details>;
}
