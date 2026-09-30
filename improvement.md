# Improvement roadmap

This file lists proposed work for the current local, single-user prototype. Items here are **not implemented** unless marked otherwise. Start with data quality and evaluation before adding application automation.

## 1. Make listings trustworthy

### Check whether a job is still open

The database now records when a job was first seen and when the same source ID was observed again. Old rows are removed after 365 days. These dates do not tell us whether an employer closed a posting yesterday.

- Add `last_checked` and an `open`, `closed`, or `unknown` status to each job.
- Continue updating `last_seen` for exact source IDs. Mark a job closed only after a reliable source signal or repeated absence from a proven-complete source, since a failed or partial fetch must not close every job from that source.
- Show the check date and status in the React UI. Let the user open the original posting before applying.

**Done when:** a closed sample posting disappears from the default list, while a temporary source failure leaves existing postings marked unknown rather than closed.

### Store eligibility as data

The current experience extractor in [`core/experience.py`](core/experience.py) can miss postings that offer separate fresher and experienced tracks. [`fetchers/unstop.py`](fetchers/unstop.py) fetches open jobs and internships but does not apply student, degree, specialization, or passing-year filters from Unstop search pages.

- Save explicit source fields for minimum experience, student eligibility, degree or course, graduation year, and deadline when available.
- Keep `unknown` distinct from `not eligible`; do not infer eligibility from a missing field.
- Add filters for genuinely relevant student roles, including the Unstop IT and 2027 filters if their response fields can be verified.
- Check extracted experience against a small set of manually reviewed postings, especially mixed-track descriptions.

**Done when:** the UI can distinguish a confirmed fresher role from a role with no stated experience requirement.

### Monitor source health

[`run.py`](run.py) already stores per-source run statistics. Turn those into a simple health report: last successful fetch, fetched count, saved count, failure reason, and unusual drops. Keep rate limits and source access rules in mind; do not work around blocked or private endpoints.

**Done when:** a broken collector is visible without inspecting a long console log, and one source failure does not invalidate other sources.

## 2. Measure and improve matching

### Build a small evaluation set

The current [`core/matcher.py`](core/matcher.py) blends semantic similarity and skill overlap. Its score clipping bounds and relevance rules have not been calibrated on labeled resume–job pairs, so the displayed percentage is a ranking score rather than a probability of fit.

- Label about 100–200 resume–job pairs as relevant, borderline, or irrelevant across data, software, and unrelated roles. Keep resumes private and use only data you may share.
- Report precision at 10 for each resume, the rate of clearly irrelevant jobs in the top 10, and examples of false positives and false negatives.
- Compare the current blend with keyword-only and embedding-only baselines before changing weights or thresholds.
- If a new method wins on a held-out set, document the measured improvement and the cases it still misses.

**Done when:** changes to the match formula are supported by a repeatable evaluation, not just a few attractive examples.

### Handle long and difficult resumes

[`core/embeddings.py`](core/embeddings.py) limits model input length, so later sections of a long resume can be truncated. [`core/resume_text.py`](core/resume_text.py) extracts text from PDF, DOCX, and TXT files but does not OCR scanned PDFs.

- Detect empty or very short extraction and show a clear message; consider OCR only for scanned files.
- Compare whole-resume matching with section-level embeddings for skills, experience, and projects.
- Improve the current React resume skill editor with suggestions from the global skill vocabulary and clearer feedback when a correction changes job ranking.

**Done when:** a scanned or long sample resume has an understandable result, and section-level matching improves the labeled evaluation before replacing the current method.

## 3. Make the app easier to rely on

### Add useful application states

The UI can dismiss jobs. Add optional `saved`, `applied`, and `interview` states with dates and notes so users can track work without losing the original job link. Keep these records only in the local database by default.

**Done when:** a job can be saved, marked applied, and found again after restarting the app.

### Improve cold-start feedback and privacy

First-time embedding of a large job pool can take time. Show progress and explain when the model is downloading or new jobs are being embedded. The API now rejects resume files over 5 MB; consider a text-length limit and better file validation if larger inputs become common. Avoid logging resume text. The current FastAPI resume state is shared process memory, so keep the server on localhost until per-user state and authentication exist.

**Done when:** users see useful progress during a cold start, malformed uploads fail clearly, and resume contents do not appear in logs.

### Add automated checks

- Use saved, non-sensitive response fixtures to test pagination, normalization, and failures for representative fetchers such as Greenhouse, Workday, and Unstop.
- Test deduplication, India location handling, experience extraction, and skill matching with edge cases found in real postings.
- Test the FastAPI resume and job endpoints using a temporary SQLite database.
- Run Python tests and the React production build in GitHub Actions without live scraping or model downloads on every pull request.

**Done when:** a change that breaks parsing, the API contract, or the React build fails locally or in CI before it is merged.

## 4. Explore later

- **Application assistance:** investigate Playwright for opening a posting and prefilling common fields, with user review before any submission. Treat each employer's form and access rules separately.
- **Multi-user deployment:** only after adding authentication, per-user resume storage, access controls, and a deployment plan. The current API is designed for localhost use.
- **Source expansion:** add a source only when it provides real, relevant listings and can be maintained; improve existing source quality first.

## Suggested next milestone

1. Label a small resume–job evaluation set and record the current top-10 quality.
2. Add `last_seen` and a reliable open/closed/unknown status for collected jobs.
3. Add fixture-based tests for Unstop and one ATS collector, then set up CI.

These three tasks give evidence that the listings and ranking are useful before expanding the feature set.
