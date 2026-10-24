"""Read-only public-release checks, including all locally reachable Git blobs.

Reports locations and rule names, never matched credential values. This is a
small heuristic scan, not a guarantee that a repository contains no secrets.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
from raambaad.paths import ROOT

PATTERNS = {
    'private_key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github_token': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'aws_access_key': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'provider_api_key': re.compile(rb'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{35,}\b'),
    'personal_windows_path': re.compile(rb'[A-Za-z]:[\\/]+Users[\\/]+(?!Public|Default|example|user[\\/]|<)[A-Za-z0-9_.-]+', re.I),
}
PRIVATE_PARTS = {'runtime', '.archive', '.browser-profile', 'node_modules', '__pycache__', '.venv', 'venv'}
PRIVATE_SUFFIXES = {'.db', '.sqlite', '.sqlite3', '.pdf', '.docx', '.zip', '.pem', '.pfx', '.key'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def private_path(name):
    path = Path(name)
    return (bool(set(path.parts) & PRIVATE_PARTS) or path.suffix.lower() in PRIVATE_SUFFIXES
            or bool(re.search(r'\.(?:db|sqlite3?)(?:-.*)?$', path.name, re.I))
            or path.name in {'Cookies', 'Login Data', 'Local State', 'Web Data'}
            or path.name.startswith('career-pages-') and path.suffix == '.json'
            or path.name.startswith('.env') and path.name != '.env.example')


def scan_bytes(data, location):
    return [{'location':location, 'rule':name} for name, pattern in PATTERNS.items() if pattern.search(data)]


def audit(history=True):
    report = {'working_files':0, 'history_blobs':0, 'findings':[],
              'scope':'Existing tracked and unignored files; all blobs reachable from local Git refs.',
              'limitations':'Heuristic patterns only. Does not inspect remote-only refs, unreachable objects or encrypted contents.'}
    candidates = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').decode().split('\0')) - {''}
    for name in sorted(candidates):
        path = ROOT / name
        if not path.is_file():
            continue  # Pending tracked deletions are checked in history below.
        report['working_files'] += 1
        if private_path(name):
            report['findings'].append({'location':name, 'rule':'private_artifact'})
        report['findings'] += scan_bytes(path.read_bytes(), name)
    if history:
        objects = {}
        for line in git('rev-list', '--objects', '--all').decode().splitlines():
            oid, _, name = line.partition(' ')
            objects.setdefault(oid, name)
        proc = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            for oid, name in objects.items():
                proc.stdin.write((oid+'\n').encode()); proc.stdin.flush()
                header = proc.stdout.readline().split()
                if len(header) != 3:
                    raise RuntimeError('Unexpected Git object response')
                size = int(header[2]); data = proc.stdout.read(size); proc.stdout.read(1)
                if header[1] != b'blob':
                    continue
                report['history_blobs'] += 1
                location = f'history:{oid[:12]}:{name}'
                if private_path(name):
                    report['findings'].append({'location':location, 'rule':'private_artifact'})
                report['findings'] += scan_bytes(data, location)
        finally:
            proc.stdin.close(); proc.wait()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-history', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = audit(not args.no_history)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2))
    return int(bool(report['findings']))


if __name__ == '__main__':
    raise SystemExit(main())
