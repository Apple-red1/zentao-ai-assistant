"""Shared data pipeline for team Bug lists and daily reports."""
from __future__ import annotations

from datetime import date, datetime, timezone

from zentao.identity import resolve_user
from team_config import TeamError, valid_account


def read_list(client, resource, **kwargs):
    result = client.list_all(resource, preserve_partial=True, **kwargs)
    context = {'resource': resource}
    if kwargs.get('scope'):
        context['scope'] = f"{kwargs['scope']}:{kwargs['scope_id']}"
    if resource == 'user':
        context['browse'] = kwargs['browse']
    failures = [dict(item, **context) for item in result.partial_failures]
    if not result.complete and not failures:
        failures.append(dict(context, code='LIST_INCOMPLETE'))
    return result.items, failures


def read_directory(client, *, per_page=1000):
    users, failures = [], []
    for browse in ('inside', 'outside'):
        rows, errors = read_list(client, 'user', browse=browse, per_page=per_page)
        users.extend(rows)
        failures.extend(errors)
    accounts, ids = {}, {}
    for row in users:
        account = row.get('account')
        if not valid_account(account):
            failures.append({'code': 'USER_ACCOUNT_INVALID', 'resource': 'user'})
            continue
        ident = str(row.get('id', account))
        if ((account in accounts and accounts[account] != row)
                or (ident in ids and ids[ident] != account)):
            failures.append({'code': 'USER_DIRECTORY_CONFLICT', 'account': account})
        accounts.setdefault(account, row)
        ids[ident] = account
    return list(accounts.values()), failures


def resolve_members(users, failures, values):
    if failures:
        raise TeamError('TEAM_DIRECTORY_INCOMPLETE', '用户目录不完整或存在冲突；团队配置未修改',
                        {'partial_failures': failures})
    accounts = []
    for value in values:
        account = resolve_user(users, value).get('account')
        if not valid_account(account):
            raise TeamError('TEAM_MEMBER_INVALID', '成员缺少有效账号')
        accounts.append(account)
    return sorted(set(accounts))


def team_members(owner, configured, users, directory_failures):
    by_account = {u['account']: u for u in users}
    result = []
    for account in [owner, *sorted(set(configured) - {owner})]:
        failures = list(directory_failures)
        user = by_account.get(account)
        if user is None:
            failures.append({'code': 'TEAM_MEMBER_UNAVAILABLE', 'account': account,
                             'message': '用户目录中未找到配置账号；未猜测替代账号'})
        name = user.get('realname') if user is not None and not directory_failures else None
        result.append({'account': account, 'realname': name if isinstance(name, str) and name else account,
                       'complete': not failures, 'partial_failures': failures})
    return result


def positive_id(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    if not str(value).isascii() or not str(value).isdigit():
        return None
    try:
        ident = int(value)
    except ValueError:
        return None
    return ident if ident > 0 else None


def collect_bugs(client, *, scope=None, scope_id=None, per_page=1000):
    rows, failures, scopes = [], [], []
    if scope:
        scopes.append((scope, scope_id))
    else:
        # Scan every available list surface: a visible project/execution can expose
        # Bugs even when its product is absent from the product directory.
        for resource in ('product', 'project', 'execution'):
            listed, errors = read_list(client, resource, browse='all', per_page=per_page)
            failures.extend(errors)
            for row in listed:
                ident = positive_id(row.get('id'))
                if ident is None:
                    failures.append({'code': 'SCOPE_ID_INVALID', 'resource': resource})
                else:
                    scopes.append((resource, ident))
    for kind, ident in sorted(set(scopes)):
        listed, errors = read_list(client, 'bug', scope=kind, scope_id=ident, browse='all', per_page=per_page)
        rows.extend(listed)
        failures.extend(errors)
    return rows, failures


def account_field(row, *keys):
    """Normalize explicit account fields without display-name/id/creator fallbacks."""
    values = []
    for key in keys:
        if key not in row:
            continue
        value = row[key]
        if isinstance(value, dict):
            if 'account' not in value:
                continue
            value = value['account']
        if value in (None, '') or (isinstance(value, str) and value.casefold() == 'closed'):
            values.append('')
        elif valid_account(value):
            values.append(value)
        else:
            return None
    if not values or len(set(values)) > 1:
        return None
    return values[0]


def bug_account(row):
    return account_field(row, 'assignedTo', 'assignedToAccount')


def bug_resolver_account(row):
    return account_field(row, 'resolvedBy', 'resolvedByAccount')


def level(value):
    if isinstance(value, bool):
        return 5
    value = str(value)
    return int(value) if value in ('1', '2', '3', '4') else 5


def created_time(row):
    value = row.get('openedDate')
    if not isinstance(value, str):
        return None
    try:
        created = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return created.astimezone(timezone.utc) if created.tzinfo is not None else created
    except (ValueError, OverflowError):
        return None


def bug_sort_key(row, *, mixed_timezones=False):
    pri, sev = level(row.get('pri', row.get('priority'))), level(row.get('severity'))
    created = created_time(row)
    if mixed_timezones:
        created = None
    elif created is not None and created.tzinfo is not None:
        created = created.astimezone(timezone.utc).replace(tzinfo=None)
    return (pri == 5 or sev == 5, pri, sev, created is None, created or datetime.max, int(row['id']))


def build_team_report(members, rows, *, scope=None, scope_id=None, failures=None, today=None):
    failures = list(failures or [])
    common_failures = list(failures)
    by_account = {m['account']: m for m in members}
    member_errors = {m['account']: list(m['partial_failures']) for m in members}
    for member in members:
        for error in member['partial_failures']:
            if error not in failures:
                failures.append(error)
    seen, conflicted, duplicates = {}, set(), 0

    def record(error, account=None):
        failures.append(error)
        targets = [account] if account in by_account else list(by_account)
        for target in targets:
            member_errors[target].append(error)

    for row in rows:
        ident = positive_id(row.get('id'))
        if ident is None:
            record({'code': 'BUG_ID_INVALID'})
            continue
        if ident in seen:
            duplicates += 1
            before = seen[ident]
            def signature(value):
                status = value.get('status')
                owner = (bug_account(value) if status == 'active'
                         else bug_resolver_account(value) if status == 'resolved' else None)
                verification = bug_account(value) if status == 'resolved' else None
                return (owner, verification, status, value.get('title'),
                        value.get('pri', value.get('priority')), value.get('severity'),
                        value.get('openedDate'))
            if signature(before) != signature(row) and ident not in conflicted:
                conflicted.add(ident)
                record({'code': 'BUG_SNAPSHOT_CONFLICT', 'bug_id': ident})
            continue
        seen[ident] = row
    groups = {status: {account: [] for account in by_account} for status in ('active', 'resolved')}
    for ident, row in seen.items():
        if ident in conflicted or row.get('status') == 'closed':
            continue
        status = row.get('status')
        if not isinstance(status, str) or status not in groups:
            record({'code': 'BUG_STATUS_INVALID', 'bug_id': ident})
            continue
        if status == 'active':
            account = bug_account(row)
            if account is None:
                record({'code': 'BUG_ASSIGNEE_INVALID', 'bug_id': ident, 'field': 'assignedTo'})
                continue
            if account not in by_account:
                continue
        else:
            account = bug_resolver_account(row)
            if not valid_account(account):
                record({'code': 'BUG_RESOLVER_INVALID', 'bug_id': ident, 'field': 'resolvedBy'})
                continue
            if account not in by_account:
                continue
            if not valid_account(bug_account(row)):
                record({'code': 'BUG_VERIFICATION_ASSIGNEE_INVALID', 'bug_id': ident,
                        'field': 'assignedTo', 'account': account}, account)
        if created_time(row) is None:
            record({'code': 'BUG_DATE_INVALID', 'bug_id': ident, 'account': account}, account)
        if not isinstance(row.get('title'), str) or not row['title']:
            record({'code': 'BUG_TITLE_INVALID', 'bug_id': ident, 'account': account}, account)
        # Keep the actual fields and original IDs in machine data.
        groups[status][account].append(dict(row))
    for status, group in groups.items():
        for account, bugs in group.items():
            bucket = lambda b: (level(b.get('pri', b.get('priority'))), level(b.get('severity')))
            kinds = {}
            for bug in bugs:
                created = created_time(bug)
                if created is not None:
                    kinds.setdefault(bucket(bug), set()).add(created.tzinfo is not None)
            mixed_buckets = {key for key, values in kinds.items() if len(values) > 1}
            if mixed_buckets:
                record({'code': 'BUG_DATE_INCOMPARABLE', 'account': account, 'status': status}, account)
            bugs.sort(key=lambda b: bug_sort_key(b, mixed_timezones=bucket(b) in mixed_buckets))

    def phase(status):
        return [dict(m, bugs=groups[status][m['account']],
                     complete=not common_failures and not member_errors[m['account']],
                     partial_failures=[*common_failures, *member_errors[m['account']]]) for m in members]

    active, resolved = phase('active'), phase('resolved')
    active_count = sum(len(m['bugs']) for m in active)
    resolved_count = sum(len(m['bugs']) for m in resolved)
    return {'scope': {'type': scope, 'id': scope_id} if scope else {'type': 'all-visible'},
            'snapshot_date': str(date.fromisoformat(today) if today else date.today()),
            'effective_accounts': list(by_account),
            'bug_ids': sorted(int(b['id']) for g in (active, resolved) for m in g for b in m['bugs']),
            'summary': {'total_not_closed': active_count + resolved_count,
                        'active_immediate_action': active_count, 'resolved_awaiting_verification': resolved_count},
            'active': active, 'awaiting_verification': resolved,
            'duplicates_removed': duplicates, 'complete': not failures, 'partial_failures': failures}
