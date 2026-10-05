// Hand-mirrors the JSON shapes api/main.py returns. Kept deliberately
// explicit rather than generated — if the API changes, this file is the
// single place the frontend needs to follow it.

export interface Job {
  id: string;
  title: string;
  company: string;
  display_company: string;
  location: string;
  url: string;
  source: string;
  category: string;
  skills: string[];
  /** -1 means "unknown" (nothing found in the description), NOT zero years.
   *  0 is a real, meaningful value: explicitly fresher-friendly. */
  experience_years: number;
  first_seen_ms: number;
  first_seen: string;
  /** Last observed in a collector result; does not prove the job is still open. */
  last_seen: string;
  is_remote: boolean;
  is_ncr: boolean;
  is_india: boolean;
  /** Computed server-side from config.EXCLUDE_SENIOR — never re-derive
   *  this in the frontend, see api/data.py's comment for why. */
  is_senior: boolean;
  /** null until a resume is uploaded. */
  match_pct: number | null;
}

export interface JobDetail {
  id: string;
  title: string;
  description: string;
  experience_lines: string[];
  eligibility: {
    minimum_years: number | null;
    education_evidence: string[];
    graduation_evidence: string[];
    mandatory_skill_evidence: string[];
    mandatory_skills: string[];
    missing_mandatory_skills: string[];
    needs_review: boolean;
    note: string;
  };
  skill_match: {
    matched: string[];
    missing: string[];
    /** null when the job lists no recognized skills — distinct from 0,
     *  which means "recognized skills, none of them yours". */
    pct: number | null;
  };
}

export interface Stats {
  visible: number;
  companies: number;
  resume_loaded: boolean;
}

export interface ResumeState {
  loaded: boolean;
  resume_key: string | null;
  word_count: number;
  skills: string[];
}

export interface ResumeUploadResult extends ResumeState {
  auto_skills: string[];
  had_saved_override: boolean;
  scored: number;
}

export interface Filters {
  locationText: string;
  showRemote: boolean;
  showNcr: boolean;
  showIndia: boolean;
  hideHighExperience: boolean;
}
