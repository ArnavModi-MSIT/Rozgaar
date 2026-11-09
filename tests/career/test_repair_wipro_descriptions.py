import sqlite3
import unittest

from scripts.career import repair_wipro_descriptions as repair


class BrokenRowSelectionTests(unittest.TestCase):
    def test_selects_only_empty_or_boilerplate_wipro_rows(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE jobs (id TEXT, company TEXT, url TEXT, description TEXT)")
        conn.executemany("INSERT INTO jobs VALUES (?,?,?,?)", [
            ("empty", "wipro", "https://careers.wipro.com/job/a/1-en_US", ""),
            ("null", "wipro", "https://careers.wipro.com/job/b/2-en_US", None),
            ("boiler", "wipro", "https://careers.wipro.com/job/c/3-en_US", "Wipro Limited (NYSE: WIT, BSE: 507685) is a company."),
            ("good", "wipro", "https://careers.wipro.com/job/d/4-en_US", "Role Purpose: support delivery. Experience: 5-8 Years"),
            ("other", "hcltech", "https://example.com/job/5", ""),
        ])
        self.assertEqual({jid for jid, _ in repair.broken_rows(conn)}, {"empty", "null", "boiler"})


if __name__ == "__main__":
    unittest.main()
