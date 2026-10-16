import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { HealthReport, JobStatePatch, TrackedJob, TrackerView } from "../types";

function date(value: number | null) { return value ? new Date(value * 1000).toLocaleString() : "Not recorded"; }

function TrackerCard({ job, onChange }: { job: TrackedJob; onChange: () => Promise<void> }) {
  const [notes, setNotes] = useState(job.notes);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { setNotes(job.notes); }, [job.notes]);
  async function change(patch?: JobStatePatch) {
    setBusy(true); setError("");
    try {
      if (patch) await api.updateJob(job.id, patch); else await api.restore([job.id]);
      await onChange();
    } catch (e) { setError(e instanceof Error ? e.message : "Couldn't save"); }
    finally { setBusy(false); }
  }
  return <article className="rounded-lg border border-gray-200 p-4 bg-white">
    <a className="font-semibold text-amber-800 underline" href={job.url} target="_blank" rel="noopener noreferrer">{job.title}</a>
    <p className="text-sm mt-1">{job.display_company} · {job.location}</p>
    <p className="text-xs text-gray-500 mt-1">{job.tracking_status} · posting {job.posting_status}{job.dismissed ? " · removed from discovery" : ""}</p>
    <p className="text-xs text-gray-500">Last seen: {date(job.last_seen)}{job.saved_at ? ` · Saved: ${date(job.saved_at)}` : ""}{job.applied_at ? ` · Applied: ${date(job.applied_at)}` : ""}</p>
    {job.status_evidence && <p className="text-xs text-gray-500">{job.status_evidence} ({date(job.status_checked_at)})</p>}
    <fieldset disabled={busy} className="mt-3 text-sm space-y-2 disabled:opacity-50">
      <div className="flex flex-wrap gap-3 items-center">
        <label>Track <select aria-label={`Track ${job.title}`} className="border rounded px-1" value={job.tracking_status} onChange={e => void change({ tracking_status: e.target.value as TrackedJob["tracking_status"] })}>
          <option value="none">None</option><option value="saved">Saved</option><option value="applied">Applied</option>
        </select></label>
        <label>After reviewing source <select aria-label={`Posting status for ${job.title}`} className="border rounded px-1" value={job.posting_status} onChange={e => void change({ posting_status: e.target.value as TrackedJob["posting_status"] })}>
          <option value="unknown">Unknown</option><option value="open">Open</option><option value="closed">Closed</option>
        </select></label>
        {!!job.dismissed && <button className="underline" onClick={() => void change()}>Restore to discovery</button>}
      </div>
      <textarea aria-label={`Notes for ${job.title}`} maxLength={4000} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Private notes: application date, follow-up, interview…" className="block w-full border rounded p-2 text-sm" rows={2} />
      <button className="underline disabled:opacity-40" disabled={notes === job.notes} onClick={() => void change({ notes })}>Save notes</button>
    </fieldset>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
  </article>;
}

export default function WorkspacePanel({ view, onJobsChange }: { view: TrackerView | "health"; onJobsChange: () => Promise<void> }) {
  const [jobs, setJobs] = useState<TrackedJob[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [health, setHealth] = useState<HealthReport | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [issuesOnly, setIssuesOnly] = useState(false);
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      if (view === "health") setHealth(await api.sourceHealth());
      else {
        const result = await api.tracker(view, offset);
        if (offset > 0 && result.jobs.length === 0) {
          setOffset(Math.max(0, Math.floor((result.total - 1) / 100) * 100));
        }
        setJobs(result.jobs); setTotal(result.total);
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Couldn't load"); }
    finally { setLoading(false); }
  }, [view, offset]);
  useEffect(() => { void load(); }, [load]);
  async function changed() { await onJobsChange(); await load(); }
  return <section className="space-y-3">
    <div className="flex justify-between items-center"><h2 className="text-lg font-semibold">{view === "health" ? "Source health" : `${view[0].toUpperCase()}${view.slice(1)} jobs (${total})`}</h2><button disabled={loading} className="underline text-sm" onClick={() => void load()}>Refresh</button></div>
    <p className="text-xs text-gray-500">{view === "health" ? "Reads the latest local collection results. This screen does not start a scraper." : "Saved history ignores discovery filters. Opening a link does not mark an application. Restored jobs still follow your discovery filters."}</p>
    {loading && <p className="text-sm">Loading…</p>}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {!loading && !error && view !== "health" && jobs.length === 0 && <p className="text-sm">No jobs here.</p>}
    {view !== "health" && <>
      {jobs.map(job => <TrackerCard key={job.id} job={job} onChange={changed} />)}
      <div className="flex gap-4 text-sm"><button disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - 100))} className="underline disabled:opacity-40">Previous</button><span>{total ? `${offset + 1}–${Math.min(offset + 100, total)} of ${total}` : "0"}</span><button disabled={offset + 100 >= total || loading} onClick={() => setOffset(offset + 100)} className="underline disabled:opacity-40">Next</button></div>
    </>}
    {view === "health" && health && <>
      <p className="text-sm text-gray-600">{health.note}</p>
      <details><summary className="cursor-pointer text-sm underline">Platform summaries ({health.platforms.length})</summary><ul className="text-xs mt-2 space-y-1">{health.platforms.map(p => <li key={p.platform}>{p.platform}: <strong>{p.health}</strong> · {p.latest.jobs_fetched} returned · {date(p.latest.timestamp)}{p.latest.error ? ` · ${p.latest.error}` : ""}</li>)}</ul></details>
      <div className="flex flex-wrap gap-4 text-sm"><input aria-label="Find company or platform" value={search} onChange={e => setSearch(e.target.value)} placeholder="Find company or platform" className="border rounded p-2" /><label className="self-center"><input type="checkbox" checked={issuesOnly} onChange={e => setIssuesOnly(e.target.checked)} /> Failed / partial / missing descriptions</label></div>
      <div className="overflow-x-auto"><table className="w-full text-xs text-left"><thead><tr className="border-b"><th className="py-2">Company / source</th><th>Outcome</th><th>Returned</th><th>India / unknown</th><th>Missing JD</th><th>Checked</th></tr></thead><tbody>
        {health.companies.filter(c => `${c.name} ${c.platform}`.toLowerCase().includes(search.toLowerCase()) && (!issuesOnly || ["failed", "partial"].includes(c.status) || (c.missing_descriptions ?? 0) > 0)).map(c => <tr key={`${c.company}:${c.platform}`} className="border-b align-top">
          <td className="py-3 pr-2"><strong>{c.name}</strong><br />{c.platform}{!c.configured ? " (old source)" : ""}<br />{c.stored} stored · {c.closed} marked closed</td>
          <td className="py-3 pr-2 max-w-xs"><strong>{c.status}</strong>{c.error && <p className="mt-1 text-gray-500 break-words">{c.error}</p>}</td>
          <td className="py-3">{c.fetched ?? "—"}</td><td className="py-3">{c.india_or_unknown ?? "—"}</td><td className="py-3">{c.missing_descriptions ?? "—"}</td><td className="py-3">{date(c.timestamp)}</td>
        </tr>)}
      </tbody></table></div>
    </>}
  </section>;
}
