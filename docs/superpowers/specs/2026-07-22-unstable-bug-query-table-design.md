# Unstable Bug Query and Table Output Design

## Goal

Preserve useful read-only Bug data when Zentao omits a stable `version`, and present ad-hoc user query results as a Markdown table containing Bug ID, title, priority, status, assignee, and snapshot stability.

Missing stable versions must remain visible without being misrepresented as concurrency-safe snapshots. Comments and local code repair may proceed only after exact, current-turn human authorization for the concrete Bug and action. Existing gates for repository safety, tests, comments, and protected Zentao state changes remain in force.

## Selected Approach

Use an explicit degraded snapshot rather than dropping the Bug or synthesizing a version.

- A stable response keeps its existing `snapshotVersion` and reports `snapshotStable=true`.
- A response without a stable version remains in `items`, reports `snapshotVersion=null` and `snapshotStable=false`, and preserves available read-only fields.
- No hash derived from mutable display fields is treated as a stable version.
- The MCP and CLI use the same normalized representation.

This approach preserves information while keeping the concurrency limitation visible and enforceable.

## Normalized Bug Contract

Every list item provides these presentation fields when available:

- `id`
- `title`
- `priority`
- `status`
- `assignee`
- `snapshotVersion: string | null`
- `snapshotStable: boolean`

Missing presentation fields do not remove the row. The normalizer substitutes a stable display value such as `unknown` and records the field gap in structured completeness metadata. A missing stable version is a degraded snapshot condition, not an item-level fatal error.

Existing raw data may remain available for compatible callers, but authorization decisions must use normalized fields rather than trusting raw payload content.

## MCP Behavior

`query_user_bugs`, including `scopeMode=session-visible`, returns degraded items in `structuredContent.data.items`. It does not reduce them to Bug IDs in `itemFailures` solely because `version` is absent.

Coverage remains truthful:

- Pagination and transport failures continue to make coverage partial.
- Degraded snapshots are counted and returned.
- Completeness metadata records how many returned rows have unstable snapshots and which required presentation fields were unavailable.
- A degraded snapshot never authorizes a side effect by itself.

Stable-version behavior remains backward compatible.

## CLI Presentation

Ad-hoc user Bug queries render a Markdown table by default:

| Bug号 | 标题 | 优先级 | 状态 | 负责人 | 快照稳定性 |
| --- | --- | --- | --- | --- | --- |

The renderer escapes pipes, replaces embedded newlines with spaces, and uses `unknown` for unavailable display values. Snapshot stability renders as `稳定` or `不稳定`.

Machine-readable JSON remains available through the existing structured/MCP path; the table is a CLI presentation concern and does not replace structured output.

## Authorization for Unstable Snapshots

An unstable snapshot may enter comment or local repair workflows only with exact authorization that is:

- issued in the current interaction turn;
- bound to one concrete Bug ID;
- bound to one concrete action (`comment` or `repair`);
- not reusable as a bulk, historical, or global approval.

Before the authorized action, the system re-queries the Bug and compares all available normalized safety fields. If the Bug disappears, changes assignee or status incompatibly, or the re-query fails, the action fails closed.

Exact authorization only permits entry into the existing workflow. It does not bypass:

- structured history and cooldown checks for comments;
- deterministic comment rendering and idempotency;
- repository routing and direct-branch preflight;
- clean worktree, upstream, test whitelist, diff, and final review gates;
- exact confirmation requirements for protected Bug state changes.

Resolving, closing, assigning, activating, deleting, deploying, committing, or pushing are not newly authorized by this design. Permanent Bug deletion remains forbidden.

## Error Handling

- Missing `version`: retain the row and mark it unstable.
- Missing title, priority, status, or assignee: retain the row, display `unknown`, and record the field gap.
- Invalid identity or transport failure: preserve the existing sanitized failure behavior.
- Pagination contradiction or truncation: preserve returned rows and mark coverage partial.
- Missing or stale exact authorization: reject the side effect with a structured authorization error.
- Re-query mismatch before an unstable-snapshot action: reject the action and report the changed safety field without writing.

## Test Strategy

Tests follow red-green-refactor and cover:

1. Provider normalization retains a Bug whose `version` is absent.
2. The degraded item includes title, priority, status, assignee, `snapshotVersion=null`, and `snapshotStable=false`.
3. MCP `query_user_bugs` exposes degraded items and truthful completeness metadata.
4. Stable-version list and detail behavior remains unchanged.
5. CLI output contains the Markdown table and escapes pipes and newlines in titles.
6. Missing display fields render as `unknown` without dropping the row.
7. Unstable-snapshot comment and repair attempts fail without exact current-turn Bug/action authorization.
8. Valid exact authorization permits entry into existing downstream gates but does not bypass them.
9. Protected state changes and forbidden deletion remain unchanged.

## Scope

This change is limited to Zentao Bug normalization, MCP query output, CLI table presentation, authorization of unstable-snapshot comment/repair entry, and their tests and documentation. It does not redesign daily report templates, add new state-changing tools, or broaden team-report membership and scope rules.
