from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zentao_skill.internal.config import Config
from zentao_skill.internal.errors import ConfigError, HttpFailure
from zentao_skill.internal.token_cache import TokenCache
from zentao_skill.internal.zentao.session import ZentaoSession


class RecordingHttp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str], object]] = []
        self.business_attempts = 0

    def request(self, method: str, url: str, *, headers=None, json_body=None, multipart=None):
        self.calls.append((method, url, dict(headers or {}), json_body))
        if url.endswith('/users/login'):
            return {'status': 'success', 'token': 'fresh-token'}
        self.business_attempts += 1
        if self.business_attempts == 1:
            raise HttpFailure(401, {'error': 'expired'})
        return {'bugs': [], 'pager': {'pageID': 1, 'recPerPage': 100, 'total': 0}}


class TokenCacheTests(unittest.TestCase):
    def test_cache_round_trip_is_private_scoped_and_contains_no_password(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache = TokenCache(root=root, ttl_seconds=3600)
            config = Config('https://zentao.example.com', 'alice', 'super-secret')
            cache.store(config, 'token-value')
            path = cache.path_for(config)
            self.assertTrue(path.is_file())
            payload = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual('token-value', payload['token'])
            self.assertNotIn('super-secret', path.read_text(encoding='utf-8'))
            self.assertEqual('token-value', cache.load(config))
            if os.name == 'posix':
                self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
                self.assertEqual(0o700, stat.S_IMODE(path.parent.stat().st_mode))



    @unittest.skipUnless(hasattr(os, 'symlink'), 'symlink unavailable')
    def test_cache_root_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            target = base / 'target'
            target.mkdir()
            link = base / 'auth-link'
            link.symlink_to(target, target_is_directory=True)
            cache = TokenCache(root=link, ttl_seconds=3600)
            config = Config('https://zentao.example.com', 'alice', 'secret')
            with self.assertRaises(ConfigError):
                cache.store(config, 'token-value')

    @unittest.skipUnless(os.name == 'posix', 'POSIX permission contract')
    def test_insecure_cache_permissions_are_rejected_before_read(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache = TokenCache(root=root, ttl_seconds=3600)
            config = Config('https://zentao.example.com', 'alice', 'secret')
            cache.store(config, 'token-value')
            cache.path_for(config).chmod(0o644)
            with self.assertRaises(ConfigError):
                cache.load(config)

    def test_expired_cache_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache = TokenCache(root=root, ttl_seconds=1)
            config = Config('https://zentao.example.com', 'alice', 'secret')
            with patch('zentao_skill.internal.token_cache.time.time', return_value=100):
                cache.store(config, 'old-token')
            with patch('zentao_skill.internal.token_cache.time.time', return_value=102):
                self.assertIsNone(cache.load(config))
            self.assertFalse(cache.path_for(config).exists())

    def test_cached_token_401_refreshes_once_and_updates_cache(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            config = Config('https://zentao.example.com', 'alice', 'secret')
            cache = TokenCache(root=Path(td), ttl_seconds=3600)
            cache.store(config, 'cached-token')
            http = RecordingHttp()
            session = ZentaoSession(config, http=http, token_cache=cache, retry_delays=(0, 0))
            result = session.get('/products/1/bugs')
            self.assertEqual([], result['bugs'])
            self.assertEqual('fresh-token', cache.load(config))
            login_calls = [call for call in http.calls if call[1].endswith('/users/login')]
            self.assertEqual(1, len(login_calls))
            business_calls = [call for call in http.calls if not call[1].endswith('/users/login')]
            self.assertEqual(['cached-token', 'fresh-token'], [call[2].get('Token') for call in business_calls])


if __name__ == '__main__':
    unittest.main()
