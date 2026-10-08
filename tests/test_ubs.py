import unittest
from unittest.mock import patch
from fetchers import ubs
from core.experience import extract_min_experience

class UBSTests(unittest.TestCase):
    def detail(self, sid='1', country='India'):
        fields=[dict(VerityZone='reqid',AnswerValue=sid),dict(VerityZone='formtext23',AnswerValue=country),dict(VerityZone='jobdescription',AnswerValue='<p>Build platforms</p>',QuestionName='Your role',QuestionType='textarea'),dict(VerityZone='formtext59',AnswerValue='<p>4 to 7 years of experience in engineering</p>',QuestionName='Your skills and experience',QuestionType='textarea')]
        return {'ServiceResponse':{'Jobdetails':{'isActive':True,'JobDetailQuestions':fields}}}
    def test_full_requirements(self):
        text=ubs.parse_detail(self.detail(),'1')
        self.assertIn('Build platforms',text)
        self.assertEqual(extract_min_experience(text),4)
    def test_identity(self): self.assertEqual(ubs.parse_detail(self.detail('2'),'1'),'')
    def test_country(self): self.assertEqual(ubs.parse_detail(self.detail(country='Switzerland'),'1'),'')
    def test_inactive(self):
        d=self.detail(); d['ServiceResponse']['Jobdetails']['isActive']=False
        self.assertEqual(ubs.parse_detail(d,'1'),'')
    def test_missing_configuration_fails(self):
        with patch.object(ubs,'get_text',return_value='<html></html>'):
            with self.assertRaises(RuntimeError): ubs.collect()
    def test_deadline(self):
        with self.assertRaises(RuntimeError): ubs.collect(0)

    def test_board_merge_deduplicates(self):
        from fetchers.result import CollectionResult
        with patch.object(ubs,'collect_board',side_effect=[CollectionResult([{'source_id':'1'}]),CollectionResult([{'source_id':'1'},{'source_id':'2'}])]) as call:
            result=ubs.collect()
        self.assertEqual(len(result),2)
        self.assertEqual(call.call_args_list[1].args[:2],(5131,15232))
    def test_one_board_failure_is_partial(self):
        from fetchers.result import CollectionResult
        with patch.object(ubs,'collect_board',side_effect=[RuntimeError('unavailable'),CollectionResult([{'source_id':'2'}])]):
            result=ubs.collect()
        self.assertEqual(result.status,'partial')
        self.assertEqual(len(result),1)

if __name__=='__main__': unittest.main()
