# 功能与能力面

当前产品单元是单一 `skills/zentao/` Skill。官方 API v2 快照覆盖 20 个资源、120 个 endpoint；Token 作为内部认证能力，其余资源通过统一 `<resource> <action> [scope] [parameters]` CLI 暴露。

## 资源

`bug`、`build`、`epic`、`execution`、`feedback`、`file`、`product`、`product-plan`、`program`、`project`、`release`、`requirement`、`story`、`system`、`task`、`test-case`、`test-task`、`ticket`、`user`。

完整机器索引见 `skills/zentao/references/api-v2/endpoints.json`；领域导航见同目录的资源 reference；参数合同以 CLI `--help` 为准。

## 风险等级

- R0：读取（list/view），可直接执行。
- R1：普通写入（create/edit/upload/change），要求当前请求明确表达对应写操作。
- R2：生命周期动作（resolve/close/activate/start/finish），要求当前请求明确表达该状态变更。
- R3：delete，要求当前请求明确删除具体资源，并且 CLI 必须显式传 `--yes`。

每条命令只执行一个明确的 ZenTao API v2 endpoint。写操作不自动重试，也不会写后自动 GET；结果不确定时返回 `UNKNOWN_WRITE_RESULT`。
