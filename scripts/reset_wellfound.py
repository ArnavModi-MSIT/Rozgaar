"""Reset Wellfound checkpoints and deduplication only; preserve other sources.

Use --apply to clear active data. A private recovery backup is kept outside the
reader data directory, so it cannot be reimported by the seen-posting store.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3

from rozgaar.paths import ROOT, READER_DATA
from url_reader.identity import source_for_url
from url_reader.storage.lock import CollectionLock


def checkpoints(directory):
    found = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        named = path.name.startswith(('wellfound_', 'repair_wellfound_'))
        if path.suffix == '.json':
            try:
                value = json.loads(path.read_text(encoding='utf-8-sig'))
            except (ValueError, OSError):
                value = {}
            if isinstance(value, dict):
                source = value.get('source') or source_for_url(value.get('search_url') or '')
                if named and source and source != 'wellfound':
                    raise ValueError(f'Refusing to reset a file marked as another source: {path.name}')
                named = named or source == 'wellfound'
        if named:
            found.append(path)
    return found


def reset(directory, backup, apply=False):
    directory, backup = Path(directory).resolve(), Path(backup).resolve()
    if backup.is_relative_to(directory) or directory.is_relative_to(backup):
        raise ValueError('The recovery backup must be outside the reader data directory.')
    with CollectionLock(directory / '.collection.lock'):
        files = checkpoints(directory)
        stores = []
        for path in sorted(directory.glob('*.sqlite3')):
            with sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True) as conn:
                tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'seen_postings' not in tables:
                    continue
                count = conn.execute("SELECT COUNT(*) FROM seen_postings WHERE source='wellfound'").fetchone()[0]
                stores.append((path, count))
        report = {'checkpoint_files':[p.name for p in files], 'seen_rows':{p.name:n for p,n in stores}, 'applied':False}
        if not apply:
            return report
        backup.mkdir(parents=True, exist_ok=False)
        # Back up every store before changing files or rows, including WAL data.
        for path, _ in stores:
            with sqlite3.connect(path) as conn, sqlite3.connect(backup/path.name) as destination:
                conn.backup(destination)
        for path in files:
            if not path.resolve().is_relative_to(directory):
                raise ValueError('Checkpoint escaped the intended data directory.')
            shutil.move(str(path), str(backup/path.name))
        for path, _ in stores:
            with sqlite3.connect(path) as conn:
                others_before = list(conn.execute("SELECT * FROM seen_postings WHERE source!='wellfound' ORDER BY source,posting_id"))
                conn.execute("DELETE FROM seen_postings WHERE source='wellfound'")
                if conn.execute("SELECT 1 FROM sqlite_master WHERE name='imported_files'").fetchone():
                    for (name,) in conn.execute('SELECT path FROM imported_files').fetchall():
                        if Path(name).name.startswith(('wellfound_', 'repair_wellfound_')) or Path(name).resolve() in files:
                            conn.execute('DELETE FROM imported_files WHERE path=?', (name,))
                others_after = list(conn.execute("SELECT * FROM seen_postings WHERE source!='wellfound' ORDER BY source,posting_id"))
                if others_before != others_after:
                    raise RuntimeError('Non-Wellfound history changed; rolling back.')
        report.update(applied=True, backup=str(backup))
        (backup/'reset-report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    backup = ROOT/'.archive'/('wellfound-reset-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    print(json.dumps(reset(READER_DATA, backup, args.apply), indent=2))


if __name__ == '__main__':
    main()
