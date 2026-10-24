import { useEffect, useState } from "react";
import { platformRequest, sourceLabel } from "../platform";
import type { PlatformState, ReaderState, ReaderItem } from "../platform";

interface Props { platform: PlatformState | null; onChange: () => Promise<void> }
const button = "rounded-md border border-gray-300 px-3 py-2 text-sm bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed";
const field = "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm";

export default function UrlReader({ platform, onChange }: Props) {
  const [reader, setReader] = useState<ReaderState | null>(null);
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState("");
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState("");
  const [limit, setLimit] = useState(150);
  const [delay, setDelay] = useState(3);
  const [workers, setWorkers] = useState(1);
  const [resume, setResume] = useState(true);
  const [repair, setRepair] = useState(false);
  const [openWellfound, setOpenWellfound] = useState(true);
  const [initialized, setInitialized] = useState(false);
  const [file, setFile] = useState("");
  const [query, setQuery] = useState("");
  const [quality, setQuality] = useState("all");
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<ReaderItem | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const search = new URLSearchParams({ q: query, quality, page: String(page) });
        if (file) search.set("file", file);
        const value = await platformRequest<ReaderState>(`/reader/state?${search}`);
        if (active) { setReader(value); setPollError(""); }
      } catch (e) { if (active) setPollError(e instanceof Error ? e.message : "Reader unavailable"); }
      if (active) timer = setTimeout(() => void poll(), 2500);
    };
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [file, query, quality, page]);

  useEffect(() => {
    if (reader && !initialized) {
      setUrl(reader.settings.url); setLimit(reader.settings.limit); setDelay(reader.settings.delay);
      setWorkers(reader.settings.workers ?? 1); setInitialized(true);
      setOpenWellfound(reader.settings.wellfound_live ?? true);
    }
  }, [reader, initialized]);

  async function action(path: string, payload: object = {}) {
    if (!platform) return;
    setBusy(true); setError("");
    try {
      await platformRequest(path, platform.token, payload);
      await onChange();
    } catch (e) { setError(e instanceof Error ? e.message : "Operation failed"); }
    finally { setBusy(false); }
  }

  async function inspect(item: ReaderItem) {
    if (!reader?.file) return;
    setDetailBusy(true); setError("");
    try {
      setDetail(await platformRequest<ReaderItem>(`/reader/job?${new URLSearchParams({ file: reader.file, id: item.job_id })}`));
    } catch (e) { setError(e instanceof Error ? e.message : "Could not read item"); }
    finally { setDetailBusy(false); }
  }

  const readerRunning = reader?.running ?? false;
  const useOpenWellfound = openWellfound && /^https:\/\/(?:www\.)?wellfound\.com\/jobs\/?(?:[?#]|$)/.test(url.trim());

  return <section className="space-y-5" aria-label="URL reader workspace">
    <div><h2 className="text-xl font-semibold">URL reader</h2><p className="text-sm text-gray-500 mt-1">Collect from a search URL and download the original JSON. Reader results stay separate from career pages.</p></div>
    {error && <p role="alert" className="rounded-md bg-red-50 text-red-700 p-3 text-sm">{error}</p>}
    {pollError && <p role="alert" className="rounded-md bg-red-50 text-red-700 p-3 text-sm">{pollError}</p>}
    {platform?.offline && <p className="rounded-md bg-amber-50 p-3 text-sm">Offline mode is enabled. Saved results are available; new collection is disabled.</p>}
    <section className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex justify-between items-center gap-3"><h3 className="font-semibold">Browser job reader</h3><span role="status" className="text-xs rounded-full bg-stone-100 px-3 py-1">{reader?.status ?? "loading"}</span></div>
      <p className="text-sm text-gray-500 mt-1">LinkedIn jobs / posts · Internshala jobs / internships · Naukri · Instahyre · Wellfound</p>
      <form className="space-y-4 mt-4" onSubmit={e => { e.preventDefault(); setFile(""); setPage(1); void action("/reader/start", { url, limit, delay, workers, fresh: !resume, retry_incomplete: repair, wellfound_live: useOpenWellfound }); }}>
        <label className="block text-sm font-medium">Search URL<textarea aria-label="Search URL" required rows={3} className={field + " mt-1 font-normal"} value={url} onChange={e => setUrl(e.target.value)} placeholder="Paste the search URL from a supported website" /></label>
        <p className="text-xs text-gray-500"><button type="button" className="text-sky-700 underline" disabled={readerRunning} onClick={() => { setOpenWellfound(true); setUrl("https://wellfound.com/jobs"); }}>Use filtered Wellfound tab</button> · <button type="button" className="text-sky-700 underline" disabled={readerRunning} onClick={() => { setOpenWellfound(false); setUrl("https://wellfound.com/location/india"); }}>Public India results</button> · <button type="button" className="text-sky-700 underline" disabled={readerRunning} onClick={() => { setOpenWellfound(false); setUrl("https://wellfound.com/jobs"); }}>Public highlights</button></p>
        {useOpenWellfound && <p className="rounded-md bg-sky-50 p-3 text-sm">Open exactly one signed-in Wellfound search in reader Chrome, set your filters there, then start here. The reader uses that open tab without reloading it. Do not change its filters or manually switch result pages while collecting. Resume from the same result batch. Captured filters get a separate JSON checkpoint.</p>}
        <div className="grid grid-cols-3 gap-3">
          <label className="text-sm">Target items<input className={field + " mt-1"} type="number" min={1} max={1000} step={1} required value={limit} onChange={e => setLimit(Number(e.target.value))} /></label>
          <label className="text-sm">Delay (seconds)<input className={field + " mt-1"} type="number" min={1} step={0.5} required value={delay} onChange={e => setDelay(Number(e.target.value))} /></label>
          <label className="text-sm">Detail readers<select className={field + " mt-1"} value={workers} onChange={e => setWorkers(Number(e.target.value))}>{[1, 2, 3].map(n => <option key={n} value={n}>{n} reader{n > 1 ? "s" : ""}</option>)}</select></label>
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          <label><input type="checkbox" checked={resume} onChange={e => setResume(e.target.checked)} /> Resume today’s progress</label>
          <label><input type="checkbox" checked={repair} onChange={e => setRepair(e.target.checked)} /> Repair incomplete descriptions</label>
        </div>
        <div className="flex flex-wrap gap-2"><button className={button + " bg-sky-50"} type="submit" disabled={busy || !initialized || !platform || readerRunning || platform.offline}>Start browser reader</button><button type="button" className={button} disabled={busy || !readerRunning} onClick={() => void action("/reader/stop")}>Stop browser reader</button></div>
      </form>
      <p className="text-xs text-gray-500 mt-3">Reuses the dedicated Chrome profile and existing seen-posting history. Sign in there when needed. Verification pauses collection; saved progress can be resumed.</p>
      <p className="text-xs text-gray-500 mt-1">Stalled pages retry automatically. After 90 seconds without progress, the reader restarts once from its saved queue. Stop can terminate an unresponsive worker.</p>
      {reader && <div className="border-t border-gray-100 mt-5 pt-4">
        {reader.search_state && <p className="text-xs rounded-md bg-sky-50 p-3 mb-3">Captured Wellfound search: {reader.search_state.header_text} · {reader.search_state.result_count} results at capture</p>}
        <div className="grid grid-cols-4 gap-3">{[["Saved", reader.saved], ["Attempted", reader.attempted], ["Skipped", reader.skipped], ["Pending", reader.pending]].map(([name, count]) => <div key={name}><p className="text-xl font-semibold tabular-nums">{Number(count).toLocaleString()}</p><p className="text-xs text-gray-500">{name}</p></div>)}</div>
        <progress className="w-full mt-3 accent-sky-600" max={reader.target || 1} value={reader.saved} aria-label="Reader collection progress" />
        <p className="text-sm mt-2">{reader.message || "Ready for collection."}</p>
        <p className="text-xs text-gray-500 mt-2">{reader.complete_candidates} complete candidates · {reader.incomplete} need review · {reader.errors} errors · {reader.retried} retries · {reader.pages_advanced} result batches</p>
        <p className="text-xs text-gray-500 mt-1">Extraction checks do not guarantee source completeness.</p>
        {reader.last_error != null && <details className="text-xs mt-2 text-red-700"><summary>Latest reader error</summary><pre className="whitespace-pre-wrap">{JSON.stringify(reader.last_error, null, 2)}</pre></details>}
        {reader.pagination != null && <details className="text-xs mt-2"><summary>Pagination diagnostics</summary><pre className="whitespace-pre-wrap">{JSON.stringify(reader.pagination, null, 2)}</pre></details>}
      </div>}
    </section>

    <section className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
      <div className="flex flex-wrap justify-between items-center gap-3"><h3 className="font-semibold">Reader results and run history</h3>{reader?.file && <a className="text-sm underline text-sky-700" href={`/api/platform/reader/download?${new URLSearchParams({ file: reader.file })}`}>Download JSON</a>}</div>
      <label className="block text-sm">Run<select aria-label="Saved run" className={field + " mt-1"} value={file} onChange={e => { setFile(e.target.value); setPage(1); }}><option value="">Current / latest run</option>{reader?.history.map(run => <option key={run.file} value={run.file}>{sourceLabel(run.source)} · {run.count} items · {run.status} · {run.file}</option>)}</select></label>
      <div className="grid grid-cols-2 gap-3"><input aria-label="Search reader results" className={field} type="search" placeholder="Search title, company or text" value={query} onChange={e => { setQuery(e.target.value); setPage(1); }} /><select aria-label="Description quality" className={field} value={quality} onChange={e => { setQuality(e.target.value); setPage(1); }}><option value="all">All description quality</option><option value="complete_candidate">Complete candidate</option><option value="suspected_truncated">Needs review</option><option value="missing">Missing description</option></select></div>
      <p className="text-xs text-gray-500 break-all">{reader?.file || "No saved run"}{reader?.updated_at ? ` · Updated ${new Date(reader.updated_at).toLocaleString()}` : ""}</p>
      <div className="divide-y divide-gray-100">{reader?.jobs.map(item => <article key={item.job_id} className="py-3"><div className="flex justify-between gap-3"><div><a className="font-medium text-amber-800 hover:underline" target="_blank" rel="noopener noreferrer" href={item.link}>{item.title || "Untitled item"}</a><p className="text-sm text-gray-500">{item.company} · {item.description_status.replace(/_/g, " ")}</p></div><button className={button} disabled={detailBusy} onClick={() => void inspect(item)}>Read text</button></div><p className="text-xs text-gray-500 mt-1">{item.location_and_posting_info}</p></article>)}{reader && !reader.jobs.length && <p className="text-sm text-gray-500 py-3">No matching items in this run.</p>}</div>
      <div className="flex justify-between items-center"><button className={button} disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button><span className="text-xs text-gray-500">Page {reader?.jobs_page ?? 1} of {reader?.jobs_pages ?? 1} · {reader?.jobs_matching ?? 0} items</span><button className={button} disabled={!reader || page >= reader.jobs_pages} onClick={() => setPage(p => p + 1)}>Next</button></div>
    </section>
    {detail && <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={() => setDetail(null)}><section role="dialog" aria-modal="true" aria-label={detail.title} className="bg-white rounded-xl p-6 max-w-3xl w-full max-h-[85vh] overflow-auto" onClick={e => e.stopPropagation()} onKeyDown={e => { if (e.key === "Escape") setDetail(null); }}><button autoFocus className={button + " float-right"} onClick={() => setDetail(null)}>Close</button><h3 className="text-lg font-semibold pr-20">{detail.title}</h3><p className="text-sm text-gray-500 mt-1">{detail.company}</p><a className="text-sm underline text-sky-700" href={detail.link} target="_blank" rel="noopener noreferrer">Open original</a><pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed mt-4">{detail.description || "Description not available."}</pre></section></div>}
  </section>;
}
