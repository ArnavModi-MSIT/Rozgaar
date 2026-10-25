type ExperienceEvidence = {
  experience_years: number;
  preferred_experience_years?: number;
};

export function exceedsExperienceLimit(job: ExperienceEvidence, maximumYears: number): boolean {
  // Unknown (-1) is retained. Required and preferred lower bounds both count.
  return Math.max(job.experience_years, job.preferred_experience_years ?? -1) > maximumYears;
}
