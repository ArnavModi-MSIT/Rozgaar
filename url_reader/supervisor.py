"""A killable browser runner: stalled Playwright calls cannot trap the dashboard."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import urlopen

IDLE_TIMEOUT = 90
STOP_GRACE = 5


class FileStopSignal:
    def __init__(self, path, registry_path):
        self.path, self.registry_path = Path(path), registry_path

    def is_set(self):
        return self.path.exists()


def close_owned_targets(cdp, registry):
    """Use Chrome's local browser endpoint, independent of a frozen renderer."""
    parts = urlsplit(cdp)
    if parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return
    scheme = "https" if parts.scheme in {"https", "wss"} else "http"
    origin = urlunsplit((scheme, parts.netloc, "", "", ""))
    try:
        targets = Path(registry).read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    handed_off = {target[1:] for target in targets if target.startswith("!")}
    deadline = time.monotonic() + 5
    try:
        with urlopen(origin + "/json/list", timeout=2) as response:
            live = {item.get("id") for item in json.load(response) if isinstance(item, dict)}
    except (OSError, ValueError, TypeError):
        return
    for target in dict.fromkeys(targets):
        if target in handed_off or target not in live or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", target):
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            with urlopen(origin + "/json/close/" + quote(target, safe=""), timeout=min(2, remaining)) as response:
                response.read(128)
        except OSError:
            pass  # Already-closed targets and disconnected Chrome are normal here.


def _stamp(path):
    try:
        stat = Path(path).stat()
        return stat.st_mtime_ns, stat.st_size
    except OSError:
        return None


def _terminate(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


def execute(args, *, idle_timeout=IDLE_TIMEOUT, stop_grace=STOP_GRACE, recovery_limit=1, command_factory=None):
    import url_reader.engine as reader
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    recoveries = 0
    # Sidecar files never appear among the reader's JSON runs.
    with tempfile.TemporaryDirectory(prefix=".watchdog-", dir=output.parent) as folder:
        folder = Path(folder)
        request, reply, stop, registry = [folder / name for name in ("request", "reply", "stop", "targets")]
        settings = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()
                    if key not in {"stop_event", "seen_store"}}
        while True:
            request.write_text(json.dumps(settings), encoding="utf-8")
            reply.unlink(missing_ok=True)
            stop.unlink(missing_ok=True)
            registry.write_text("", encoding="utf-8")
            command = (command_factory(request, reply, stop, registry) if command_factory else
                       [sys.executable, "-u", "-m", "url_reader.supervisor", "--child", str(request), str(reply), str(stop), str(registry)])
            process = subprocess.Popen(command, cwd=reader.PROJECT_ROOT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            last_stamp, last_progress = _stamp(output), time.monotonic()
            stopping_at = None
            reason = None
            try:
                while process.poll() is None:
                    now = time.monotonic()
                    current = _stamp(output)
                    if current != last_stamp:
                        last_stamp, last_progress = current, now
                    if args.stop_event.is_set():
                        if stopping_at is None:
                            stop.touch()
                            stopping_at = now
                        if now - stopping_at >= stop_grace:
                            reason = "stopped"
                            break
                    elif now - last_progress >= max(idle_timeout, float(settings.get("delay", 0)) + min(30, idle_timeout)):
                        reason = "stalled"
                        break
                    time.sleep(0.1)
                if reason:
                    _terminate(process)
                if not reason and reply.is_file():
                    value = json.loads(reply.read_text(encoding="utf-8"))
                    return value["result"], value["code"]
                try:
                    result = json.loads(output.read_text(encoding="utf-8"))
                    reader.validate_checkpoint(result, settings["url"], settings.get("search_state"))
                except (OSError, ValueError, TypeError, KeyError):
                    # Do not replace a pre-existing or incompatible checkpoint on startup failure.
                    return {"status": "interrupted" if reason == "stopped" else "failed", "jobs": [], "errors": [],
                            "stop_reason": "Stopped before browser progress was initialized." if reason == "stopped" else "Browser runner stopped before initializing progress. Existing files were preserved."}, 130 if reason == "stopped" else 1
                if reason == "stalled" and recoveries < recovery_limit:
                    recoveries += 1
                    settings["fresh"] = False
                    # Repair passes cannot reopen their output as a fresh repair file.
                    if settings.get("retry_incomplete"):
                        break
                    result.update(status="running", browser_recoveries=result.get("browser_recoveries", 0) + 1,
                                  activity="Browser stalled. Restarting owned tabs from saved progress...")
                    reader.save_result(output, result)
                    print(result["activity"], flush=True)
                    continue
                break
            finally:
                _terminate(process)
                close_owned_targets(settings.get("cdp", ""), registry)
        result.update(status="interrupted" if reason == "stopped" else "partial", activity="",
                      stop_reason=("Stopped. Saved jobs and pending links are preserved." if reason == "stopped" else
                                   "Browser stopped making progress. Saved jobs and pending links are preserved; resume this run to retry."))
        reader.save_result(output, result)
        return result, 130 if reason == "stopped" else 1


def child(request, reply, stop, registry):
    import url_reader.engine as reader
    settings = json.loads(Path(request).read_text(encoding="utf-8"))
    for key in ("output", "profile"):
        settings[key] = Path(settings[key])
    settings["stop_event"] = FileStopSignal(stop, registry)
    result, code = reader.execute(SimpleNamespace(**settings))
    reader.save_result(reply, {"result": result, "code": code})


if __name__ == "__main__":
    if len(sys.argv) != 6 or sys.argv[1] != "--child":
        raise SystemExit("This is an internal reader worker. Open the localhost URL reader.")
    child(*sys.argv[2:])
