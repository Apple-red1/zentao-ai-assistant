from __future__ import annotations

import unittest
from types import SimpleNamespace

from zentao_skill.internal.errors import UsageError
from zentao_skill.public.client import ZentaoClient


class FakeBugService:
    def __init__(self) -> None:
        self.pages: list[int] = []

    def list_product(self, *, product, page=None, per_page=None, browse=None, **kwargs):
        self.pages.append(page)
        rows = {
            1: [{'id': 1, 'status': 'active'}, {'id': 2, 'status': 'resolved'}],
            2: [{'id': 3, 'status': 'closed'}],
        }.get(page, [])
        return {'bugs': rows, 'pager': {'pageID': page, 'recPerPage': per_page, 'total': 3}}


class FakeServices:
    def __init__(self) -> None:
        self.bug = FakeBugService()


class PublicClientTests(unittest.TestCase):
    def test_connection_identity_is_canonical_without_secrets(self):
        config = SimpleNamespace(base_url='HTTP://LOCALHOST:80/zentao/', account='admin', password='secret')
        client = ZentaoClient(services=SimpleNamespace(session=SimpleNamespace(config=config)))
        self.assertEqual({'base_url': 'http://localhost/zentao', 'account': 'admin'}, client.connection_identity)
        for base in ('http://user:secret@localhost', 'http://localhost/?token=secret', 'http://localhost/#secret'):
            config.base_url = base
            with self.assertRaises(UsageError):
                _ = client.connection_identity

    def test_partial_opt_in_keeps_prior_pages_without_changing_default_error(self):
        services = FakeServices()
        original = services.bug.list_product
        def fail(**kwargs):
            if kwargs['page'] == 2:
                raise RuntimeError('secret must not be echoed')
            return original(**kwargs)
        services.bug.list_product = fail
        client = ZentaoClient(services=services)
        with self.assertRaises(RuntimeError):
            client.list_all('bug', scope='product', scope_id=7, per_page=2)
        result = client.list_all('bug', scope='product', scope_id=7, per_page=2, preserve_partial=True)
        self.assertEqual([1, 2], [b['id'] for b in result.items])
        self.assertFalse(result.complete)
        self.assertEqual(1, result.pages)
        self.assertEqual(2, result.partial_failures[0]['page'])
        self.assertNotIn('secret', str(result.partial_failures))

    def test_partial_mode_rejects_invalid_or_changing_pager_totals(self):
        for total in (True, -1, 0, 'invalid'):
            with self.subTest(total=total):
                services = FakeServices()
                services.bug.list_product = lambda **kw: {'bugs': [{'id': 1}], 'pager': {'total': total}}
                result = ZentaoClient(services=services).list_all(
                    'bug', scope='product', scope_id=7, per_page=2, preserve_partial=True)
                self.assertFalse(result.complete)
                self.assertEqual('PAGINATION_INVALID', result.partial_failures[0]['code'])
        services.bug.list_product = lambda **kw: {
            'bugs': [{'id': kw['page']}], 'pager': {'total': 2 if kw['page'] == 1 else 3}}
        result = ZentaoClient(services=services).list_all(
            'bug', scope='product', scope_id=7, per_page=1, preserve_partial=True)
        self.assertFalse(result.complete)
        self.assertEqual([1, 2], [b['id'] for b in result.items])
        self.assertEqual('PAGINATION_TOTAL_CHANGED', result.partial_failures[0]['code'])

    def test_list_all_reuses_one_service_and_fetches_until_pager_total(self) -> None:
        services = FakeServices()
        client = ZentaoClient(services=services)
        result = client.list_all('bug', scope='product', scope_id=7, per_page=2)
        self.assertEqual([1, 2, 3], [row['id'] for row in result.items])
        self.assertEqual([1, 2], services.bug.pages)
        self.assertTrue(result.complete)
        self.assertEqual(2, result.pages)

    def test_invalid_resource_scope_is_rejected_before_service_call(self) -> None:
        client = ZentaoClient(services=FakeServices())
        with self.assertRaises(UsageError):
            client.list_all('task', scope='product', scope_id=1)


    def test_repeated_page_is_partial_instead_of_false_complete(self) -> None:
        services = FakeServices()
        services.bug.list_product = lambda **kwargs: {
            'bugs': [{'id': 1}, {'id': 2}],
            'pager': {'pageID': kwargs['page'], 'recPerPage': kwargs['per_page'], 'total': 3},
        }
        result = ZentaoClient(services=services).list_all('bug', scope='product', scope_id=7, per_page=2)
        self.assertFalse(result.complete)
        self.assertEqual('PAGINATION_STALLED', result.partial_failures[0]['code'])

    def test_programmatic_facade_rejects_write_actions(self) -> None:
        client = ZentaoClient(services=FakeServices())
        with self.assertRaises(UsageError):
            client.call('bug', 'delete', item_id=1)


if __name__ == '__main__':
    unittest.main()
