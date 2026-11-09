import unittest
from unittest.mock import patch

from backend.fetchers import successfactors as sf

WIPRO_PAGE = """
<span itemprop="title">EDI Sterling Integrator</span>
<span itemprop="description">Wipro Limited (NYSE: WIT, BSE: 507685) is a leading technology services company.</span>
<span itemprop="description"><p>Role Purpose</p><p>Support process delivery and resolve client queries.</p></span>
<span itemprop="description">Mandatory Skills: EDI. Experience: 5-8 Years.</span>
"""
SINGLE_BLOCK = '<div data-careersite-propertyid="description" itemprop="description"><p>Real role text.</p></div>'


class DescriptionSelectionTests(unittest.TestCase):
    def fetch(self, html):
        with patch.object(sf, "get_text", return_value=html):
            return sf.fetch_job_description("careers.example.com", "/job/x/1")

    def test_wipro_joins_real_blocks_and_drops_company_boilerplate(self):
        text = self.fetch(WIPRO_PAGE)
        self.assertIn("Support process delivery", text)
        self.assertIn("Experience: 5-8 Years", text)
        self.assertNotIn("NYSE: WIT", text)

    def test_boilerplate_only_page_gives_no_description(self):
        page = '<span itemprop="description">Wipro Limited (NYSE: WIT) is a company.</span>'
        self.assertEqual(self.fetch(page), "")

    def test_single_block_tenants_unchanged(self):
        self.assertEqual(self.fetch(SINGLE_BLOCK), "Real role text.")

    def test_itemprop_only_single_block(self):
        self.assertEqual(self.fetch('<span itemprop="description">Only text.</span>'), "Only text.")

    def test_missing_page_or_element_is_empty(self):
        self.assertEqual(self.fetch(None), "")
        self.assertEqual(self.fetch("<p>nothing</p>"), "")


class DeadlineTests(unittest.TestCase):
    CFG = dict(company="wipro", host="careers.wipro.com", variant="rmk", category_id=0, fetch_details=True)
    PAGE = {"jobSearchResult": [{"response": {"id": str(i), "unifiedStandardTitle": "Dev", "urlTitle": "Dev"}} for i in range(3)]}

    def run_rmk(self, deadline, expires_after_listing=False):
        state = {"listing_done": False}

        def clock():
            # time.monotonic is process-wide (the thread pool calls it too), so
            # expiry is keyed to "listing finished", not to a call count.
            return deadline + 1 if (expires_after_listing and state["listing_done"]) else 0

        class Resp:
            def __init__(self, data): self.data = data
            def raise_for_status(self): pass
            def json(self): return self.data

        def post(*args, **kwargs):
            # A page shorter than RMK_PAGE_SIZE is the last one, so the listing
            # is finished as soon as it has been served.
            state["listing_done"] = True
            return Resp(self.PAGE)

        with patch.object(sf.SESSION, "post", side_effect=post), \
             patch.object(sf, "fetch_job_description", return_value="Full JD") as detail, \
             patch.object(sf.time, "sleep"), \
             patch.object(sf.time, "monotonic", side_effect=clock):
            return sf.fetch_successfactors_rmk(dict(self.CFG), deadline=deadline), detail

    def test_expired_budget_marks_partial_and_names_the_count(self):
        with self.assertLogs("jobbot", level="WARNING") as logs:
            result, detail = self.run_rmk(deadline=100, expires_after_listing=True)
        self.assertEqual(result.status, "partial")
        self.assertIn("3 of 3", result.error)
        self.assertTrue(any("not fetched" in line for line in logs.output))

    def test_enough_budget_is_ok(self):
        result, _ = self.run_rmk(deadline=100)
        self.assertEqual(getattr(result, "status", "ok"), "ok")
        self.assertTrue(all(j["description"] == "Full JD" for j in result))

    def test_collect_propagates_partial(self):
        with patch.object(sf, "fetch_successfactors_rmk",
                          return_value=sf.CollectionResult([{"x": 1}], status="partial", error="wipro: 3 of 3")):
            out = sf.collect([dict(self.CFG)])
        self.assertEqual(out.status, "partial")
        self.assertIn("wipro", out.error)
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
