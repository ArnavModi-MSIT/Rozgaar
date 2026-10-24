import unittest
from scripts.release_check import private_path, scan_bytes


class ReleaseCheckTests(unittest.TestCase):
    def test_private_artifacts_are_not_source(self):
        for name in ('runtime/career/jobs.db', '.archive/old/source.py', 'jobs.db-wal',
                     'resume.pdf', '.env.production', 'browser/Login Data', 'career-pages-test.json'):
            self.assertTrue(private_path(name), name)
        for name in ('backend/core/storage.py', 'examples/matcher_synthetic.json', '.env.example'):
            self.assertFalse(private_path(name), name)

    def test_token_findings_never_include_the_value(self):
        token = b'gh' + b'p_' + b'x' * 36
        findings = scan_bytes(token, 'example.txt')
        self.assertEqual(findings, [{'location':'example.txt', 'rule':'github_token'}])
        self.assertNotIn(token.decode(), str(findings))


if __name__ == '__main__':
    unittest.main()
