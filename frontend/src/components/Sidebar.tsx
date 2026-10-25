import { useEffect, useRef, useState } from "react";
import type { Filters, ResumeState } from "../types";

interface Props {
  exportOnly?: boolean;
  filters: Filters;
  onFilterChange: (patch: Partial<Filters>) => void;
  resume: ResumeState;
  onUpload: (file: File, saveForLater: boolean) => void;
  onClearResume: () => void;
  onUsePreviousResume: () => void;
  onDeleteSavedResume: () => void;
  onUpdateResumeSkills: (skills: string[]) => Promise<void>;
  resumeBusy: boolean;
  resumeError: string | null;
  autoRemove: boolean;
  onAutoRemoveChange: (v: boolean) => void;
  counts: { belowThreshold: number; highExperience: number };
  onBulkDismiss: (which: "match" | "experience") => void;
  minMatch: number;
}

function Check({
  label,
  checked,
  onChange,
  hint,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  hint?: string;
}) {
  return (
    <label className="flex items-start gap-2 py-1 cursor-pointer select-none">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 accent-amber-700 cursor-pointer"
      />
      <span className="text-sm leading-snug">
        {label}
        {hint && <span className="block text-xs text-gray-500">{hint}</span>}
      </span>
    </label>
  );
}

export default function Sidebar({
  exportOnly = false,
  filters,
  onFilterChange,
  resume,
  onUpload,
  onClearResume,
  onUsePreviousResume,
  onDeleteSavedResume,
  onUpdateResumeSkills,
  resumeBusy,
  resumeError,
  autoRemove,
  onAutoRemoveChange,
  counts,
  onBulkDismiss,
  minMatch,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [draftSkills, setDraftSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState("");
  const [saveForLater, setSaveForLater] = useState(true);
  useEffect(() => setDraftSkills(resume.skills), [resume.skills]);

  const addSkill = () => {
    const skill = newSkill.trim().toLowerCase();
    if (skill && !draftSkills.includes(skill)) {
      setDraftSkills((current) => [...current, skill].sort());
    }
    setNewSkill("");
  };

  return (
    <aside className="w-72 shrink-0 border-r border-gray-200 bg-white h-screen overflow-y-auto p-5 space-y-6">
      <div>
        <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-500 mb-2">
          Resume
        </h2>
        {resume.saved_resume && (
          <div className="mb-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
            <p className="text-xs text-gray-600">Saved on this PC</p>
            <p className="text-sm break-all mt-0.5">{resume.saved_resume.filename}</p>
            {(!resume.loaded || resume.resume_key !== resume.saved_resume.resume_key) && (
              <button
                type="button"
                disabled={resumeBusy}
                onClick={onUsePreviousResume}
                className="w-full mt-2 rounded-md bg-amber-700 px-3 py-2 text-sm text-white hover:bg-amber-800 disabled:opacity-60"
              >
                {resumeBusy ? "Loading…" : "Use previous resume"}
              </button>
            )}
            <button
              type="button"
              disabled={resumeBusy}
              onClick={onDeleteSavedResume}
              className="mt-2 text-xs text-gray-600 underline hover:text-gray-900 disabled:opacity-40"
            >
              Delete saved copy
            </button>
          </div>
        )}
        {resume.loaded ? (
          <div className="rounded-md bg-green-50 border border-green-200 px-3 py-2">
            <p className="text-sm text-green-800">
              Loaded — {resume.word_count} words
            </p>
            {resume.filename && <p className="mt-0.5 text-xs text-green-700 break-all">{resume.filename}</p>}
            <p className="text-xs text-green-700 mt-0.5">
              {resume.skills.length} resume skills
            </p>
            <div className="mt-3 border-t border-green-200 pt-2">
              <p className="text-xs font-medium text-green-900 mb-1">Correct extracted skills</p>
              <div className="flex flex-wrap gap-1">
                {draftSkills.map((skill) => (
                  <button
                    key={skill}
                    type="button"
                    disabled={resumeBusy}
                    onClick={() => setDraftSkills((current) => current.filter((s) => s !== skill))}
                    title={`Remove ${skill}`}
                    className="rounded bg-white border border-green-200 px-1.5 py-0.5 text-xs hover:bg-red-50"
                  >
                    {skill} ×
                  </button>
                ))}
              </div>
              <form onSubmit={(e) => { e.preventDefault(); addSkill(); }} className="flex gap-1 mt-2">
                <input
                  disabled={resumeBusy}
                  value={newSkill}
                  onChange={(e) => setNewSkill(e.target.value)}
                  placeholder="Add skill"
                  aria-label="Add resume skill"
                  className="min-w-0 w-full rounded border border-green-200 px-2 py-1 text-xs"
                />
                <button type="submit" disabled={resumeBusy} className="text-xs underline disabled:opacity-40">Add</button>
              </form>
              <button
                type="button"
                disabled={resumeBusy || draftSkills.join("|") === resume.skills.join("|")}
                onClick={() => { void onUpdateResumeSkills(draftSkills).catch(() => {}); }}
                className="mt-2 text-xs font-medium text-green-900 underline disabled:opacity-40"
              >
                {resumeBusy ? "Rescoring…" : "Save skills and rescore"}
              </button>
            </div>
            <button
              onClick={onClearResume}
              disabled={resumeBusy}
              className="mt-2 text-xs text-gray-600 underline hover:text-gray-900 disabled:opacity-40"
            >
              Unload resume
            </button>
          </div>
        ) : (
          <>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onUpload(f, saveForLater);
                e.target.value = "";
              }}
            />
            <button
              disabled={resumeBusy}
              onClick={() => fileRef.current?.click()}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm hover:bg-gray-50 disabled:opacity-60"
            >
              {resumeBusy ? "Scoring jobs…" : "Upload resume (pdf, docx, txt)"}
            </button>
            <label className="flex items-center gap-2 mt-2 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={saveForLater}
                disabled={resumeBusy}
                onChange={(e) => setSaveForLater(e.target.checked)}
                className="accent-amber-700"
              />
              Save for next time on this PC
            </label>
            <p className="text-xs text-gray-500 mt-1.5">
              Reuse saved resume text and embeddings after restarting. Delete the saved copy anytime.
            </p>
          </>
        )}
        {resumeError && (
          <p className="text-xs text-red-600 mt-2">{resumeError}</p>
        )}
      </div>

      <div>
        <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-500 mb-2">
          Filters
        </h2>

        <label className="block text-xs text-gray-600 mb-1">
          City / State contains
        </label>
        <input
          type="text"
          value={filters.locationText}
          placeholder="e.g. Delhi, Gurugram, Noida"
          onChange={(e) => onFilterChange({ locationText: e.target.value })}
          className="w-full rounded-md border border-gray-300 px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-600/30"
        />

        <p className="text-xs text-gray-500 mt-3 mb-1">
          Location type — ticking more than one widens the results
        </p>
        <Check
          label="Remote"
          checked={filters.showRemote}
          onChange={(v) => onFilterChange({ showRemote: v })}
        />
        <Check
          label="Delhi NCR"
          checked={filters.showNcr}
          onChange={(v) => onFilterChange({ showNcr: v })}
        />
        <Check
          label="India"
          hint="Anywhere in India, not just NCR"
          checked={filters.showIndia}
          onChange={(v) => onFilterChange({ showIndia: v })}
        />

        <div className="mt-3 pt-3 border-t border-gray-100">
          <label htmlFor="max-experience" className="block text-xs font-medium text-gray-600 mb-1">
            Maximum experience
          </label>
          <select
            id="max-experience"
            value={filters.maxExperienceYears}
            onChange={(e) => onFilterChange({ maxExperienceYears: Number(e.target.value) })}
            className="w-full rounded-md border border-gray-300 px-2.5 py-1.5 text-sm mb-2"
          >
            {[0, 1, 2, 3, 5].map((years) => (
              <option key={years} value={years}>{years === 0 ? "Fresher / 0 years" : `Up to ${years} year${years === 1 ? "" : "s"}`}</option>
            ))}
          </select>
          <Check
            label={`Hide roles asking for more than ${filters.maxExperienceYears} year${filters.maxExperienceYears === 1 ? "" : "s"}`}
            hint="Checks required or preferred minimum experience. Unknown requirements are kept. Hiding does not remove jobs."
            checked={filters.hideHighExperience}
            onChange={(v) => onFilterChange({ hideHighExperience: v })}
          />
        </div>
      </div>

      {!exportOnly && <div>
        <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-500 mb-2">
          Behaviour
        </h2>
        <Check
          label="Remove a job when I open it"
          hint="Optional: opening the link removes it from discovery. Recover it in Removed. Default is off."
          checked={autoRemove}
          onChange={onAutoRemoveChange}
        />
      </div>}

      <div>
        <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-500 mb-2">
          Bulk remove
        </h2>
        <div className="space-y-1.5">
          {!exportOnly && resume.loaded && counts.belowThreshold > 0 && (
            <button
              onClick={() => onBulkDismiss("match")}
              className="w-full text-left rounded-md border border-gray-200 px-2.5 py-1.5 text-xs hover:bg-gray-50"
            >
              Remove {counts.belowThreshold} below {minMatch}% match
            </button>
          )}
            <button
              onClick={() => onBulkDismiss("experience")}
              disabled={counts.highExperience === 0}
              className="w-full text-left rounded-md border border-gray-200 px-2.5 py-1.5 text-xs hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Remove {counts.highExperience} asking for more than {filters.maxExperienceYears} year{filters.maxExperienceYears === 1 ? "" : "s"}
            </button>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Applies to all loaded career jobs, including those hidden by filters. Unknown requirements are kept. Use Undo to restore the removed jobs.
        </p>
      </div>
    </aside>
  );
}
