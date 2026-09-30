import { useRef } from "react";
import type { Filters, ResumeState } from "../types";

interface Props {
  filters: Filters;
  onFilterChange: (patch: Partial<Filters>) => void;
  resume: ResumeState;
  onUpload: (file: File) => void;
  onClearResume: () => void;
  resumeBusy: boolean;
  resumeError: string | null;
  autoRemove: boolean;
  onAutoRemoveChange: (v: boolean) => void;
  counts: { belowThreshold: number; senior: number; highExperience: number };
  onBulkDismiss: (which: "match" | "senior" | "experience") => void;
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
  filters,
  onFilterChange,
  resume,
  onUpload,
  onClearResume,
  resumeBusy,
  resumeError,
  autoRemove,
  onAutoRemoveChange,
  counts,
  onBulkDismiss,
  minMatch,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <aside className="w-72 shrink-0 border-r border-gray-200 bg-white h-screen overflow-y-auto p-5 space-y-6">
      <div>
        <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-500 mb-2">
          Resume
        </h2>
        {resume.loaded ? (
          <div className="rounded-md bg-green-50 border border-green-200 px-3 py-2">
            <p className="text-sm text-green-800">
              Loaded — {resume.word_count} words
            </p>
            <p className="text-xs text-green-700 mt-0.5">
              {resume.skills.length} skills detected
            </p>
            <button
              onClick={onClearResume}
              className="mt-2 text-xs text-gray-600 underline hover:text-gray-900"
            >
              Remove resume
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
                if (f) onUpload(f);
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
            <p className="text-xs text-gray-500 mt-1.5">
              Ranks every job by how well it matches.
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
          <Check
            label="Hide senior/lead/manager titles"
            checked={filters.hideSenior}
            onChange={(v) => onFilterChange({ hideSenior: v })}
          />
          <Check
            label="Hide jobs needing 1+ years"
            hint="Jobs with an unknown requirement are kept"
            checked={filters.hideHighExperience}
            onChange={(v) => onFilterChange({ hideHighExperience: v })}
          />
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-500 mb-2">
          Behaviour
        </h2>
        <Check
          label="Remove a job when I open it"
          hint="Opening the link marks it applied / not interested"
          checked={autoRemove}
          onChange={onAutoRemoveChange}
        />
      </div>

      <div>
        <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-500 mb-2">
          Bulk remove
        </h2>
        <div className="space-y-1.5">
          {resume.loaded && counts.belowThreshold > 0 && (
            <button
              onClick={() => onBulkDismiss("match")}
              className="w-full text-left rounded-md border border-gray-200 px-2.5 py-1.5 text-xs hover:bg-gray-50"
            >
              Remove {counts.belowThreshold} below {minMatch}% match
            </button>
          )}
          {counts.senior > 0 && (
            <button
              onClick={() => onBulkDismiss("senior")}
              className="w-full text-left rounded-md border border-gray-200 px-2.5 py-1.5 text-xs hover:bg-gray-50"
            >
              Remove {counts.senior} senior/lead/manager
            </button>
          )}
          {counts.highExperience > 0 && (
            <button
              onClick={() => onBulkDismiss("experience")}
              className="w-full text-left rounded-md border border-gray-200 px-2.5 py-1.5 text-xs hover:bg-gray-50"
            >
              Remove {counts.highExperience} needing 1+ years
            </button>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Permanent — same as removing each one individually.
        </p>
      </div>
    </aside>
  );
}
