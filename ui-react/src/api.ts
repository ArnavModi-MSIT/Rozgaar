// Thin fetch wrapper over api/main.py. All URLs are relative on purpose —
// see vite.config.ts for why (same code path in dev and production).

import type { Job, JobDetail, ResumeState, ResumeUploadResult, Stats } from "./types";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    // FastAPI puts the human-readable reason in `detail`; fall back to the
    // status line when the body isn't the shape we expect.
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) message = body.detail;
    } catch {
      /* non-JSON error body — keep the status line */
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async stats(): Promise<Stats> {
    return json(await fetch("/api/stats"));
  },

  async jobs(): Promise<Job[]> {
    const data = await json<{ jobs: Job[] }>(await fetch("/api/jobs"));
    return data.jobs;
  },

  async jobDetail(id: string): Promise<JobDetail> {
    return json(await fetch(`/api/jobs/${encodeURIComponent(id)}`));
  },

  async dismiss(id: string): Promise<void> {
    await json(await fetch(`/api/jobs/${encodeURIComponent(id)}/dismiss`, { method: "POST" }));
  },

  async dismissBulk(ids: string[]): Promise<number> {
    const data = await json<{ dismissed: number }>(
      await fetch("/api/jobs/dismiss-bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids }),
      }),
    );
    return data.dismissed;
  },

  async uploadResume(file: File, saveForLater: boolean): Promise<ResumeUploadResult> {
    const form = new FormData();
    form.append("file", file);
    form.append("save_for_later", String(saveForLater));
    return json(await fetch("/api/resume", { method: "POST", body: form }));
  },

  async resume(): Promise<ResumeState> {
    return json(await fetch("/api/resume"));
  },

  async usePreviousResume(): Promise<ResumeUploadResult> {
    return json(await fetch("/api/resume/previous", { method: "POST" }));
  },

  async deleteSavedResume(): Promise<void> {
    await json(await fetch("/api/resume/saved", { method: "DELETE" }));
  },

  async clearResume(): Promise<void> {
    await json(await fetch("/api/resume", { method: "DELETE" }));
  },

  async updateResumeSkills(skills: string[]): Promise<{ skills: string[] }> {
    return json(
      await fetch("/api/resume/skills", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skills }),
      }),
    );
  },
};
