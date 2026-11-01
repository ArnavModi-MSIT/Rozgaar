import unittest
from unittest.mock import patch
from backend.fetchers import kissht

class KisshtTests(unittest.TestCase):
    def row(self):
        return dict(Company_Name='Kissht',Country_Name='India',ERFCode=1,TrackToken='18a517b3-46df-4c23-927e-c983d056d557',SearchKeyWord='Engineer-1',Position_Name='Engineer',LOCATIONNAME='Mumbai')
    def test_identity_scope_and_public_url(self):
        row=self.row();job=kissht._listing(row)
        self.assertEqual(job['source_id'],'1')
        self.assertIn('/CandidatePortal/',job['url'])
        for key,value in [('Company_Name','Other'),('Country_Name','USA'),('TrackToken','../other')]:
            record=dict(row);record[key]=value
            with self.assertRaises(ValueError):kissht._listing(record)
    def test_full_text_tail_and_short_source_flag(self):
        job=kissht._listing(self.row())
        body='<div class="jobs-content"><h6>Engineer</h6></div><div class="jobs-meta">Kissht</div><div class="description-info"><h4>Job Description</h4>'+('Python '*1200)+'Last requirement</div>'
        text,short=kissht._description(body,job)
        self.assertGreater(len(text),6000)
        self.assertIn('Last requirement',text)
        self.assertFalse(short)
        with self.assertRaises(ValueError):kissht._description('',job)
        text,short=kissht._description(body.replace('Python '*1200,'Brief '),job)
        self.assertTrue(short)
    def test_blocked_first_page_is_not_zero_jobs(self):
        with patch.object(kissht,'get_text',return_value=None),self.assertRaises(RuntimeError):kissht.fetch({})
