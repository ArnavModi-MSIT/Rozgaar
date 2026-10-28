"""Local dependency discovery and connection limits; no network calls."""
import unittest
from unittest.mock import MagicMock, Mock, patch

from backend.fetchers import infoedge, smartrecruiters, standard


class TransportSetupTests(unittest.TestCase):
    def test_infoedge_uses_private_runtime_without_pwsh_on_path(self):
        executable = infoedge.ROOT / 'runtime/tools/powershell/pwsh.exe'
        process = Mock(stdout=MagicMock())
        with patch.object(infoedge.shutil, 'which', return_value=None), \
             patch.object(infoedge.Path, 'is_file', lambda path: path == executable), \
             patch.object(infoedge.subprocess, 'Popen', return_value=process) as start:
            with infoedge.PublicTransport():
                pass
        self.assertEqual(start.call_args.args[0][0], str(executable))

    def test_pools_bound_and_reuse_connections_at_worker_capacity(self):
        for module, capacity in [(standard, 16), (smartrecruiters, 40)]:
            with self.subTest(module=module.__name__):
                adapter = module.SESSION.get_adapter('https://example.test/')
                self.assertEqual(adapter._pool_maxsize, capacity)
                self.assertTrue(adapter._pool_block)
