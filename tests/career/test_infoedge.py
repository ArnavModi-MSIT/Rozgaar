import unittest
from unittest.mock import patch

from backend.fetchers import infoedge


def listing(sid, country='India'):
    return {'_source':dict(id=sid,companyId=15578,jobTitle='Software Engineer',jobUrl=f'engineer-noida-{sid}',
                          jobLocationRecord=[dict(country=country,formattedLocation='Noida, India' if country=='India' else 'Dubai, UAE')])}


def page(rows,total,more):
    return dict(code=200,data=dict(data=rows,totalCount=total,hasMoreData=more))


def detail(sid,**extra):
    return dict(id=sid,companyId=15578,longDescription='JD',role='<p>Full engineering responsibilities</p><p>Qualifications: Python</p>',minYrsOfExperience=0,maxYrsOfExperience=1,**extra)


class FakeTransport:
    def __init__(self,replies):self.replies=iter(replies);self.calls=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def request(self,kind,**values):
        self.calls.append((kind,values))
        value=next(self.replies)
        if isinstance(value,Exception):raise value
        return value


class InfoEdgeTests(unittest.TestCase):
    def run_source(self,replies,**kwargs):
        transport=FakeTransport(replies)
        with patch.object(infoedge,'PublicTransport',return_value=transport),patch.object(infoedge.time,'sleep'):
            result=infoedge.collect(**kwargs)
        return result,transport

    def test_offsets_count_foreign_rows_without_importing_them(self):
        result,transport=self.run_source([page([listing(1),listing(2,'United Arab Emirates')],3,True),page([listing(3)],3,False),detail(1),detail(3)])
        self.assertEqual(result.status,'ok')
        self.assertEqual([j['source_id'] for j in result],['1','3'])
        self.assertEqual(transport.calls[:2],[('search',{'offset':0}),('search',{'offset':2})])
        self.assertIn('Qualifications: Python',result[0]['description'])
        self.assertIn('Experience: 0 to 1 years',result[0]['description'])
        self.assertTrue(result[0]['url'].endswith('engineer-noida-1?id=1'))

    def test_role_field_preserves_full_qualifications_beyond_preview_cap(self):
        data=detail(1)
        data['role']='<p>'+'Introduction '*700+'</p><p>Required experience: 5 years</p>'
        text=infoedge._description(data,'1')
        self.assertGreater(len(text),6000)
        self.assertIn('Required experience: 5 years',text)

    def test_wrong_company_or_detail_identity_rejected(self):
        for changes in [{'id':2},{'companyId':99}]:
            data=detail(1);data.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):infoedge._description(data,'1')
        source=listing(1)['_source'];source['companyId']=99
        with self.assertRaises(ValueError):infoedge._listing(source)

    def test_unknown_country_not_relabelled_as_india(self):
        source=listing(1)['_source'];source['jobLocationRecord']=[];source['location']='Remote'
        with self.assertRaises(ValueError):infoedge._listing(source)

    def test_list_preview_never_replaces_missing_detail(self):
        source=listing(1);source['_source']['mediumDescriptionWithoutHtml']='Short preview'
        result,_=self.run_source([page([source],1,False),RuntimeError('HTTP failure')])
        self.assertEqual(result.status,'partial')
        self.assertEqual(result[0]['description'],'')
        self.assertIn('1 full descriptions unavailable',result.error)
        empty=detail(1);empty['role']=''
        with self.assertRaises(ValueError):infoedge._description(empty,'1')
        empty['skillSet']='Python, SQL'
        with self.assertRaises(ValueError):infoedge._description(empty,'1')

    def test_failed_first_page_and_verified_empty_are_different(self):
        with self.assertRaises(RuntimeError):self.run_source([{}])
        result,_=self.run_source([page([],0,False)])
        self.assertEqual(result.status,'ok');self.assertEqual(len(result),0)

    def test_repeated_or_failed_page_preserves_partial_jobs(self):
        for response in [page([listing(1)],3,True),RuntimeError('Network failed')]:
            result,_=self.run_source([page([listing(1)],3,True),response,detail(1)])
            self.assertEqual(len(result),1)
            self.assertEqual(result.status,'partial')

    def test_detail_failures_stop_after_three_and_keep_remaining_listings(self):
        result,transport=self.run_source([page([listing(i) for i in range(1,6)],5,False)]+[RuntimeError('unavailable')]*3)
        self.assertEqual(len(result),5)
        self.assertEqual(len(transport.calls),4)
        self.assertIn('three consecutive',result.error)

    def test_blank_descriptions_do_not_prevent_reading_later_jobs(self):
        blank=[detail(i) for i in range(1,4)]
        for row in blank:row['role']=''
        result,transport=self.run_source([page([listing(i) for i in range(1,5)],4,False)]+blank+[detail(4)])
        self.assertEqual(len(transport.calls),5)
        self.assertTrue(result[-1]['description'])
        self.assertEqual(result.source_counts['missing_descriptions'],3)

    def test_closed_job_is_skipped_but_access_restriction_stops_requests(self):
        result,transport=self.run_source([page([listing(1),listing(2)],2,False),infoedge.PublicRequestError('Closed',404),detail(2)])
        self.assertTrue(result[1]['description'])
        result,transport=self.run_source([page([listing(1),listing(2)],2,False),infoedge.PublicRequestError('Restricted',403)])
        self.assertEqual(len(transport.calls),2)
        self.assertIn('access restricted',result.error)

    def test_deadline_does_not_request_and_source_is_registered(self):
        with self.assertRaises(RuntimeError):self.run_source([],deadline=0)
        from backend.core.collector import PLATFORMS
        import backend.config as config
        self.assertIn('infoedge',dict(PLATFORMS))
        self.assertEqual(config.DISPLAY_NAMES['infoedge'],'Info Edge')
