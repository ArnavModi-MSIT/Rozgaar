"""Generate the configured career inventory offline, without running collectors."""
import argparse
import ast
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import backend.config as config
from rozgaar.paths import ROOT

GROUPS = ('GREENHOUSE', 'LEVER', 'ASHBY', 'ORACLE', 'GOOGLE_CAREERS', 'PHENOM', 'WORKDAY',
          'EIGHTFOLD', 'SUCCESSFACTORS', 'ICIMS', 'SMARTRECRUITERS', 'WORKABLE', 'AINTERVIEWS',
          'INDIAMART', 'WORKDAY_INDIA', 'WORKDAY_STUDENTS', 'EMPLOYER_PORTALS')
GENERIC = {name.lower() for name in GROUPS} | {'standard'}
ALIASES = {'qualcomm_students': 'qualcomm', 'morgan_stanley_students': 'morganstanley',
           'mastercard_workday': 'mastercard', 'tower_research': 'towerresearchcapital'}


def inventory():
    names = {row['key']: row['name'] for row in json.loads((ROOT/'docs/catalog/COMPANY_SOURCES.json').read_text(encoding='utf-8'))}
    names.update(config.DISPLAY_NAMES)
    entries = defaultdict(lambda: {'keys': set(), 'sources': set()})

    def add(key, source):
        name = names.get(key, key.replace('_', ' ').replace('-', ' ').title())
        entries[name]['keys'].add(key)
        entries[name]['sources'].add(source)

    for group in GROUPS:
        for row in getattr(config, group):
            key = row if isinstance(row, str) else row.get('company') or row.get('company_id')
            source = group.lower()
            if group == 'EMPLOYER_PORTALS':
                source += ' / ' + row['kind']
            add(key, source)
    # Parse registration names without importing adapter modules or HTTP clients.
    tree = ast.parse((ROOT/'backend/core/collector.py').read_text(encoding='utf-8'))
    platforms = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == 'PLATFORMS' for target in node.targets))
    for platform in platforms.elts:
        key = ast.literal_eval(platform.elts[0])
        if key not in GENERIC:
            add(ALIASES.get(key, key), key + ' (dedicated adapter)')
    return entries


def render(date):
    entries = inventory()
    lines = ['# Career-page company inventory', '', f'Updated: {date}.', '',
             f'**{len(entries)} company/display-name entries** configured in the career-page pipeline. Multiple boards or student feeds for the same display name share one row; separate divisions may retain their own display names.', '',
             'This is a configuration inventory, not a live health check, a count of companies with current jobs, or a guarantee of complete descriptions. It excludes the separate URL-reader pipeline.', '',
             'Compiled from `backend/config/sources.py`, `backend/config/career_expansion.py`, `backend/config/display.py`, and every registered collector in `backend/core/collector.py`.', '',
             'Regenerate offline after source changes: `runtime/python/Scripts/python.exe -m scripts.career.company_inventory`. This command does not collect jobs or change the database.', '',
             'The older `COMPANY_SOURCES.json` is a curated 75-company audit input, not the full inventory. Dated observations are in [Source maintenance](../SOURCE_STATUS.md); the [26 October expansion](CAREER_EXPANSION_20261026.md) records validation scope and salary uncertainty.', '',
             '| Company | Configuration key / board | Source / collector |', '|---|---|---|']
    for name, row in sorted(entries.items(), key=lambda item: item[0].casefold()):
        lines.append('| ' + name.replace('|', '\\|') + ' | ' + ', '.join('`'+key+'`' for key in sorted(row['keys']))
                     + ' | ' + ', '.join('`'+source+'`' for source in sorted(row['sources'])) + ' |')
    return '\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', default=datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime('%d %B %Y'))
    args = parser.parse_args()
    path = ROOT/'docs/catalog/CAREER_COMPANIES.md'
    path.write_text(render(args.date), encoding='utf-8')
    print(f'Wrote {len(inventory())} company/display-name entries to {path}')


if __name__ == '__main__':
    main()
