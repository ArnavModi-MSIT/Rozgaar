# Public-release preparation

Prepared on 24 October 2026. All changes are local; publishing and Git history changes are separate actions.

## Changes

- Replaced stale setup and architecture notes with the current modular layout and Windows setup commands.
- Preserved old notes under ignored `.archive/public-prep-20261024/` rather than deleting local history.
- Kept the source inventory used by tests under `docs/catalog/`; generated source-audit reports now go to `runtime/artifacts/`.
- Expanded ignore rules for databases, sidecars, resumes, keys, logs, exports and backups; added consistent source line-ending rules.
- Added contribution/security guidance and a reusable release scan. CI runs the scan with full checkout history.

## Checks

- Frontend production build passed.
- 510 unit/API tests and all 11 intercepted browser fixtures passed.
- The heuristic release scan inspected 737 locally reachable Git blobs and reported no configured credential-pattern or private-artifact matches.
- Git's staging dry-run included no `runtime/`, `.archive/`, browser profiles, dependencies or generated frontend bundles.
- Local documentation links were checked.

The detailed scan is saved privately as `runtime/artifacts/public-release-audit.json`. Run `python -m scripts.release_check` again after further changes. Pattern scans are not proof that no sensitive content exists; remote-only refs and unreachable objects were not scanned.

## Publication decisions

The repository uses the MIT license, selected by the owner. See the root `LICENSE` file. Third-party dependencies retain their own licenses. The existing origin remote is unchanged. No commit, push, history rewrite or repository-visibility change was performed.
