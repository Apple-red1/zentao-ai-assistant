# 个人 Bug 日报

业务日期：2099-01-02（Asia/Shanghai）
快照截止：2099-01-02T08:00:00+08:00
运行类型：SYNTHETIC_FIXTURE
覆盖范围：example-web、example-api、example-ai-web、example-ai-api
完整性：Synthetic complete fixture.

## 等待补充信息 Bug

BUG-1001｜当前状态：active｜判断：NEEDS_REPORTER_INFO
路由：selectedRepository=null，layer=frontend；候选为 example-web、example-ai-web；关键词：example、synthetic。
是否修改代码：否
快照版本：fixture-version-1001
原因：Synthetic reproduction detail is intentionally missing.
AI评论：FAILED / None
备注：拟添加备注（写入失败）：@example-reporter Please provide the synthetic reproduction detail.

## 人工需走查 Bug

BUG-1002｜当前状态：active｜判断：PATCH_RETAINED_FOR_HUMAN_VALIDATION
路由：example-ai-web / frontend；关键词：example、link。
是否修改代码：是
快照版本：fixture-version-1002
门禁：Synthetic branch gate passed for example/fixture-branch.
根因证据：Synthetic fixture evidence points to example/component.ts.
测试：Synthetic test command failed; 未声称修复完成。
禅道备注：NOT_SENT / None
