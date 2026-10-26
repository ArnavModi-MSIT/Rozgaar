import argparse
import tempfile
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlsplit

from url_reader import engine as reader, dashboard
from url_reader.sources import indeed
from url_reader.identity import canonical_job_url, posting_key, source_for_url
from url_reader.storage.history import SeenPostings

JK = '916b6f8775764ece'
JOB = 'https://in.indeed.com/viewjob?jk='+JK


class IndeedTests(unittest.TestCase):
    def test_supplied_filters_are_preserved_and_only_cursor_selection_removed(self):
        value = indeed.DEFAULT_SEARCH+'&start=20&pp=cursor&vjk='+JK+'&from=searchOnDesktopSerp'
        query = parse_qs(urlsplit(reader.search_url(value)).query,keep_blank_values=True)
        self.assertEqual(query,{'q':[''],'l':['dwarka, delhi, delhi'],'salaryType':['₹2,40,000'],
                                'radius':['25'],'sc':['0kf:attr(VDTG7);']})
        self.assertEqual(reader.search_signature(value),reader.search_signature(indeed.DEFAULT_SEARCH))
        self.assertNotEqual(reader.search_signature(value),reader.search_signature(value.replace('radius=25','radius=50')))

    def test_repeated_and_blank_filter_values_are_retained(self):
        value = 'https://in.indeed.com/jobs?q=C%2B%2B&sc=first&sc=second&empty='
        self.assertEqual(parse_qs(urlsplit(indeed.search_url(value)).query,keep_blank_values=True),
                         {'q':['C++'],'sc':['first','second'],'empty':['']})

    def test_strict_posting_keys_and_tracking_links(self):
        for path in ('viewjob','rc/clk','pagead/clk'):
            url = 'https://in.indeed.com/'+path+'?jk='+JK+'&from=tracking'
            self.assertEqual(posting_key(url),('indeed',JK))
            self.assertEqual(canonical_job_url(url),JOB)
        for url in (JOB.replace('https:','http:'),JOB.replace('in.indeed.com','in.indeed.com.evil'),
                    JOB.replace(JK,'abc'),JOB+'&jk=1234567890abcdef',indeed.DEFAULT_SEARCH+'&vjk='+JK):
            self.assertIsNone(posting_key(url))

    def test_search_rejects_credentials_untrusted_hosts_and_detail_urls(self):
        for value in (JOB,'http://in.indeed.com/jobs','https://user:pass@in.indeed.com/jobs',
                      'https://in.indeed.com.evil/jobs','https://in.indeed.com:444/jobs',
                      'https://secure.indeed.com/account/login','https://in.indeed.com:bad/jobs'):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                indeed.search_url(value)

    def test_real_next_link_restores_omitted_filters_and_retains_offset(self):
        target = indeed.filtered_next_url(indeed.DEFAULT_SEARCH,'/jobs?start=10&pp=cursor')
        query = parse_qs(urlsplit(target).query,keep_blank_values=True)
        self.assertEqual(query['start'],['10'])
        self.assertEqual(query['pp'],['cursor'])
        self.assertEqual(query['salaryType'],['₹2,40,000'])
        self.assertEqual(reader.search_signature(target),reader.search_signature(indeed.DEFAULT_SEARCH))
        for href in ('/jobs?radius=50&start=10','https://example.com/jobs?start=10','https://indeed.com/jobs?start=10'):
            with self.assertRaises((ValueError,argparse.ArgumentTypeError)):
                indeed.filtered_next_url(indeed.DEFAULT_SEARCH,href)

    def test_output_history_and_dashboard_use_indeed_namespace(self):
        self.assertTrue(reader.daily_output_path(indeed.DEFAULT_SEARCH).name.startswith('indeed_'))
        self.assertEqual(dashboard.source_name(indeed.DEFAULT_SEARCH),'indeed')
        self.assertEqual(source_for_url(JOB),'indeed')
        with tempfile.TemporaryDirectory() as folder, SeenPostings(Path(folder)/'history.sqlite3') as history:
            history.remember({'link':JOB,'title':'Analyst','description':'Full responsibilities.'},'indeed.json')
            self.assertTrue(history.was_seen(JOB))
            self.assertFalse(history.was_seen('https://wellfound.com/jobs/916'))


if __name__ == '__main__':
    unittest.main()
