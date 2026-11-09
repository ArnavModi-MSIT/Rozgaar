import unittest

from backend.config import sources
from backend.fetchers.workday import workday_base


class WorkdayHostTests(unittest.TestCase):
    def test_base_with_and_without_server_number(self):
        self.assertEqual(workday_base("cmegroup", "wd1"), "https://cmegroup.wd1.myworkdayjobs.com")
        self.assertEqual(workday_base("nxp", ""), "https://nxp.myworkdayjobs.com")
        self.assertEqual(workday_base("nxp"), "https://nxp.myworkdayjobs.com")

    def test_nxp_uses_hostless_server(self):
        row = next(c for c in sources.WORKDAY_INDIA if c["company"] == "nxp")
        self.assertEqual(row["wd_server"], "")
        self.assertEqual(workday_base(row["tenant"], row["wd_server"]), "https://nxp.myworkdayjobs.com")


if __name__ == "__main__":
    unittest.main()
