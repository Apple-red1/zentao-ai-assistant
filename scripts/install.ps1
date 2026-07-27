param(
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
$pythonPrefix = @()
if ($null -ne $pythonCommand) {
    $pythonPrefix = @('-3.11')
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
}
if ($null -eq $pythonCommand) {
    throw '需要 Python 3.11 或更高版本。'
}

function Invoke-Python {
    param([string[]]$Arguments)
    & $pythonCommand.Source @pythonPrefix @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python 命令执行失败，退出码：$LASTEXITCODE"
    }
}

Invoke-Python @('-c', 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 2)')

$codexCommand = Get-Command codex -ErrorAction SilentlyContinue
if ($null -eq $codexCommand) {
    throw '未找到 Codex CLI，请先安装或升级 Codex。'
}

& $pythonCommand.Source @pythonPrefix -m pipx --version *> $null
if ($LASTEXITCODE -ne 0) {
    Invoke-Python @('-m', 'pip', 'install', '--user', 'pipx')
    Invoke-Python @('-m', 'pipx', 'ensurepath')
}

Invoke-Python @('-m', 'pipx', 'install', '--force', $repoRoot)

$pipxBin = & $pythonCommand.Source @pythonPrefix -m pipx environment --value PIPX_BIN_DIR
if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($pipxBin)) {
    $env:PATH = "$pipxBin$([IO.Path]::PathSeparator)$env:PATH"
}

try {
    & $codexCommand.Source plugin marketplace add $repoRoot *> $null
} catch {
    # 已存在的本地 Marketplace 可以安全复用。
}
& $codexCommand.Source plugin add 'zentao-ai-bug@zentao-ai-assistant'
if ($LASTEXITCODE -ne 0) {
    throw 'Codex 插件安装失败。'
}

$configPath = if ($env:ZENTAO_CONFIG) {
    $env:ZENTAO_CONFIG
} else {
    Join-Path $HOME '.codex/zentao-ai-bug/config.yaml'
}
$zentaoCommand = Get-Command zentao-ai -ErrorAction SilentlyContinue
if ($NonInteractive) {
    if ((Test-Path $configPath) -and $null -ne $zentaoCommand) {
        & $zentaoCommand.Source doctor --config $configPath
    } else {
        Write-Output '安装完成。请运行 zentao-ai setup，然后运行 zentao-ai doctor。'
    }
} else {
    if ($null -eq $zentaoCommand) {
        throw 'zentao-ai 尚未进入 PATH；请重开终端后运行 zentao-ai setup。'
    }
    & $zentaoCommand.Source setup
    & $zentaoCommand.Source doctor
}

Write-Output '插件已安装。重启 Codex 或新建任务后即可使用。'
