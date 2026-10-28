import { useState } from "react";
import { platformRequest, saveJson } from "../platform";
import type { PlatformState, CareerExport } from "../platform";
import type { Job } from "../types";

type Props = {
  platform: PlatformState | null;
  filtered: Job[];
  exportFilters: Record<string, string | boolean | number | null>;
  loading: boolean;
  loadError: string | null;
  onChanged: () => Promise<void>;
  onRemoved: (ids: string[]) => void;
  onError: (message: string) => void;
};

export default function CareerExportPanel({ platform, filtered, exportFilters, loading, loadError, onChanged, onRemoved, onError }: Props) {
  const [exportBusy, setExportBusy] = useState(false);
  const [exportLimit, setExportLimit] = useState(100);
  const [exportNotice, setExportNotice] = useState("");
  async function downloadTopJobs() {
    if (!platform || !filtered.length) return;
    const ids = filtered.slice(0, exportLimit).map(job => job.id);
    setExportBusy(true); onError(""); setExportNotice("");
    try {
      const payload = await platformRequest<CareerExport>("/career-exports", platform.token, {
        ids, limit: exportLimit, filters: exportFilters,
      });
      saveJson(payload, payload.filename);
      setExportNotice(`Download requested for ${payload.count} jobs. After saving the file, remove this exact batch to show the next jobs.`);
      await onChanged();
    } catch (e) { onError(e instanceof Error ? e.message : "Could not export jobs"); }
    finally { setExportBusy(false); }
  }

  async function downloadLastBatch() {
    if (!platform?.latest_export) return;
    const batch = platform.latest_export;
    setExportBusy(true); onError("");
    try {
      const payload = await platformRequest<CareerExport>(`/career-exports/${batch.batch_id}`);
      saveJson(payload, payload.filename);
      setExportNotice(`Download requested for the saved batch of ${payload.count} jobs.`);
    } catch (e) { onError(e instanceof Error ? e.message : "Could not download JSON"); }
    finally { setExportBusy(false); }
  }

  async function removeLastBatch() {
    if (!platform?.latest_export) return;
    const batchId = platform.latest_export.batch_id;
    setExportBusy(true); onError("");
    try {
      const result = await platformRequest<{ removed: number; ids: string[] }>(`/career-exports/${batchId}/remove`, platform.token, {});
      onRemoved(result.ids);
      setExportNotice(`Removed ${result.removed} jobs from the JSON batch. Your filters do not change which jobs this removes.`);
      await onChanged();
    } catch (e) { onError(e instanceof Error ? e.message : "Could not remove batch"); }
    finally { setExportBusy(false); }
  }

  return (
<section className="rounded-xl border border-sky-200 bg-sky-50 p-4 mb-5" aria-label="Career JSON export">
            <h2 className="font-semibold">JSON for shortlisting</h2>
            <p className="text-sm text-gray-600 mt-1">Export the first {Math.min(exportLimit, filtered.length)} jobs in this filtered list, in the same order, with their full stored descriptions.</p>
            <div className="flex flex-wrap gap-2 mt-3">
              <label className="flex items-center gap-2 text-sm">Jobs per JSON<select className="rounded-md border border-gray-300 bg-white px-3 py-2" value={exportLimit} disabled={exportBusy} onChange={e => setExportLimit(Number(e.target.value))}>{[50, 100, 250, 500, 1000].map(size => <option key={size} value={size}>{size}</option>)}</select></label>
              <button className="rounded-md bg-sky-700 text-white px-4 py-2 text-sm disabled:opacity-40" disabled={exportBusy || loading || !!loadError || !platform || !filtered.length} onClick={() => void downloadTopJobs()}>{exportBusy ? "Working…" : `Download top ${Math.min(exportLimit, filtered.length)} JSON`}</button>
              {platform?.latest_export && <><button className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm disabled:opacity-40" disabled={exportBusy} onClick={() => void downloadLastBatch()}>Download last batch again</button><button className="rounded-md border border-amber-300 bg-white px-3 py-2 text-sm disabled:opacity-40" disabled={exportBusy || !platform.latest_export.remaining_count} onClick={() => void removeLastBatch()}>Remove downloaded batch ({platform.latest_export.remaining_count})</button></>}
            </div>
            {platform?.latest_export && <p className="text-xs text-gray-500 mt-2 break-all">Last JSON: {platform.latest_export.filename} · {platform.latest_export.count} jobs · {platform.latest_export.remaining_count} still in the list. Removal is separate from download and can be undone.</p>}
            {exportNotice && <p role="status" className="text-sm text-sky-900 mt-2">{exportNotice}</p>}
          </section>
  );
}
