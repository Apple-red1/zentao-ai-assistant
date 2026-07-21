# Plugin wrapper CLI dispatch design

## Goal

Codex plugin scripts must work when launched by any available Python interpreter, including an isolated Codex runtime that does not contain the `zentao_ai` package, as long as the supported CLI installation is available on `PATH`.

## Root cause

The plugin scripts currently import `zentao_ai` directly. The supported installation uses `pipx`, which places the package in its own virtual environment and exposes launchers on `PATH`. Codex invokes plugin scripts with its bundled Python, so the import fails even though `zentao-ai` itself is installed and functional.

## Command boundary

The Python package will publish stable companion console scripts for internal plugin operations:

- `zentao-ai-state` dispatches to the durable state/ledger CLI.
- `zentao-ai-repository` dispatches to the repository guard CLI.
- `zentao-ai-render-report` dispatches to the deterministic report renderer.

The existing `zentao-ai` launcher remains the public application CLI. The plugin `doctor.py` wrapper invokes `zentao-ai doctor` and forwards all user arguments.

Plugin wrappers use only Python standard-library process discovery and execution. They locate the expected launcher with `shutil.which`, execute it without a shell, preserve argument ordering, and return the child exit code. They never inspect pipx directories, virtual environments, credentials, or platform-specific launcher internals.

## Failure behavior

If a required launcher is unavailable, the wrapper exits nonzero and emits the existing supported GitHub/pipx installation instruction. It must not fall back to importing `zentao_ai`, modifying `sys.path`, installing dependencies, or guessing environment paths.

Signals and normal child exit codes are propagated by the operating system/process API. Standard input, output, and error remain attached so JSON and Markdown contracts are unchanged.

## Packaging and compatibility

The companion commands are declared in `pyproject.toml` and installed with the same distribution as `zentao-ai`. Windows, macOS, and Linux use the packaging tool's native launcher generation. Existing public CLI commands and MCP configuration remain unchanged.

The cached plugin copy is refreshed through the normal plugin packaging/install flow; repository source is the only code changed.

## Tests

- Package metadata tests assert all companion scripts point at the intended `main` callables.
- Wrapper contract tests place synthetic companion executables on a temporary `PATH`, run each wrapper under isolated Python (`-I -S`), and assert exact argv forwarding plus child exit-code propagation.
- Missing-command tests assert the supported GitHub/pipx instruction and a nonzero exit code.
- Existing plugin, CLI, MCP, state, repository, and report tests remain green.
