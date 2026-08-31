"""Phase-specific Markdown presentation; URLs come only from the base CLI."""
from __future__ import annotations

import html
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from team_config import TeamError
from team_report import bug_account, bug_resolver_account, level

CLI = Path(__file__).resolve().parents[2] / 'zentao' / 'scripts' / 'zentao.py'


def bug_urls(ids):
    mapping, failures = {}, []
    for start in range(0, len(ids), 200):
        chunk = ids[start:start + 200]
        try:
            result = subprocess.run([sys.executable, str(CLI), 'bug', 'web-url',
                                     *map(str, chunk), '--json'], capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise ValueError('link command failed')
            rows = json.loads(result.stdout)
            rows = rows if isinstance(rows, list) else [rows]
            chunk_map = {}
            for row in rows:
                if (not isinstance(row, dict) or type(row.get('id')) is not int
                        or row['id'] not in chunk or not isinstance(row.get('url'), str)
                        or not row['url'] or row['id'] in chunk_map):
                    raise ValueError('invalid link result')
                chunk_map[row['id']] = row['url']
            mapping.update(chunk_map)
            if set(chunk_map) != set(chunk):
                failures.append('部分 Bug 链接生成失败；未猜测 URL')
        except (OSError, ValueError, subprocess.SubprocessError):
            failures.append('Bug 链接生成失败；未猜测 URL')
    return mapping, failures


def escape(value):
    text = html.escape(str(value), quote=False).replace('\\', '\\\\')
    for char in ('|', '[', ']', '*', '_', '`', '#'):
        text = text.replace(char, '\\' + char)
    return text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')


def render_team_report(report, *, brief=False):
    urls, display_failures = bug_urls(report['bug_ids'])
    lines = []
    if brief:
        summary = report['summary']
        prefix = '已获取' if not report['complete'] else '共'
        lines.extend([f"# 团队日报 · {report['snapshot_date']}", '',
                      f"{prefix} {summary['total_not_closed']} 个未关闭 Bug；"
                      f"需要马上行动 {summary['active_immediate_action']} 个，"
                      f"待测试验证 {summary['resolved_awaiting_verification']} 个。", ''])
    if not report['complete']:
        lines.extend(['**数据不完整：数量仅代表已获取结果，不能将失败成员视为 0。**', ''])
    for key, state, heading in (('active', 'active', '一、需要马上行动'),
                                ('awaiting_verification', 'resolved', '二、待测试验证')):
        lines.extend([f'## {heading}', ''])
        names = Counter(m['realname'] for m in report[key])
        for member in report[key]:
            name = member['realname']
            if names[name] > 1:
                name += f" / {member['account']}"
            bugs = member['bugs']
            count = str(len(bugs)) if member['complete'] else f'已获取 {len(bugs)}，数据不完整' if bugs else '数据不完整'
            lines.extend([f'### {escape(name)}（{count}）', ''])
            if not bugs:
                lines.extend(['暂无符合条件的 Bug。' if member['complete'] else '查询不完整，无法确定是否存在符合条件的 Bug。', ''])
                continue
            if state == 'active':
                lines.extend(['| Bug ID | 标题 | 优先级 | 状态 |', '|---|---|---|---|'])
            else:
                lines.extend(['| Bug ID | 标题 | 优先级 | 状态 | 当前测试负责人 |',
                              '|---|---|---|---|---|'])
            for bug in bugs:
                owner = bug_account(bug) if state == 'active' else bug_resolver_account(bug)
                if bug.get('status') != state or owner != member['account']:
                    raise TeamError('TEAM_PRESENTATION_CONFLICT', 'Bug 状态或负责人和分组不一致')
                ident = int(bug['id'])
                link = f'[{ident}]({urls[ident]})' if ident in urls else f'{ident}（链接生成失败）'
                pri = level(bug.get('pri', bug.get('priority')))
                priority = f'P{pri}' if pri < 5 else '—'
                title = bug.get('title') if isinstance(bug.get('title'), str) else '（标题缺失）'
                row = f"| {link} | {escape(title)} | {priority} | {'激活' if state == 'active' else '已解决'}"
                if state == 'resolved':
                    row += f" | {escape(bug_account(bug) or '—')}"
                lines.append(row + ' |')
            lines.append('')
    if report['partial_failures']:
        lines.extend(['## 数据完整性', ''])
        for failure in report['partial_failures']:
            detail = ' / '.join(str(failure[k]) for k in
                                ('resource', 'scope', 'browse', 'account', 'bug_id', 'field', 'page')
                                if k in failure)
            lines.append(f"- {escape(failure['code'])}" + (f'：{escape(detail)}' if detail else ''))
        lines.append('')
    if display_failures:
        lines.extend(['## 链接生成', '', *[f'- {message}' for message in dict.fromkeys(display_failures)], ''])
    return '\n'.join(lines).rstrip()
