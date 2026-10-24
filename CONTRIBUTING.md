# Contributing

Use the Windows setup in [README](README.md). Keep changes within the existing modules; [the code map](docs/CODE_MAP.md) lists edit locations.

- Keep career and URL-reader stores separate. Never collect at startup.
- Preserve snapshots, tracking/removal state and checkpoints. Test migrations on synthetic databases.
- Never commit real resumes, job exports, account data, cookies or browser profiles. Use synthetic fixtures.
- Treat missing descriptions and requirements as unknown. Preserve full source text and label partial source results.
- Do not bypass account verification or automate application submission.

Run `runtime/python/Scripts/python.exe -m scripts.check`. For browser changes, install the fixture browser and run `-m scripts.check --browser`. For UI changes, run `npm ci` and `npm run build` in `frontend/`. Include the relevant checks and limits in a pull request.

Before publishing, run `runtime/python/Scripts/python.exe -m scripts.release_check`. This scans the candidate files and locally reachable Git history using heuristic patterns; review the diff as well. Do not attach runtime files to public issues.
