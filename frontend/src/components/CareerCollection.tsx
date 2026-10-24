import { useState } from "react";
import { platformRequest } from "../platform";
import type { PlatformState } from "../platform";

export default function CareerCollection({ platform, onChange }: { platform: PlatformState | null; onChange: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const running = ["running", "stopping"].includes(platform?.career.status ?? "");
  async function action(name: "start" | "stop") {
    if (!platform) return;
    setBusy(true); setError("");
    try { await platformRequest(`/careers/${name}`, platform.token, {}); await onChange(); }
    catch (e) { setError(e instanceof Error ? e.message : "Collection failed"); }
    finally { setBusy(false); }
  }
  return <section className="rounded-xl border border-gray-200 bg-white p-5 mb-5" aria-label="Career page collection">
    <div className="flex justify-between gap-3"><div><h2 className="font-semibold">Career page collection</h2><p className="text-sm text-gray-500 mt-1">Collect company openings, filter the list, then download a JSON batch for shortlisting.</p></div><span role="status" className="text-xs rounded-full bg-stone-100 px-3 py-1 self-start">{platform?.career.status ?? "loading"}</span></div>
    <div className="flex flex-wrap gap-2 items-center mt-4">
      <button className="rounded-md bg-sky-700 text-white px-4 py-2 text-sm disabled:opacity-40" disabled={busy || !platform || running || platform.offline} onClick={() => void action("start")}>Start career collection</button>
      <button className="rounded-md border border-gray-300 px-4 py-2 text-sm disabled:opacity-40" disabled={busy || !running} onClick={() => void action("stop")}>Stop collection</button>
      <span className="text-xs text-gray-500">{(platform?.counts.careers ?? 0).toLocaleString()} stored career records</span>
    </div>
    {platform?.offline && <p className="text-sm text-amber-800 mt-2">Offline mode is enabled. Saved jobs and JSON exports remain available.</p>}
    {error && <p role="alert" className="text-sm text-red-700 mt-2">{error}</p>}
    <details className="text-xs mt-3"><summary className="cursor-pointer text-gray-600">Collection log</summary><pre className="rounded-lg bg-stone-950 text-stone-200 p-3 mt-2 max-h-60 overflow-auto whitespace-pre-wrap">{platform?.career.logs.join("\n") || "No collection started from this session."}</pre><p className="text-gray-500 mt-2">Stopping preserves committed batches. A finished run may contain partial or failed sources; check its log.</p></details>
  </section>;
}
