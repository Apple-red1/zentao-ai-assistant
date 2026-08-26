#!/bin/sh
set -eu

non_interactive=0
if [ "${1:-}" = "--non-interactive" ]; then
  non_interactive=1
elif [ "$#" -gt 0 ]; then
  echo "用法：scripts/install.sh [--non-interactive]" >&2
  exit 2
fi

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH='' cd -- "${script_dir}/.." && pwd)
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

# 运行 pipx 的统一入口：默认使用 python3 -m pipx；当通过 Homebrew
# 安装 pipx 时（Homebrew Python 受 PEP 668 保护，python3 -m pipx
# 无法使用），改用独立的 pipx 可执行文件。
PIPX_CMD=''
pipx_run() {
  if [ -n "$PIPX_CMD" ]; then
    command "$PIPX_CMD" "$@"
  else
    "$python_bin" -m pipx "$@"
  fi
}

if ! "$python_bin" -m pipx --version >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    brew install pipx
    PIPX_CMD='pipx'
  elif ! "$python_bin" -m pip install --user pipx; then
    echo "无法自动安装 pipx：当前 Python 环境受 PEP 668 保护（externally-managed-environment）。" >&2
    echo "请先手动安装 pipx（例如 brew install pipx），然后重新运行本脚本。" >&2
    exit 2
  fi
  pipx_run ensurepath
fi

pipx_run install --force "$repo_root"

pipx_bin_dir=$(pipx_run environment --value PIPX_BIN_DIR 2>/dev/null || true)
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
