import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import url_reader.engine as reader
import url_reader.supervisor as supervised_reader

JOB = "https://www.linkedin.com/jobs/view/123/"
NEXT = "https://www.linkedin.com/jobs/view/456/"


class StallRecoveryTests(unittest.TestCase):
    def test_navigation_timeout_does_not_query_stuck_dom(self):
        page = Mock(url=JOB)
        page.goto.side_effect = reader.PlaywrightTimeoutError("navigation stalled")
        with patch.object(reader, "check_access") as access, self.assertRaises(reader.TransientReadError):
            reader.navigate_page(page, JOB)
        access.assert_not_called()
        page.wait_for_load_state.assert_not_called()
        self.assertEqual(page.goto.call_args.kwargs["timeout"], 15000)

    def test_search_timeout_resets_loading_then_retries_same_filters(self):
        page = Mock()
        with patch.object(reader, "navigate_page", side_effect=[reader.TransientReadError("stalled"), "loaded"]) as navigate:
            self.assertEqual(reader.navigate(page, reader.DEFAULT_SEARCH), "loaded")
        self.assertEqual(navigate.call_count, 2)
        self.assertEqual(navigate.call_args.args[1], reader.DEFAULT_SEARCH)
        page.goto.assert_called_once_with("about:blank", wait_until="commit", timeout=5000)

    def test_detail_retry_replaces_stuck_tab_and_keeps_original_tab(self):
        original, stuck, fresh = Mock(), Mock(), Mock()
        for page in (original, stuck, fresh):
            page.is_closed.return_value = False
        context = Mock()
        context.new_page.side_effect = [stuck, fresh]
        owned = []
        detail = reader.DetailReader(context, owned)
        with patch.object(reader, "read_job", side_effect=[reader.TransientReadError("stalled"), {"link": JOB, "description": "Full text"}]), patch.object(reader, "interruptible_wait"):
            result = {}
            record = reader.read_with_retry(detail, JOB, SimpleNamespace(retries=1), result, Mock())
        self.assertEqual(record["extraction_attempts"], 2)
        self.assertEqual(result["retried"], 1)
        self.assertEqual(owned, [stuck, fresh])
        stuck.close.assert_called_once()
        original.close.assert_not_called()

    def test_owned_tab_registry_contains_only_reader_created_target(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            registry = Path(folder)/"targets"
            page = Mock()
            session = page.context.new_cdp_session.return_value
            session.send.return_value = {"targetInfo": {"targetId": "owned-123"}}
            owned = reader.OwnedPages(registry)
            owned.append(page)
            self.assertEqual(registry.read_text(), "owned-123\n")
            session.detach.assert_called_once()

    def test_cleanup_closes_only_registered_targets_on_loopback(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            registry = Path(folder)/"targets"
            registry.write_text("owned-123\nowned-123\n../unrelated\n", encoding="utf-8")
            with patch.object(supervised_reader, "urlopen") as open_url:
                open_url.return_value.__enter__.return_value.read.return_value = '[{"id":"owned-123"},{"id":"user-original"}]'
                supervised_reader.close_owned_targets("http://127.0.0.1:9222", registry)
                self.assertEqual(open_url.call_count, 2)
                self.assertEqual(open_url.call_args.args[0], "http://127.0.0.1:9222/json/close/owned-123")
            with patch.object(supervised_reader, "urlopen") as open_url:
                supervised_reader.close_owned_targets("https://example.com", registry)
                open_url.assert_not_called()


CHILD_FIXTURE = '''import json, pathlib, sys, time
request, reply, stop, registry, mode, counter = sys.argv[1:]
settings=json.loads(pathlib.Path(request).read_text())
path=pathlib.Path(settings['output'])
counter=pathlib.Path(counter)
attempt=int(counter.read_text())+1 if counter.exists() else 1
counter.write_text(str(attempt))
result=json.loads(path.read_text())
if mode=='recover' and attempt==2:
    assert settings['fresh'] is False
    assert len(result['jobs'])==1 and result['progress']['pending_links']
    result['jobs'].append({'link':'https://www.linkedin.com/jobs/view/456/','description':'Second full description'})
    result['progress']['pending_links']=[]
    result['status']='completed'
    path.write_text(json.dumps(result))
    pathlib.Path(reply).write_text(json.dumps({'result':result,'code':0}))
elif mode=='blocked':
    result.update(status='blocked',stop_reason='Manual verification required')
    pathlib.Path(reply).write_text(json.dumps({'result':result,'code':1}))
else:
    time.sleep(30)
'''


class SupervisorTests(unittest.TestCase):
    def run_fixture(self, mode, *, stop=False, recoveries=1):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            folder = Path(folder)
            helper = folder/"child.py"
            helper.write_text(CHILD_FIXTURE, encoding="utf-8")
            args = SimpleNamespace(output=folder/"jobs.json", url=reader.DEFAULT_SEARCH,
                                   profile=folder/"profile", limit=2, delay=0, fresh=True,
                                   stop_event=threading.Event(), cdp="http://127.0.0.1:1")
            value = {"jobs": [], "errors": []}
            reader.prepare_output(args, value, reader.search_url(args.url))
            value["jobs"] = [{"link": JOB, "description": "Original full description"}]
            value["progress"].update(pending_links=[NEXT], attempted_links=[JOB])
            reader.save_result(args.output, value)
            counter = folder/"counter"
            def command(request, reply, stop_path, registry):
                return [sys.executable, str(helper), str(request), str(reply), str(stop_path), str(registry), mode, str(counter)]
            timer = threading.Timer(0.3, args.stop_event.set) if stop else None
            if timer:
                timer.start()
            started = time.monotonic()
            try:
                result, code = supervised_reader.execute(args, idle_timeout=0.7, stop_grace=0.2, recovery_limit=recoveries, command_factory=command)
            finally:
                if timer:
                    timer.cancel()
            self.assertLess(time.monotonic()-started, 6)
            self.assertEqual(result["jobs"][0]["description"], "Original full description")
            return result, code, int(counter.read_text())

    def test_hung_child_is_replaced_and_checkpoint_resumed(self):
        result, code, attempts = self.run_fixture("recover")
        self.assertEqual((result["status"], code, attempts), ("completed", 0, 2))
        self.assertEqual(result["browser_recoveries"], 1)
        self.assertEqual(len(result["jobs"]), 2)

    def test_repeated_hang_stops_with_pending_work_preserved(self):
        result, code, attempts = self.run_fixture("hang")
        self.assertEqual((result["status"], code, attempts), ("partial", 1, 2))
        self.assertEqual(result["progress"]["pending_links"], [NEXT])

    def test_stop_interrupts_unresponsive_child_without_waiting_forever(self):
        result, code, attempts = self.run_fixture("hang", stop=True)
        self.assertEqual((result["status"], code, attempts), ("interrupted", 130, 1))
        self.assertEqual(result["progress"]["pending_links"], [NEXT])

    def test_login_block_does_not_restart_or_bypass(self):
        result, code, attempts = self.run_fixture("blocked")
        self.assertEqual((result["status"], code, attempts), ("blocked", 1, 1))


if __name__ == "__main__":
    unittest.main()
