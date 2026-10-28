from pathlib import Path
from contextlib import closing
import tempfile,sqlite3,unittest
from unittest.mock import patch
from backend.core.experience import experience_requirements
from backend.core.storage import init_db,save_job
from backend.api import data
from backend.fetchers import workday

class ExportRegressionTests(unittest.TestCase):
    def test_exl_qualification_ranges_and_plus(self):
        for text,value in [("Bachelor's/Master's in any stream 5-8 years",5),("Bachelor's/Master's in Engineering 8+ years",8),('Bachelor Degree or Post Graduate Degree 5 - 8 years',5),('BBA, MBA, CA Intermediate, CMA Intermediate, CS Intermediate) 6 - 12 years',6)]:
            with self.subTest(text=text):self.assertEqual(experience_requirements(text,'Assistant Manager')[0],value)

    def test_role_heading_in_body(self):
        self.assertEqual(experience_requirements('Platform Engineer - 5-8 Years\nProvide Databricks expertise','Platform Engineer')[0],5)
        self.assertEqual(experience_requirements('8+ years in data engineering/ETL roles, with at least 4+ years in Azure cloud ETL leadership.','Data Engineer')[0],8)

    def test_preferred_range_remains_separate(self):
        self.assertEqual(experience_requirements("Preferred Qualifications:\nBachelor's degree 5-8 years",'Engineer'),(None,5))

    def test_months_degree_duration_and_company_age_not_promoted(self):
        for text in ['Graduate in any stream 6 - 12 months experience in insurance','Bachelor degree is a 3-4 years course','Bachelor degree. Company is 8+ years old']:
            with self.subTest(text=text):self.assertIsNone(experience_requirements(text,'Analyst')[0])
        self.assertEqual(experience_requirements("Bachelor's/Master's in any stream 0-1 years",'Analyst')[0],0)

    def test_workday_invalid_cards_are_not_jobs(self):
        cfg=dict(company='medtronic',tenant='medtronic',wd_server='wd1',site='MedtronicCareers')
        rows=[dict(title='',externalPath='',bulletFields=['R1']),dict(title='Engineer',externalPath='',bulletFields=['R2']),dict(title='Engineer',externalPath='/job/Delhi/Engineer_R3',bulletFields=['R3'],locationsText='Delhi, India')]
        with patch.object(workday,'_post',return_value=dict(total=3,jobPostings=rows)):
            jobs=workday.fetch_workday(cfg)
        self.assertEqual(len(jobs),1);self.assertEqual(jobs[0]['source_id'],'R3');self.assertEqual(jobs.status,'partial')

    def test_existing_blank_titles_hidden_without_losing_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'jobs.db'
            with closing(sqlite3.connect(db)) as conn:
                init_db(conn)
                for id,title in [('bad',''),('good','Engineer')]:
                    save_job(conn,id,dict(company='medtronic',title=title,location='India',url='https://example.com',description=''), 'workday')
                conn.commit()
            with patch.object(data,'DB_PATH',db):self.assertEqual(set(data._load_jobs_df()['id']),{'good'})
            with closing(sqlite3.connect(db)) as conn:self.assertEqual(conn.execute('select count(*) from jobs').fetchone()[0],2)
