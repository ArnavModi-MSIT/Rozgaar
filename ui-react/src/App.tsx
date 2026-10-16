import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import JobCard from "./components/JobCard";
import Sidebar from "./components/Sidebar";
import StudentPrograms from "./components/StudentPrograms";
import type { Filters, Job, ResumeState } from "./types";

// Once a resume is loaded, hide jobs scoring below this threshold.
const MIN_MATCH = 20;
// Keep ranges starting at zero and unknowns; hide lower bounds of 1+ years.
const EXPERIENCE_THRESHOLD = 1;
const PAGE_SIZE = 40;

const DEFAULT_FILTERS: Filters = {
  locationText: "",
  showRemote: false,
  showNcr: false,
  showIndia: false,
  hideHighExperience: true,
};

export default function App() {
  const [visitBaseline, setVisitBaseline] = useState(() => {
    try { const value = Number(localStorage.getItem("job-intel-last-visit")); return Number.isFinite(value) && value > 0 ? value : 0; } catch { return 0; }
  });
  const [onlyNew, setOnlyNew] = useState(false);
  const [studentOnly, setStudentOnly] = useState(false);
  const [visitRecorded, setVisitRecorded] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [resume, setResume] = useState<ResumeState>({
    loaded: false,
    resume_key: null,
    word_count: 0,
    skills: [],
    filename: null,
    saved_resume: null,
  });
  const [resumeBusy, setResumeBusy] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [autoRemove, setAutoRemove] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const refresh = useCallback(async () => {
    try {
      const [jobList, resumeState] = await Promise.all([api.jobs(), api.resume()]);
      setJobs(jobList);
      setResume(resumeState);
      setLoadError(null);
    } catch (e) {
      setLoadError(
        e instanceof Error
          ? `${e.message} — is the backend running on port 8000?`
          : "failed to load",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!loading && !loadError && !visitRecorded) {
      try { localStorage.setItem("job-intel-last-visit", String(Date.now())); } catch { /* Storage may be disabled. */ }
      setVisitRecorded(true);
    }
  }, [loading, loadError, visitRecorded]);
  const newCount = jobs.filter(j => j.first_seen_ms > visitBaseline).length;

  const resumeSkills = useMemo(() => new Set(resume.skills), [resume.skills]);

  // All filtering happens in memory. With a few thousand jobs this is well
  // under a frame, which is exactly why the rewrite was worth doing:
  // ticking a box no longer round-trips to the server.
  const filtered = useMemo(() => {
    const text = filters.locationText.trim().toLowerCase();
    const anyLocationType =
      filters.showRemote || filters.showNcr || filters.showIndia;

    let out = jobs.filter((j) => {
      if (onlyNew && j.first_seen_ms <= visitBaseline) return false;
      // Discovery by title only; enrollment eligibility must be checked in the JD.
      if (studentOnly && !/\b(intern(?:ship)?|apprentice(?:ship)?|student|summer analyst|summer associate|industrial trainee|co[ -]?op)\b/i.test(j.title.replace(/_/g, " "))) return false;
      if (text && !j.location.toLowerCase().includes(text)) return false;

      // Remote / NCR / India are OR'd together — ticking more than one
      // widens the result.
      if (anyLocationType) {
        const hit =
          (filters.showRemote && j.is_remote) ||
          (filters.showNcr && j.is_ncr) ||
          (filters.showIndia && j.is_india);
        if (!hit) return false;
      }

      if (
        filters.hideHighExperience &&
        Math.max(j.experience_years, j.preferred_experience_years ?? -1) >= EXPERIENCE_THRESHOLD
      ) {
        // Unknown (-1) is deliberately kept — "couldn't determine" is not
        // evidence a job needs too much experience.
        return false;
      }
      if (resume.loaded && j.match_pct !== null && j.match_pct < MIN_MATCH) {
        return false;
      }
      return true;
    });

    out = resume.loaded
      ? out.sort((a, b) => (b.match_pct ?? 0) - (a.match_pct ?? 0))
      : out.sort((a, b) => b.first_seen.localeCompare(a.first_seen));
    return out;
  }, [jobs, filters, resume.loaded, onlyNew, visitBaseline, studentOnly]);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [filters, resume.loaded, onlyNew, visitBaseline, studentOnly]);

  const bulkCounts = useMemo(
    () => ({
      belowThreshold: jobs.filter(
        (j) => j.match_pct !== null && j.match_pct < MIN_MATCH,
      ).length,
      highExperience: jobs.filter(
        (j) => Math.max(j.experience_years, j.preferred_experience_years ?? -1) >= EXPERIENCE_THRESHOLD,
      ).length,
    }),
    [jobs],
  );

  // Optimistic: the card disappears immediately and the POST settles in the
  // background. On failure we reload rather than guess at rolling back.
  const dismiss = useCallback(async (id: string) => {
    setJobs((prev) => prev.filter((j) => j.id !== id));
    try {
      await api.dismiss(id);
    } catch {
      void refresh();
    }
  }, [refresh]);

  const bulkDismiss = useCallback(
    async (which: "match" | "experience") => {
      const targets = jobs.filter((j) => {
        if (which === "match") return j.match_pct !== null && j.match_pct < MIN_MATCH;
        return Math.max(j.experience_years, j.preferred_experience_years ?? -1) >= EXPERIENCE_THRESHOLD;
      });
      const ids = new Set(targets.map((j) => j.id));
      if (ids.size === 0) return;
      setJobs((prev) => prev.filter((j) => !ids.has(j.id)));
      try {
        await api.dismissBulk([...ids]);
      } catch {
        void refresh();
      }
    },
    [jobs, refresh],
  );

  const uploadResume = useCallback(
    async (file: File, saveForLater: boolean) => {
      setResumeBusy(true);
      setResumeError(null);
      try {
        const result = await api.uploadResume(file, saveForLater);
        await refresh();
        if (result.save_warning) setResumeError(result.save_warning);
      } catch (e) {
        setResumeError(e instanceof Error ? e.message : "upload failed");
      } finally {
        setResumeBusy(false);
      }
    },
    [refresh],
  );

  const usePreviousResume = useCallback(async () => {
    if (resumeBusy) return;
    setResumeBusy(true);
    setResumeError(null);
    try {
      const result = await api.usePreviousResume();
      await refresh();
      if (result.save_warning) setResumeError(result.save_warning);
    } catch (e) {
      setResumeError(e instanceof Error ? e.message : "couldn't load the saved resume");
    } finally {
      setResumeBusy(false);
    }
  }, [refresh, resumeBusy]);

  const deleteSavedResume = useCallback(async () => {
    if (resumeBusy) return;
    setResumeBusy(true);
    setResumeError(null);
    try {
      await api.deleteSavedResume();
      await refresh();
    } catch (e) {
      setResumeError(e instanceof Error ? e.message : "couldn't delete the saved copy");
    } finally {
      setResumeBusy(false);
    }
  }, [refresh, resumeBusy]);

  const clearResume = useCallback(async () => {
    if (resumeBusy) return;
    setResumeBusy(true);
    setResumeError(null);
    try {
      await api.clearResume();
      await refresh();
    } catch (e) {
      setResumeError(e instanceof Error ? e.message : "couldn't remove resume");
    } finally {
      setResumeBusy(false);
    }
  }, [refresh, resumeBusy]);

  const updateResumeSkills = useCallback(async (skills: string[]) => {
    setResumeBusy(true);
    setResumeError(null);
    try {
      await api.updateResumeSkills(skills);
      await refresh();
    } catch (e) {
      setResumeError(e instanceof Error ? e.message : "couldn't save skills");
      throw e;
    } finally {
      setResumeBusy(false);
    }
  }, [refresh]);

  const companies = useMemo(
    () => new Set(filtered.map((j) => j.company)).size,
    [filtered],
  );

  return (
    <div className="flex">
      <Sidebar
        filters={filters}
        onFilterChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
        resume={resume}
        onUpload={uploadResume}
        onClearResume={clearResume}
        onUsePreviousResume={usePreviousResume}
        onDeleteSavedResume={deleteSavedResume}
        onUpdateResumeSkills={updateResumeSkills}
        resumeBusy={resumeBusy}
        resumeError={resumeError}
        autoRemove={autoRemove}
        onAutoRemoveChange={setAutoRemove}
        counts={bulkCounts}
        onBulkDismiss={bulkDismiss}
        minMatch={MIN_MATCH}
      />

      <main className="flex-1 h-screen overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <h1 className="text-2xl font-semibold mb-4">Job Intel</h1>
          <StudentPrograms />

          <div className="flex gap-8 border-b border-gray-200 pb-4 mb-5">
            <div>
              <div className="text-2xl font-semibold tabular-nums">
                {filtered.length.toLocaleString()}
              </div>
              <div className="text-xs uppercase tracking-wide text-gray-500">
                Matching jobs
              </div>
            </div>
            <div>
              <div className="text-2xl font-semibold tabular-nums">
                {companies.toLocaleString()}
              </div>
              <div className="text-xs uppercase tracking-wide text-gray-500">
                Companies
              </div>
            </div>
            <div>
              <div className="text-2xl font-semibold tabular-nums text-gray-400">
                {jobs.length.toLocaleString()}
              </div>
              <div className="text-xs uppercase tracking-wide text-gray-500">
                Total in DB
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 mb-4 text-sm">
            <label title="Matches student-related job titles; check the description for eligibility."><input type="checkbox" checked={studentOnly} onChange={e => setStudentOnly(e.target.checked)} /> Intern / apprentice / student titles</label>
            <label><input type="checkbox" checked={onlyNew} onChange={e => setOnlyNew(e.target.checked)} /> New since last visit ({newCount})</label>
            <button disabled={loading || !!loadError} className="underline disabled:opacity-50" onClick={() => { const now = Date.now(); setVisitBaseline(now); try { localStorage.setItem("job-intel-last-visit", String(now)); } catch { /* Optional storage. */ } }}>Mark current jobs reviewed</button>
            <button className="underline" onClick={() => void refresh()}>Refresh jobs</button>
            {visitBaseline === 0 && <span className="text-gray-500">First visit: all saved jobs count as new.</span>}
          </div>
          {loading && <p className="text-sm text-gray-500">Loading jobs…</p>}
          {loadError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {loadError}
            </div>
          )}

          {!loading && !loadError && !resume.loaded && (
            <div className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-800 mb-4">
              Upload a resume or use your previous resume in the sidebar to rank jobs.
            </div>
          )}

          {!loading && !loadError && filtered.length === 0 && (
            <p className="text-sm text-gray-500">No jobs match your current filters.</p>
          )}

          <div className="space-y-3">
            {filtered.slice(0, visibleCount).map((job) => (
              <JobCard
                key={job.id}
                job={job}
                resumeSkills={resumeSkills}
                resumeLoaded={resume.loaded}
                autoRemove={autoRemove}
                onDismiss={dismiss}
              />
            ))}
          </div>

          {visibleCount < filtered.length && (
            <button
              onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
              className="w-full mt-4 rounded-md border border-gray-300 bg-white px-4 py-2.5 text-sm hover:bg-gray-50"
            >
              Show more — {filtered.length - visibleCount} remaining
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
