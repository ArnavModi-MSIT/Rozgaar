import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.reset_wellfound import reset
from url_reader.storage.history import SeenPostings


class WellfoundResetTests(unittest.TestCase):
    def test_reset_clears_both_stores_and_checkpoints_but_keeps_other_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); data = root/'data'; data.mkdir()
            wf = {'source':'wellfound','search_url':'https://wellfound.com/jobs','jobs':[
                {'link':'https://wellfound.com/jobs/12345-fixture','title':'Intern','description':'Full description.'}]}
            other = {'search_url':'https://www.linkedin.com/jobs/search/','jobs':[
                {'link':'https://www.linkedin.com/jobs/view/98765/','title':'Analyst','description':'Another full description.'}]}
            (data/'wellfound_test.json').write_text(json.dumps(wf))
            other_path = data/'jobs_other.json'; other_path.write_text(json.dumps(other)); original = other_path.read_bytes()
            for name in ['seen_postings.sqlite3','url_reader.storage.history.sqlite3']:
                with SeenPostings(data/name) as store:
                    store.import_directory(data)
                    self.assertTrue(store.was_seen(wf['jobs'][0]['link']))
            report = reset(data, root/'backup', apply=True)
            self.assertTrue(report['applied'])
            self.assertFalse((data/'wellfound_test.json').exists())
            self.assertEqual(other_path.read_bytes(), original)
            for name in report['seen_rows']:
                with SeenPostings(data/name) as store:
                    store.import_directory(data)
                    self.assertFalse(store.was_seen(wf['jobs'][0]['link']))
                    self.assertTrue(store.was_seen(other['jobs'][0]['link']))
                self.assertTrue((root/'backup'/name).exists())

    def test_dry_run_keeps_data_and_cannot_back_up_into_import_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)/'data'; data.mkdir()
            path = data/'wellfound_empty.json'; path.write_text('{"jobs":[]}')
            self.assertFalse(reset(data, Path(folder)/'backup')['applied'])
            self.assertTrue(path.exists())
            with self.assertRaises(ValueError):
                reset(data, data/'backup', apply=True)


if __name__ == '__main__':
    unittest.main()
