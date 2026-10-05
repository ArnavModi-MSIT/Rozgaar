// Program pages are navigation links, not scraped vacancy records.
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
  }
];

export default function StudentPrograms() {
  return <details className="rounded-md border border-gray-200 p-4 mb-4 text-sm">
    <summary className="cursor-pointer font-semibold">Student programs — top 10 companies</summary>
    <p className="text-gray-500 my-3">Official program links. Some pages are global; check India locations, enrollment and graduation year in each application. A program page does not mean applications are open.</p>
    <ul className="space-y-3">{programs.map(p => <li key={p.company}>
      {p.url ? <a className="underline" href={p.url} target="_blank" rel="noreferrer">{p.company}</a> : <strong>{p.company}</strong>}
      <span className="block text-gray-500">{p.note}</span>
    </li>)}</ul>
  </details>;
}
