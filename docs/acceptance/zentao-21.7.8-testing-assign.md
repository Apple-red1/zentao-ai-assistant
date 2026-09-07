# ZenTao 21.7.8 active Bug 独立指派验收

状态：`INCONCLUSIVE/ENVIRONMENT_BLOCKER`

## 原因

Issue #62 的 T04 要求在专用、可清理的 ZenTao 21.7.8 实例上验证 active Bug 是否存在
保持 `status=active` 的独立负责人指派能力，并完成写后 `view` 回读。当前工作区没有
可用的专用 ZenTao 实例、凭据或可安全清理的验收数据；`/mnt/data/zentao.zip` 也不存在，
且源码包不能替代运行中的兼容性环境。

## 受此门槛约束的范围

- 未声称 active Bug 独立指派已支持、兼容或已通过验收。
- 未新增官方 API endpoint、`endpoints.json` 条目、catalog 路由或生命周期旁路。
- 未用 `activate`、`resolve`、`edit` 或其它生命周期动作模拟独立指派。
- T05 的 `bug assign` 兼容实现和真实写后回读保持未执行；补齐环境后必须先完成 T04，
  再按真实响应决定是否实现。

## 后续验收要求

在隔离实例中使用临时账号和可删除的 active Bug，记录实际 method/path、状态变化、
负责人字段、权限错误和结果未知情形。只有在一次受支持的非生命周期写入保持 active、
且显式回读同时确认 `status=active` 与 `assignedTo=target_account` 后，才能将状态改为
supported/native compatibility，并实现或更新基础 CLI 合同；失败则记录 upstream unsupported
或 contract conflict，无法完成安全判定仍保持本状态。测试数据和凭据不得进入仓库。
