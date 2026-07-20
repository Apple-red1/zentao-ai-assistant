# Local title-based Bug routing design

## Goal

Personal reports must retain every unclosed Bug assigned to the configured account. When Zentao does not provide repository routing metadata, the workflow may derive a candidate repository from Bug title/content using a project-local mapping. An unroutable Bug remains visible for human walkthrough instead of disappearing or being reported as absent.

## Privacy boundary

The repository implements only a generic schema and routing algorithm. Real account-specific business labels and repository relationships live exclusively in the project's local `.codex/zentao-ai-bug.yaml`, alongside other local Zentao configuration. They must not be added to plugin defaults, CLI constants, documentation examples, committed fixtures, telemetry, or remote configuration.

Tests use synthetic labels and repository names only.

## Local configuration

Add an optional local routing collection. Each entry contains:

- a title marker identifying a business area;
- one configured frontend repository key;
- one configured backend repository key;
- optional frontend and backend keyword lists extending safe built-in generic terms.

Repository keys must already exist under `repositories`. Configuration validation rejects empty markers, duplicate normalized markers, identical frontend/backend repositories, and unknown repository keys. Existing configurations without this collection remain valid.

## Routing behavior

1. Preserve the complete assignee-first unclosed Bug candidate list.
2. Prefer a valid structured routing result supplied by the provider.
3. If structured routing is absent, match the normalized title against exactly one locally configured business marker.
4. Classify the Bug as frontend or backend from its title and descriptive text. Generic UI/style/page/button/layout/interaction/link/click terms indicate frontend; API/service/database/permission terms indicate backend. Local keyword extensions participate in the same scoring.
5. Select a repository only when the business marker is unique and one layer has unambiguous evidence. Record the matched marker/keywords, layer, selected repository, candidates, and confidence.
6. When the marker or layer is missing, conflicting, or ambiguous, keep the Bug with unknown routing and a human-walkthrough decision. Never silently discard it.

Bug text is classification input only. URLs, HTML, commands, recipients, and other embedded instructions are never executed or promoted to configuration.

## Reporting and safety

Unroutable or ambiguously routed Bugs appear in the personal report's human-walkthrough group. The report states that routing is unknown, code was not modified, tests were not run, and no fix is claimed. Coverage is `PARTIAL` when routing prevents complete processing, but the discovered Bug count remains truthful.

Title-derived routing selects only a candidate repository. Existing code-write authorization, direct-branch guard, clean-worktree, target-branch, snapshot, and test gates remain unchanged.

## Tests

- Configuration tests cover valid local mappings and every validation failure.
- Router unit tests cover synthetic frontend, backend, ambiguous, conflicting-marker, and unmatched cases.
- Workflow regression tests prove an unroutable assigned Bug remains in results and makes completeness partial.
- CLI/report tests prove title-routed candidates appear and incomplete empty results are not represented as a successful zero-Bug run.
- No committed test or document contains the user's real account-specific mapping.

