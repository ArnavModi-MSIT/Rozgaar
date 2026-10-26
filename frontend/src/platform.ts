export const sourceLabel = (source: string) => ({
  linkedin: "LinkedIn", internshala: "Internshala", naukri: "Naukri",
  instahyre: "Instahyre", wellfound: "Wellfound", indeed: "Indeed", linkedin_posts: "LinkedIn posts",
}[source.replace(/^reader_/, "")] ?? source.replace(/_/g, " "));

export interface PlatformState {
  app: string; token: string; mode: "separate"; data_revision: number; counts: { careers: number };
  career: { status: string; exit_code: number | null; started_at: number | null; logs: string[] };
  reader_running: boolean; offline: boolean;
  latest_export: CareerExportBatch | null;
  separation: { archived: number; already_separate: boolean; backup?: string; archive?: string } | null;
}
export interface CareerExportBatch {
  batch_id: string; filename: string; created_at: number; removed_at: number | null;
  count: number; remaining_count: number;
}
export interface CareerExport {
  batch_id: string; filename: string; count: number; jobs: Record<string, unknown>[];
}
export function saveJson(payload: object, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url; link.download = filename;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
export interface ReaderItem {
  job_id: string; title: string; company: string; link: string;
  location_and_posting_info: string; description_status: string; description?: string;
}
export interface ReaderState {
  running: boolean; file: string | null; active_file: string | null; status: string; message: string;
  saved: number; attempted: number; pending: number; skipped: number; errors: number;
  complete_candidates: number; incomplete: number; retried: number; pages_advanced: number;
  jobs_page: number; jobs_pages: number; jobs_matching: number; target: number;
  updated_at: string | null; source: string; jobs: ReaderItem[]; last_error: unknown; pagination: unknown;
  settings: { url: string; limit: number; delay: number; workers?: number; wellfound_live?: boolean };
  search_state?: { mode: string; header_text: string; result_count: number; fingerprint: string } | null;
  history: { file: string; count: number; errors: number; source: string; status: string; updated_at: string }[];
}

export async function platformRequest<T>(path: string, token?: string, payload?: object): Promise<T> {
  const response = await fetch(`/api/platform${path}`, payload === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json", "X-Platform-Token": token ?? "" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try { const value = await response.json(); message = typeof value.detail === "string" ? value.detail : message; } catch { /* Keep HTTP error. */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
