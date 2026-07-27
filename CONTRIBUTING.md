# Contributing

1. Create a focused branch from the default branch.
2. Add a failing test before changing behavior.
3. Keep secrets, local configuration, runtime state and generated files out of Git.
4. Run `python -m pytest`, `python -m ruff check src tests`, `python -m mypy src`, package build checks, and plugin validation.
5. Open a pull request describing behavior, safety impact and verification evidence.

Never add a Bug deletion capability. New write operations require an explicit security design and current-message authorization.
