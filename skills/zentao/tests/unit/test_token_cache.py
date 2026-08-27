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
    @unittest.skipUnless(os.name == "posix", "POSIX path alias contract")
    def test_default_cache_allows_symlink_above_runtime_scope(self) -> None:
        for scope in ("project", "user"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as td:
                base = Path(td).resolve()
                actual = base / "actual"
                actual.mkdir()
                alias = base / "alias"
                alias.symlink_to(actual, target_is_directory=True)
                root, home = alias / "repo", alias / "home"
                root.mkdir()
                if scope == "project":
                    (root / ".env").write_text("config\n", encoding="utf-8")
                config = Config("https://zentao.example.com", scope, "secret")
                with patch("zentao_skill.internal.config.project_root", return_value=root), patch("pathlib.Path.home", return_value=home), patch.dict(os.environ, {}, clear=True):
                    cache = TokenCache()
                    cache.store(config, "alias-token")
                    self.assertEqual("alias-token", cache.load(config))
                    cache.clear(config)
                    self.assertFalse(cache.path_for(config).exists())

    @unittest.skipUnless(os.name == "posix", "POSIX symlink boundary")
    def test_default_cache_rejects_links_inside_runtime_scope(self) -> None:
        for scope, component in (("project", ".tmp"), ("user", ".zentao-ai-assistant"), ("user", ".zentao-ai-assistant/cache")):
            with self.subTest(scope=scope, component=component), tempfile.TemporaryDirectory() as td:
                base = Path(td).resolve()
                root, home, outside = base / "repo", base / "home", base / "outside"
                root.mkdir()
                outside.mkdir()
                if scope == "project":
                    (root / ".env").write_text("config\n", encoding="utf-8")
                link = (root if scope == "project" else home) / component
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(outside, target_is_directory=True)
                config = Config("https://zentao.example.com", scope, "secret")
                with patch("zentao_skill.internal.config.project_root", return_value=root), patch("pathlib.Path.home", return_value=home), patch.dict(os.environ, {}, clear=True):
                    cache = TokenCache()
                    for action in (lambda: cache.store(config, "token"), lambda: cache.load(config), lambda: cache.clear(config)):
                        with self.assertRaises(ConfigError):
                            action()
                self.assertEqual([], list(outside.iterdir()))

    def test_default_cache_uses_project_runtime_when_project_config_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            home = Path(td) / "home"
            root.mkdir()
            (root / ".env").write_text("config\n", encoding="utf-8")
            config = Config("https://zentao.example.com", "project", "secret")
            with patch("zentao_skill.internal.config.project_root", return_value=root), patch("pathlib.Path.home", return_value=home), patch.dict(os.environ, {}, clear=True):
                cache = TokenCache()
                cache.store(config, "project-token")
                self.assertEqual(root / ".tmp" / "zentao" / "auth", cache.root)
                self.assertEqual("project-token", cache.load(config))

    def test_default_cache_uses_private_user_scope_without_repo_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            home = Path(td) / "home"
            root.mkdir()
            config = Config("https://zentao.example.com", "user", "secret")
            with patch("zentao_skill.internal.config.project_root", return_value=root), patch("pathlib.Path.home", return_value=home), patch.dict(os.environ, {}, clear=True):
                cache = TokenCache()
                cache.store(config, "user-token")
                expected = home / ".zentao-ai-assistant" / "cache" / "auth"
                self.assertEqual(expected, cache.root)
                self.assertTrue(cache.path_for(config).is_file())
                self.assertEqual("user-token", cache.load(config))
                if os.name == "posix":
                    self.assertEqual(0o700, stat.S_IMODE(expected.stat().st_mode))
                    self.assertEqual(0o600, stat.S_IMODE(cache.path_for(config).stat().st_mode))
            self.assertFalse((root / ".tmp" / "zentao" / "auth").exists())

    def test_explicit_nonproject_config_keeps_token_data_in_user_scope(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "repo"
            home = base / "home"
            explicit = base / "ci" / "config.env"
            root.mkdir()
            explicit.parent.mkdir()
            explicit.write_text("ZENTAO_BASE_URL=https://ci.zentao.example.com\n", encoding="utf-8")
            config = Config("https://zentao.example.com", "ci", "secret")
            with patch("zentao_skill.internal.config.project_root", return_value=root), patch("pathlib.Path.home", return_value=home), patch.dict(
                os.environ, {"ZENTAO_CONFIG_FILE": str(explicit)}, clear=True
            ):
                cache = TokenCache()
                cache.store(config, "ci-token")
            self.assertEqual(home / ".zentao-ai-assistant" / "cache" / "auth", cache.root)

    def test_explicit_token_cache_override_wins_in_user_scope(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "repo"
            home = base / "home"
            root.mkdir()
            override = base / "override" / "auth"
            config = Config("https://zentao.example.com", "ci", "secret")
            with patch("zentao_skill.internal.config.project_root", return_value=root), patch("pathlib.Path.home", return_value=home), patch.dict(
                os.environ, {"ZENTAO_TOKEN_CACHE_DIR": str(override)}, clear=True
            ):
                cache = TokenCache()
                cache.store(config, "override-token")
            self.assertEqual(override, cache.root)
            self.assertEqual("override-token", cache.load(config))

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
