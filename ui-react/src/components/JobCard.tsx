import { useState } from "react";
import { api } from "../api";
import type { Job, JobDetail } from "../types";

interface Props {
  job: Job;
  resumeSkills: Set<string>;
  resumeLoaded: boolean;
  autoRemove: boolean;
  onDismiss: (id: string) => void;
}

function experienceLabel(years: number): string | null {
  // -1 is the project-wide "couldn't determine" sentinel — deliberately
  // shown as nothing rather than "0 years", which would be a real claim.
  if (years < 0) return "Experience requirement unknown — review description";
  if (years === 0) return "Fresher-friendly (0 years stated)";
  return `${years}+ year(s) required`;
}

export default function JobCard({
  job,
  resumeSkills,
  resumeLoaded,
  autoRemove,
  onDismiss,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<JobDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const matched = job.skills.filter((s) => resumeSkills.has(s));
  const missing = job.skills.filter((s) => !resumeSkills.has(s));
  const skillPct =
    job.skills.length > 0
      ? Math.round((100 * matched.length) / job.skills.length)
      : null;

  async function toggleDetail() {
    const next = !expanded;
    setExpanded(next);
    if (next && !detail) {
      try {
        setDetail(await api.jobDetail(job.id));
      } catch (e) {
        setDetailError(e instanceof Error ? e.message : "couldn't load details");
      }
    }
  }

  // Opening a link does not imply an application. Only the optional
  // auto-remove setting dismisses it; the anchor still opens a new tab.
  function handleOpen() {
    if (autoRemove) onDismiss(job.id);
  }

  const expLabel = experienceLabel(job.experience_years);

  return (
    <article className="rounded-lg border border-gray-200 bg-white px-4 py-3.5 hover:border-gray-300 transition-colors">
      <div className="flex gap-4">
        <div className="min-w-0 flex-1">
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleOpen}
            className="text-lg font-semibold text-amber-800 hover:underline break-words"
          >
            {job.title}
          </a>

          <p className="text-sm text-gray-700 mt-0.5">
            <span className="font-medium">{job.display_company}</span>
            {job.location && <> · {job.location}</>}
            <> · via {job.source}</>
            {job.category && <> · {job.category}</>}
          </p>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-gray-500">
            {expLabel && <span>{expLabel}</span>}
            {job.is_remote && (
              <span className="rounded bg-sky-50 text-sky-700 px-1.5 py-0.5">Remote</span>
            )}
            {job.is_ncr && (
              <span className="rounded bg-amber-50 text-amber-800 px-1.5 py-0.5">NCR</span>
            )}
            <span title="Last observed by a collector; verify the posting is still open before applying">Seen {job.last_seen}</span>
          </div>

          {resumeLoaded && skillPct !== null && (
            <p className="text-xs text-gray-600 mt-1.5">
              Skills {matched.length}/{job.skills.length} ({skillPct}%)
              {matched.length > 0 && (
                <span className="text-gray-500"> · have: {matched.join(", ")}</span>
              )}
              {missing.length > 0 && (
                <span className="text-gray-400"> · missing: {missing.join(", ")}</span>
              )}
            </p>
          )}

          <div className="flex items-center gap-3 mt-2.5">
            <button
              onClick={toggleDetail}
              className="text-xs text-gray-600 hover:text-gray-900 underline"
            >
              {expanded ? "Hide details" : "Details"}
            </button>
            <button
              onClick={() => onDismiss(job.id)}
              className="text-xs text-gray-500 hover:text-red-700"
            >
              Remove
            </button>
          </div>

          {expanded && (
            <div className="mt-3 border-t border-gray-100 pt-3">
              {detailError && <p className="text-xs text-red-600">{detailError}</p>}
              {!detail && !detailError && (
                <p className="text-xs text-gray-400">Loading…</p>
              )}
              {detail && (
                <>
                  <h3 className="text-sm font-semibold mb-2">Eligibility evidence</h3>
                  <p className="text-xs text-gray-500 mb-2">{detail.eligibility.note}</p>
                  {([ ["Education", detail.eligibility.education_evidence], ["Graduation year", detail.eligibility.graduation_evidence], ["Mandatory skills", detail.eligibility.mandatory_skill_evidence] ] as [string, string[]][]).map(([label, lines]) => (
                    <div key={label} className="text-xs mb-2"><strong>{label}</strong>{lines.length ? <ul>{lines.map((line, i) => <li key={i}>{line}</li>)}</ul> : <p className="text-gray-500">Not identified — verify the posting.</p>}</div>
                  ))}
                  {resumeLoaded && detail.eligibility.missing_mandatory_skills.length > 0 && <p className="text-xs text-amber-800 mb-2">Missing recognized mandatory skills: {detail.eligibility.missing_mandatory_skills.join(", ")}</p>}
                  {detail.experience_lines.length > 0 ? (
                    <ul className="text-xs text-gray-700 space-y-1 mb-2">
                      {detail.experience_lines.slice(0, 12).map((line, i) => (
                        <li key={i} className="leading-relaxed">
                          • {line}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-gray-400 mb-2">
                      No numbers or “experience” mentions found.
                    </p>
                  )}
                  {detail.description && (
                    <details>
                      <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-900">
                        Full description
                      </summary>
                      <p className="text-xs text-gray-700 whitespace-pre-wrap mt-2 leading-relaxed">
                        {detail.description}
                      </p>
                    </details>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {job.match_pct !== null && (
          <div className="shrink-0 text-right" title="Ranking score based on resume text and skills. It is not an eligibility or hiring probability.">
            <div className="text-2xl font-semibold tabular-nums">
              {job.match_pct.toFixed(0)}
            </div>
            <div className="text-[10px] uppercase tracking-wide text-gray-400">
              Relevance score
            </div>
          </div>
        )}
      </div>
    </article>
  );
}
