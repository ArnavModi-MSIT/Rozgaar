import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import url_reader.dashboard as dashboard
import url_reader.engine as reader
import url_reader.sources.wellfound as wellfound
import url_reader.browser.wellfound_session as wellfound_session

SEARCH = wellfound.DEFAULT_SEARCH
STATE = {"mode": "open_filtered_tab", "url": SEARCH, "header_text": "Delhi | Internship | 0-1 years",
         "fingerprint": "a" * 64, "result_count": 289, "inputs": [], "tabs": []}


class WellfoundSessionTests(unittest.TestCase):
    def test_counts_do_not_change_filter_fingerprint(self):
        page = Mock(url=SEARCH)
        data = {key: STATE[key] for key in ("header_text", "inputs", "tabs", "result_count")}
        page.evaluate.side_effect = [dict(data), dict(data, result_count=288)]
        with patch.object(reader, "check_access"):
            first, second = wellfound_session.capture(page), wellfound_session.capture(page)
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertNotEqual(first["result_count"], second["result_count"])

    def test_scope_filenames_separate_same_url_filters_and_public_results(self):
        public = reader.daily_output_path(SEARCH)
        delhi = reader.daily_output_path(SEARCH, scope_key=STATE["fingerprint"])
        bengaluru = reader.daily_output_path(SEARCH, scope_key="b" * 64)
        self.assertEqual(len({public.name, delhi.name, bengaluru.name}), 3)

    def test_scope_checkpoint_rejects_changed_filters_without_overwrite(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            args = SimpleNamespace(output=Path(folder)/"scope.json", fresh=False, limit=10, search_state=STATE)
            result = {"jobs": [], "errors": []}
            reader.prepare_output(args, result, SEARCH)
            original = args.output.read_bytes()
            args.search_state = dict(STATE, fingerprint="b" * 64)
            with self.assertRaisesRegex(ValueError, "different Wellfound browser filters"):
                reader.prepare_output(args, {}, SEARCH)
            self.assertEqual(args.output.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, "different Wellfound browser filters"):
                reader.validate_checkpoint(result, SEARCH)

    def test_missing_selected_tab_never_opens_a_fallback(self):
        context = Mock(pages=[])
        with self.assertRaisesRegex(reader.BrowserStopped, "no longer open"):
            wellfound_session.find_page(context, "target", STATE)
        context.new_page.assert_not_called()

    def test_changed_selected_tab_stops_without_navigation(self):
        page = Mock(url=SEARCH)
        with patch.object(wellfound_session, "target_id", return_value="selected"), patch.object(wellfound_session, "capture", return_value=dict(STATE, fingerprint="b"*64)):
            with self.assertRaisesRegex(reader.BrowserStopped, "filters changed"):
                wellfound_session.find_page(SimpleNamespace(pages=[page]), "selected", STATE)
        page.goto.assert_not_called()

    def test_live_filter_change_stops_while_public_personalised_page_is_rejected(self):
        page = Mock()
        page._wellfound_search_state = STATE
        with patch.object(wellfound_session, "capture", return_value=dict(STATE, fingerprint="b"*64)), self.assertRaisesRegex(reader.BrowserStopped, "filters changed"):
            wellfound.verify_search_state(page)
        page = Mock()
        page.locator.return_value.all_inner_texts.return_value = ["Search for jobs"]
        with self.assertRaisesRegex(reader.BrowserStopped, "browser state"):
            wellfound.verify_search_state(page)

    def test_manager_captures_filters_before_selecting_output(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            stop = threading.Event()
            def execute(args):
                stop.wait(2)
                return {"status": "interrupted"}, 130
            manager = dashboard.Manager(folder, execute=execute, bootstrap=lambda: None)
            try:
                with patch.object(wellfound_session, "inspect", return_value={"target": "chosen", "state": STATE}):
                    manager.start({"url": SEARCH, "limit": 10, "delay": 1, "workers": 3, "wellfound_live": True})
                self.assertEqual(manager.args.wellfound_target, "chosen")
                self.assertEqual(manager.args.search_state, STATE)
                self.assertEqual(manager.args.output.name, reader.daily_output_path(SEARCH, scope_key=STATE["fingerprint"]).name)
                self.assertTrue(manager.settings()["wellfound_live"])
            finally:
                stop.set()
                if manager.thread:
                    manager.thread.join(3)


if __name__ == "__main__":
    unittest.main()
