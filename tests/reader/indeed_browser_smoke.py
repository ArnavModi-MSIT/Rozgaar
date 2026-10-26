"""Indeed DOM, identity, filter-preserving pagination and stop fixtures; no real traffic."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from url_reader import engine as reader
from url_reader.sources import indeed

JK1,JK2 = '916b6f8775764ece','0123456789abcdef'
JOB1,JOB2 = [f'https://in.indeed.com/viewjob?jk={key}' for key in (JK1,JK2)]
DESCRIPTION = 'Build Python and SQL pipelines. ' * 250 + 'Final qualification: students may apply.'


def main():
    chrome = Path(os.environ.get('ProgramFiles','/nonexistent'))/'Google/Chrome/Application/chrome.exe'
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(chrome) if chrome.exists() else None,headless=True)
        context = browser.new_context(service_workers='block')
        state = {'missing':False,'redirect':False,'verification':False}
        search_queries = []
        def route(request):
            parts = urlsplit(request.request.url); query = parse_qs(parts.query,keep_blank_values=True)
            assert request.request.method == 'GET'
            if query.get('blocked'):
                request.fulfill(status=403,body='<title>Access Denied</title>'); return
            if parts.path == '/jobs':
                for key in ('q','l','salaryType','radius','sc'):
                    assert key in query,(key,query)
                search_queries.append(query)
                second = query.get('start') == ['10']; jk = JK2 if second else JK1
                body = f'<div class="job_seen_beacon" data-jk="{jk}"><h2 class="jobTitle"><a href="/rc/clk?jk={jk}&from=card">Analyst intern</a></h2></div>'
                body += '<footer><a href="/viewjob?jk=1111111111111111">Footer link must be excluded</a></footer>'
                body += '<button data-testid="pagination-page-next" disabled>Next</button>' if second else '<a data-testid="pagination-page-next" href="/jobs?start=10&pp=cursor">Next Page</a>'
            else:
                jk = query.get('jk',[''])[0]
                body = '<h1 class="jobsearch-JobInfoHeader-title">Data Analyst Intern</h1><div data-testid="inlineHeader-companyName"><a>Fixture Company</a></div><div id="jobLocationText">Dwarka, Delhi</div><div id="salaryInfoAndJobType">₹20,000 per month</div>'
                if state['verification']:
                    body = '<title>Additional Verification Required</title><form id="challenge-form">Verify you are human</form>'
                elif not state['missing']:
                    if jk == JK1:
                        posting = {'@type':'JobPosting','identifier':{'value':JK1},'title':'Data Analyst Intern',
                                   'hiringOrganization':{'name':'Fixture Company'},'description':'<p>'+DESCRIPTION+'</p>',
                                   'datePosted':'2026-10-25','employmentType':'INTERN'}
                        unrelated = dict(posting,identifier={'value':'1111111111111111'},description='Unrelated recommendation '*1000)
                        body += '<div id="jobDescriptionText">Short preview.</div><script type="application/ld+json">'+json.dumps([unrelated,posting])+'</script>'
                    else:
                        body += '<div id="slot"></div><script>setTimeout(()=>document.getElementById("slot").innerHTML='+json.dumps('<div id="jobDescriptionText">'+DESCRIPTION+'</div>')+',750)</script>'
                body += '<button onclick="window.forbidden=true">Apply now</button><button onclick="window.forbidden=true">Save</button>'
                if state['redirect']:
                    body += '<script>history.replaceState(null,"",'+json.dumps('/viewjob?jk='+JK2)+')</script>'
            request.fulfill(content_type='text/html',body=body)
        context.route('**/*',route)
        try:
            page = context.new_page()
            reader.navigate(page,indeed.DEFAULT_SEARCH)
            assert reader.job_links(page) == [JOB1]
            assert reader.next_results(page).status == 'advanced'
            assert reader.job_links(page) == [JOB2]
            assert reader.search_signature(page.url) == reader.search_signature(indeed.DEFAULT_SEARCH)
            assert reader.next_results(page).status == 'verified_last_page'
            first = reader.read_job(page,JOB1)
            assert first['source'] == 'indeed' and first['job_id'] == JK1 and first['company'] == 'Fixture Company'
            assert first['description'] == DESCRIPTION and first['extraction_method'] == 'jobposting_jsonld'
            second = reader.read_job(page,JOB2)
            assert second['description'] == DESCRIPTION and second['extraction_method'] == 'scoped_dom'
            assert not page.evaluate('window.forbidden || false')
            with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
                args = SimpleNamespace(url=indeed.DEFAULT_SEARCH,output=Path(folder)/'indeed.json',limit=2,delay=0,fresh=False)
                result = {'jobs':[],'errors':[]}; reader.prepare_output(args,result,args.url)
                owned = []; detail = reader.DetailReader(context,owned)
                reader.collect_jobs(page,detail,args,result,args.output)
                assert len(result['jobs']) == 2 and {j['job_id'] for j in result['jobs']} == {JK1,JK2},result
                reader.validate_checkpoint(result,indeed.DEFAULT_SEARCH)
                for tab in owned: tab.close()
            state['missing'] = True
            with patch.object(reader,'interruptible_wait'):
                try: reader.read_job(page,JOB1)
                except ValueError as exc: assert 'description was missing' in str(exc)
                else: raise AssertionError('Empty description was saved')
            state['missing'] = False; state['redirect'] = True
            try: reader.read_job(page,JOB1)
            except ValueError as exc: assert 'redirected elsewhere' in str(exc)
            else: raise AssertionError('Wrong posting identity was accepted')
            state['redirect'] = False; state['verification'] = True
            try: reader.read_job(page,JOB1)
            except reader.AccessBlocked: pass
            else: raise AssertionError('Verification was not stopped')
            state['verification'] = False
            try: reader.navigate(page,indeed.DEFAULT_SEARCH+'&blocked=1')
            except reader.AccessBlocked: pass
            else: raise AssertionError('HTTP 403 was not stopped')
            assert any(q.get('start') == ['10'] and q['sc'] == ['0kf:attr(VDTG7);'] for q in search_queries)
            print('Indeed fixtures passed: card/redirect job keys, salary/location/radius/filter preservation, real Next controls, full descriptions, JSON-LD identity, delayed DOM, checkpoint resume validation and access stops. All requests intercepted.')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
