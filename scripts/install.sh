#!/bin/sh
set -eu

non_interactive=0
if [ "${1:-}" = "--non-interactive" ]; then
  non_interactive=1
elif [ "$#" -gt 0 ]; then
  echo "用法：scripts/install.sh [--non-interactive]" >&2
  exit 2
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "${script_dir}/.." && pwd)
python_bin=${PYTHON:-python3}

if ! command -v "$python_bin" >/dev/null 2>&1; then
  echo "需要 Python 3.11 或更高版本。" >&2
  exit 2
fi

"$python_bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 2)'

if ! command -v codex >/dev/null 2>&1; then
  echo "未找到 Codex CLI，请先安装或升级 Codex。" >&2
  exit 2
fi

if ! "$python_bin" -m pipx --version >/dev/null 2>&1; then
  "$python_bin" -m pip install --user pipx
  "$python_bin" -m pipx ensurepath
fi

"$python_bin" -m pipx install --force "$repo_root"

pipx_bin_dir=$("$python_bin" -m pipx environment --value PIPX_BIN_DIR 2>/dev/null || true)
if [ -n "$pipx_bin_dir" ]; then
  PATH="${pipx_bin_dir}:${PATH}"
  export PATH
fi

# Re-running these commands updates an existing local registration/plugin.
codex plugin marketplace add "$repo_root" >/dev/null 2>&1 || true
codex plugin add zentao-ai-bug@zentao-ai-assistant

config_path=${ZENTAO_CONFIG:-${HOME}/.codex/zentao-ai-bug/config.yaml}
if [ "$non_interactive" -eq 1 ]; then
  if [ -f "$config_path" ] && command -v zentao-ai >/dev/null 2>&1; then
    zentao-ai doctor --config "$config_path"
  else
    echo "安装完成。请运行 zentao-ai setup，然后运行 zentao-ai doctor。"
  fi
else
  zentao-ai setup
  zentao-ai doctor
fi

echo "插件已安装。重启 Codex 或新建任务后即可使用。"
