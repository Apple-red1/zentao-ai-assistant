from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

import sys

SHARED = Path(__file__).resolve().parents[3] / "skills" / "_shared"
sys.path.insert(0, str(SHARED))
from zentao.identity_store import IdentityScopedJsonStore, IdentityStoreError, normalize_connection_identity


class IdentityStoreTests(unittest.TestCase):
    def identity(self, account: str = "tester") -> dict[str, str]:
        return {"base_url": "HTTPS://LOCALHOST:443/zentao/", "account": account}

    def payload(self, store: IdentityScopedJsonStore, value: str = "ok") -> dict[str, object]:
        return {"schema_version": 1, "owner": store.identity, "value": value}

    def test_identity_normalization_is_stable_and_secret_free(self):
        self.assertEqual({"base_url": "https://localhost/zentao", "account": "tester"},
                         normalize_connection_identity(self.identity()))
        with self.assertRaises(IdentityStoreError):
            normalize_connection_identity({"base_url": "https://user:password@localhost/zentao", "account": "tester"})

    def test_accounts_are_isolated_and_write_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = IdentityScopedJsonStore(self.identity(), namespace="testing", schema_version=1, root=root)
            second = IdentityScopedJsonStore(self.identity("other"), namespace="testing", schema_version=1, root=root)
            first.replace(self.payload(first))
            second.replace(self.payload(second, "other"))
            self.assertNotEqual(first.path, second.path)
            self.assertEqual("ok", first.read()["value"])
            self.assertEqual("other", second.read()["value"])
            if os.name == "posix":
                self.assertEqual(0o700, stat.S_IMODE(first.directory.stat().st_mode))
                self.assertEqual(0o600, stat.S_IMODE(first.path.stat().st_mode))

    def test_symlink_and_oversize_are_fail_closed(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink is not available")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            os.symlink(target, root / "testing")
            store = IdentityScopedJsonStore(self.identity(), namespace="testing", schema_version=1, root=root)
            with self.assertRaises(IdentityStoreError) as error:
                store.replace(self.payload(store))
            self.assertEqual("UNSAFE", error.exception.code)
        with tempfile.TemporaryDirectory() as directory:
            store = IdentityScopedJsonStore(self.identity(), namespace="testing", schema_version=1,
                                            max_bytes=128, root=Path(directory))
            with self.assertRaises(IdentityStoreError) as error:
                store.replace(self.payload(store, "x" * 1000))
            self.assertEqual("UNSAFE", error.exception.code)
            self.assertFalse(store.path.exists())

    def test_existing_lock_is_not_overwritten_or_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            store = IdentityScopedJsonStore(self.identity(), namespace="testing", schema_version=1, root=Path(directory))
            store._check_parent(create=True)
            store.lock_path.mkdir(mode=0o700)
            with self.assertRaises(IdentityStoreError) as error:
                store.update(lambda _: self.payload(store, "new"))
            self.assertEqual("BUSY", error.exception.code)
            store.lock_path.rmdir()


if __name__ == "__main__":
    unittest.main()
