import unittest
from unittest.mock import patch
import config
from fetchers import workday_india

CFG = {"company": "walmart", "tenant": "walmart", "wd_server": "wd504", "site": "WalmartExternal", "title_pattern": config.STUDENT_TITLE_RE}
FACETS = {"jobPostings": [], "facets": [{"facetParameter": "locationCountry", "values": [{"id": "india", "descriptor": "India"}]}]}
def listing(i,title):
    return {"title": title, "externalPath": f"/job/India/{i}", "bulletFields": [str(i)], "locationsText": "Bangalore"}

class WorkdayStudentTests(unittest.TestCase):
    def test_reads_all_pages_before_selecting_and_fetches_selected_description(self):
        rows=[listing(i,"Internal Systems Engineer") for i in range(20)]
        responses=[FACETS,{"total":21,"jobPostings":rows},{"total":0,"jobPostings":[listing(20,"(IND) Grad Intern - No Work Experience")]}]
        with patch.object(workday_india,"post_json",side_effect=responses) as post, patch.object(workday_india,"get_json",return_value={"jobPostingInfo":{"jobDescription":"<p>Currently enrolled in BTech</p>"}}) as detail, patch.object(workday_india.time,"sleep"):
            result=workday_india.fetch(CFG)
        self.assertEqual(result.status,"ok")
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["source_id"],"20")
        self.assertIn("Currently enrolled",result[0]["description"])
        self.assertEqual([c.kwargs["json"]["offset"] for c in post.call_args_list],[0,0,20])
        self.assertEqual(detail.call_count,1)

    def test_complete_nonstudent_board_is_valid_empty(self):
        with patch.object(workday_india,"post_json",side_effect=[FACETS,{"total":1,"jobPostings":[listing(1,"Staff Engineer")]}]),patch.object(workday_india,"get_json") as detail:
            result=workday_india.fetch(CFG)
        self.assertEqual(result.status,"ok")
        self.assertEqual(len(result),0)
        detail.assert_not_called()

    def test_failed_page_is_not_valid_student_empty(self):
        with patch.object(workday_india,"post_json",side_effect=[FACETS,None]):
            with self.assertRaises(RuntimeError):workday_india.fetch(CFG)

    def test_student_titles_are_not_internal_or_graduate_fulltime(self):
        for title in ["Industrial Trainee Program", "Software Co-op", "Research Student", "Software Engineering Internship"]:
            self.assertIsNotNone(config.STUDENT_TITLE_RE.search(title))
        for title in ["Internal Tools Engineer", "Internet Infrastructure", "Graduate Software Engineer"]:
            self.assertIsNone(config.STUDENT_TITLE_RE.search(title))
