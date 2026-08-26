# Issue #27 真实用户场景验收台账

来源为 GitHub Issue #27 的 190 条评论；严格按评论目录顺序展开，Scenario Outline 的每个 Examples 行均为独立场景。记录来自真实 ZenTao 21.7.8 流程、显式只读回读或真实错误响应；兼容性限制没有用替代接口伪造成功。

## 总结

- 实际场景：830
- 通过：684
- 通过但受 ZenTao 21.7.8/API v2 限制：146
- 未解决失败：0
- 顺序校验：PROGRAM → PRODUCT → PLAN → PROJECT → EXECUTION → EPIC → REQUIREMENT → STORY → TASK → TESTCASE → TESTTASK → BUILD → RELEASE → SYSTEM → USER → FILE → FLOW
- 自动化门槛：`python3 skills/zentao/tests/run_all.py`，98 tests，Catalog/Internal/CLI/Skill routes/Fake API/Contract/CLI E2E 均 120/120，Real API calls 0，Result PASS。

## 沿途根因修复与回归

1. `status=fail` 或 `result=fail` 统一识别为 `API_ERROR`，避免 200 业务失败被当成成功。
2. Program/Product 名称增加非空 CLI 校验，非法输入在业务 HTTP 前返回 usage error。
3. Product 描述按目标真实语义发送 scalar 文本，避免单元素数组被存成字面量 `Array`。
4. Epic/Requirement 编辑显式要求 reviewer；duplicate close 显式传递 `duplicateStory`。
5. TestCase 多步骤缺少 `stepType` 时为每步补 `step`，避免 21.7.8 静默只保留第一步。
6. File delete 不再把空响应合成成功对象；空响应现在为 `API_ERROR`。

## 逐项记录

| 场景ID/Example | 场景 | 结果 | 问题 | 根因 | 修复 | 自动化测试 | 场景复测 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PROGRAM-GH-001/01 | 按公司/事业群真实组织结构创建项目集 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-001/02 | 按公司/事业群真实组织结构创建项目集 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-001/03 | 按公司/事业群真实组织结构创建项目集 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-001/04 | 按公司/事业群真实组织结构创建项目集 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-001/05 | 按公司/事业群真实组织结构创建项目集 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-002/01 | 编辑项目集范围、负责人和周期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-002/02 | 编辑项目集范围、负责人和周期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-002/03 | 编辑项目集范围、负责人和周期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-002/04 | 编辑项目集范围、负责人和周期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-002/05 | 编辑项目集范围、负责人和周期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-003/01 | 项目集列表、排序、分页和筛选 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-003/02 | 项目集列表、排序、分页和筛选 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-003/03 | 项目集列表、排序、分页和筛选 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-003/04 | 项目集列表、排序、分页和筛选 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-003/05 | 项目集列表、排序、分页和筛选 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-004/01 | 项目集详情与对象身份确认 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-004/02 | 项目集详情与对象身份确认 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-004/03 | 项目集详情与对象身份确认 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-004/04 | 项目集详情与对象身份确认 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-004/05 | 项目集详情与对象身份确认 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-005/01 | 项目集下产品/项目归属的只读核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-005/02 | 项目集下产品/项目归属的只读核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-005/03 | 项目集下产品/项目归属的只读核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-005/04 | 项目集下产品/项目归属的只读核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-005/05 | 项目集下产品/项目归属的只读核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-006/01 | 日期、文本与完整字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-006/02 | 日期、文本与完整字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-006/03 | 日期、文本与完整字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-006/04 | 日期、文本与完整字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-006/05 | 日期、文本与完整字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-007/01 | 项目集业务边界与无效日期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-007/02 | 项目集业务边界与无效日期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-007/03 | 项目集业务边界与无效日期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-007/04 | 项目集业务边界与无效日期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-007/05 | 项目集业务边界与无效日期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROGRAM-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-001/01 | 按真实产品形态创建产品 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-001/02 | 按真实产品形态创建产品 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-001/03 | 按真实产品形态创建产品 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-001/04 | 按真实产品形态创建产品 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-001/05 | 按真实产品形态创建产品 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-002/01 | 修改产品负责人、访问控制与描述 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-002/02 | 修改产品负责人、访问控制与描述 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-002/03 | 修改产品负责人、访问控制与描述 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-002/04 | 修改产品负责人、访问控制与描述 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-002/05 | 修改产品负责人、访问控制与描述 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-003/01 | 产品全局/项目集范围列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-003/02 | 产品全局/项目集范围列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-003/03 | 产品全局/项目集范围列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-003/04 | 产品全局/项目集范围列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-003/05 | 产品全局/项目集范围列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-004/01 | 产品详情和类型/负责人核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-004/02 | 产品详情和类型/负责人核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-004/03 | 产品详情和类型/负责人核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-004/04 | 产品详情和类型/负责人核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-004/05 | 产品详情和类型/负责人核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-005/01 | 产品与项目集、多产品项目的关联语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-005/02 | 产品与项目集、多产品项目的关联语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-005/03 | 产品与项目集、多产品项目的关联语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-005/04 | 产品与项目集、多产品项目的关联语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-005/05 | 产品与项目集、多产品项目的关联语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-006/01 | 产品类型、评审人和文本字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-006/02 | 产品类型、评审人和文本字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-006/03 | 产品类型、评审人和文本字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-006/04 | 产品类型、评审人和文本字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-006/05 | 产品类型、评审人和文本字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-007/01 | 当前 API 能力之外的产品动作 | 通过（兼容性限制） | catalog 没有该产品动作 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PRODUCT-GH-007/02 | 当前 API 能力之外的产品动作 | 通过（兼容性限制） | catalog 没有该产品动作 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PRODUCT-GH-007/03 | 当前 API 能力之外的产品动作 | 通过（兼容性限制） | catalog 没有该产品动作 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PRODUCT-GH-007/04 | 当前 API 能力之外的产品动作 | 通过（兼容性限制） | catalog 没有该产品动作 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PRODUCT-GH-007/05 | 当前 API 能力之外的产品动作 | 通过（兼容性限制） | catalog 没有该产品动作 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PRODUCT-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PRODUCT-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-001/01 | 创建季度、版本和分支产品计划 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-001/02 | 创建季度、版本和分支产品计划 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-001/03 | 创建季度、版本和分支产品计划 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-001/04 | 创建季度、版本和分支产品计划 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-001/05 | 创建季度、版本和分支产品计划 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-002/01 | 编辑计划日期、标题和状态且保留归属 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-002/02 | 编辑计划日期、标题和状态且保留归属 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-002/03 | 编辑计划日期、标题和状态且保留归属 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-002/04 | 编辑计划日期、标题和状态且保留归属 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-002/05 | 编辑计划日期、标题和状态且保留归属 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-003/01 | 按产品查询计划与分页 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-003/02 | 按产品查询计划与分页 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-003/03 | 按产品查询计划与分页 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-003/04 | 按产品查询计划与分页 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-003/05 | 按产品查询计划与分页 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-004/01 | 计划详情与父子/分支关系核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-004/02 | 计划详情与父子/分支关系核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-004/03 | 计划详情与父子/分支关系核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-004/04 | 计划详情与父子/分支关系核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-004/05 | 计划详情与父子/分支关系核对 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-005/01 | 21.7.8 product/status/branch 兼容字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-005/02 | 21.7.8 product/status/branch 兼容字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-005/03 | 21.7.8 product/status/branch 兼容字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-005/04 | 21.7.8 product/status/branch 兼容字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-005/05 | 21.7.8 product/status/branch 兼容字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-006/01 | 产品计划与需求关联的能力边界 | 通过（兼容性限制） | API v2 没有计划与需求关联 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PLAN-GH-006/02 | 产品计划与需求关联的能力边界 | 通过（兼容性限制） | API v2 没有计划与需求关联 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PLAN-GH-006/03 | 产品计划与需求关联的能力边界 | 通过（兼容性限制） | API v2 没有计划与需求关联 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PLAN-GH-006/04 | 产品计划与需求关联的能力边界 | 通过（兼容性限制） | API v2 没有计划与需求关联 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PLAN-GH-006/05 | 产品计划与需求关联的能力边界 | 通过（兼容性限制） | API v2 没有计划与需求关联 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PLAN-GH-007/01 | 计划日期、层级与输入校验 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-007/02 | 计划日期、层级与输入校验 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-007/03 | 计划日期、层级与输入校验 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-007/04 | 计划日期、层级与输入校验 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-007/05 | 计划日期、层级与输入校验 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PLAN-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-001/01 | 创建不同项目模型的真实项目 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-001/02 | 创建不同项目模型的真实项目 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-001/03 | 创建不同项目模型的真实项目 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-001/04 | 创建不同项目模型的真实项目 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-001/05 | 创建不同项目模型的真实项目 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-002/01 | 编辑项目周期、PM 和关联产品 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-002/02 | 编辑项目周期、PM 和关联产品 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-002/03 | 编辑项目周期、PM 和关联产品 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-002/04 | 编辑项目周期、PM 和关联产品 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-002/05 | 编辑项目周期、PM 和关联产品 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-003/01 | 项目全局/项目集范围列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-003/02 | 项目全局/项目集范围列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-003/03 | 项目全局/项目集范围列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-003/04 | 项目全局/项目集范围列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-003/05 | 项目全局/项目集范围列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-004/01 | 项目身份与当前 API 无 view 端点边界 | 通过（兼容性限制） | Project 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PROJECT-GH-004/02 | 项目身份与当前 API 无 view 端点边界 | 通过（兼容性限制） | Project 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PROJECT-GH-004/03 | 项目身份与当前 API 无 view 端点边界 | 通过（兼容性限制） | Project 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PROJECT-GH-004/04 | 项目身份与当前 API 无 view 端点边界 | 通过（兼容性限制） | Project 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PROJECT-GH-004/05 | 项目身份与当前 API 无 view 端点边界 | 通过（兼容性限制） | Project 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| PROJECT-GH-005/01 | 项目集与多产品项目关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-005/02 | 项目集与多产品项目关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-005/03 | 项目集与多产品项目关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-005/04 | 项目集与多产品项目关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-005/05 | 项目集与多产品项目关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-006/01 | 项目模型与流程模板参数边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-006/02 | 项目模型与流程模板参数边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-006/03 | 项目模型与流程模板参数边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-006/04 | 项目模型与流程模板参数边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-006/05 | 项目模型与流程模板参数边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-007/01 | 项目创建/编辑的业务前置与错误 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-007/02 | 项目创建/编辑的业务前置与错误 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-007/03 | 项目创建/编辑的业务前置与错误 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-007/04 | 项目创建/编辑的业务前置与错误 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-007/05 | 项目创建/编辑的业务前置与错误 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| PROJECT-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-001/01 | 创建 Sprint、阶段和看板执行 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-001/02 | 创建 Sprint、阶段和看板执行 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-001/03 | 创建 Sprint、阶段和看板执行 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-001/04 | 创建 Sprint、阶段和看板执行 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-001/05 | 创建 Sprint、阶段和看板执行 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-002/01 | 编辑执行周期、负责人和关联计划 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-002/02 | 编辑执行周期、负责人和关联计划 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-002/03 | 编辑执行周期、负责人和关联计划 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-002/04 | 编辑执行周期、负责人和关联计划 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-002/05 | 编辑执行周期、负责人和关联计划 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-003/01 | 全局与项目范围执行列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-003/02 | 全局与项目范围执行列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-003/03 | 全局与项目范围执行列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-003/04 | 全局与项目范围执行列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-003/05 | 全局与项目范围执行列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-004/01 | 执行详情和类型/生命周期属性核对 | 通过（兼容性限制） | execution view/list 缺少部分 product/plan 字段 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| EXECUTION-GH-004/02 | 执行详情和类型/生命周期属性核对 | 通过（兼容性限制） | execution view/list 缺少部分 product/plan 字段 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| EXECUTION-GH-004/03 | 执行详情和类型/生命周期属性核对 | 通过（兼容性限制） | execution view/list 缺少部分 product/plan 字段 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| EXECUTION-GH-004/04 | 执行详情和类型/生命周期属性核对 | 通过（兼容性限制） | execution view/list 缺少部分 product/plan 字段 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| EXECUTION-GH-004/05 | 执行详情和类型/生命周期属性核对 | 通过（兼容性限制） | execution view/list 缺少部分 product/plan 字段 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| EXECUTION-GH-005/01 | 执行与项目/产品/计划的关系 | 通过（兼容性限制） | 部分多产品/阶段关系在 target 返回不完整 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| EXECUTION-GH-005/02 | 执行与项目/产品/计划的关系 | 通过（兼容性限制） | 部分多产品/阶段关系在 target 返回不完整 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| EXECUTION-GH-005/03 | 执行与项目/产品/计划的关系 | 通过（兼容性限制） | 部分多产品/阶段关系在 target 返回不完整 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| EXECUTION-GH-005/04 | 执行与项目/产品/计划的关系 | 通过（兼容性限制） | 部分多产品/阶段关系在 target 返回不完整 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| EXECUTION-GH-005/05 | 执行与项目/产品/计划的关系 | 通过（兼容性限制） | 部分多产品/阶段关系在 target 返回不完整 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| EXECUTION-GH-006/01 | 执行日期、days、角色与 ACL 保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-006/02 | 执行日期、days、角色与 ACL 保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-006/03 | 执行日期、days、角色与 ACL 保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-006/04 | 执行日期、days、角色与 ACL 保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-006/05 | 执行日期、days、角色与 ACL 保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-007/01 | 执行类型/阶段业务边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-007/02 | 执行类型/阶段业务边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-007/03 | 执行类型/阶段业务边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-007/04 | 执行类型/阶段业务边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-007/05 | 执行类型/阶段业务边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EXECUTION-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-001/01 | 从市场/客户/研发输入创建需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-001/02 | 从市场/客户/研发输入创建需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-001/03 | 从市场/客户/研发输入创建需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-001/04 | 从市场/客户/研发输入创建需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-001/05 | 从市场/客户/研发输入创建需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-002/01 | 编辑标题、优先级、分类和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-002/02 | 编辑标题、优先级、分类和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-002/03 | 编辑标题、优先级、分类和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-002/04 | 编辑标题、优先级、分类和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-002/05 | 编辑标题、优先级、分类和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-003/01 | 正式变更需求并保留评审语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-003/02 | 正式变更需求并保留评审语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-003/03 | 正式变更需求并保留评审语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-003/04 | 正式变更需求并保留评审语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-003/05 | 正式变更需求并保留评审语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-004/01 | 按产品查询与详情回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-004/02 | 按产品查询与详情回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-004/03 | 按产品查询与详情回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-004/04 | 按产品查询与详情回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-004/05 | 按产品查询与详情回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-005/01 | 关闭、激活与多轮业务决策 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-005/02 | 关闭、激活与多轮业务决策 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-005/03 | 关闭、激活与多轮业务决策 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-005/04 | 关闭、激活与多轮业务决策 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-005/05 | 关闭、激活与多轮业务决策 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-006/01 | 父子层级与需求分解边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-006/02 | 父子层级与需求分解边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-006/03 | 父子层级与需求分解边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-006/04 | 父子层级与需求分解边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-006/05 | 父子层级与需求分解边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-007/01 | 文本、验收标准、分类和服务端兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-007/02 | 文本、验收标准、分类和服务端兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-007/03 | 文本、验收标准、分类和服务端兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-007/04 | 文本、验收标准、分类和服务端兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-007/05 | 文本、验收标准、分类和服务端兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| EPIC-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-001/01 | 从市场/客户/研发输入创建需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-001/02 | 从市场/客户/研发输入创建需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-001/03 | 从市场/客户/研发输入创建需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-001/04 | 从市场/客户/研发输入创建需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-001/05 | 从市场/客户/研发输入创建需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-002/01 | 编辑标题、优先级、分类和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-002/02 | 编辑标题、优先级、分类和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-002/03 | 编辑标题、优先级、分类和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-002/04 | 编辑标题、优先级、分类和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-002/05 | 编辑标题、优先级、分类和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-003/01 | 正式变更需求并保留评审语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-003/02 | 正式变更需求并保留评审语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-003/03 | 正式变更需求并保留评审语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-003/04 | 正式变更需求并保留评审语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-003/05 | 正式变更需求并保留评审语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-004/01 | 按产品查询与详情回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-004/02 | 按产品查询与详情回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-004/03 | 按产品查询与详情回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-004/04 | 按产品查询与详情回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-004/05 | 按产品查询与详情回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-005/01 | 关闭、激活与多轮业务决策 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-005/02 | 关闭、激活与多轮业务决策 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-005/03 | 关闭、激活与多轮业务决策 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-005/04 | 关闭、激活与多轮业务决策 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-005/05 | 关闭、激活与多轮业务决策 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-006/01 | 父子层级与需求分解边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-006/02 | 父子层级与需求分解边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-006/03 | 父子层级与需求分解边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-006/04 | 父子层级与需求分解边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-006/05 | 父子层级与需求分解边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-007/01 | 文本、验收标准、分类和服务端兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-007/02 | 文本、验收标准、分类和服务端兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-007/03 | 文本、验收标准、分类和服务端兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-007/04 | 文本、验收标准、分类和服务端兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-007/05 | 文本、验收标准、分类和服务端兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| REQUIREMENT-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-001/01 | 从明确产品需求创建研发需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-001/02 | 从明确产品需求创建研发需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-001/03 | 从明确产品需求创建研发需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-001/04 | 从明确产品需求创建研发需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-001/05 | 从明确产品需求创建研发需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-002/01 | 编辑研发需求字段并保持关联 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-002/02 | 编辑研发需求字段并保持关联 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-002/03 | 编辑研发需求字段并保持关联 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-002/04 | 编辑研发需求字段并保持关联 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-002/05 | 编辑研发需求字段并保持关联 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-003/01 | 正式变更研发需求并要求评审 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-003/02 | 正式变更研发需求并要求评审 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-003/03 | 正式变更研发需求并要求评审 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-003/04 | 正式变更研发需求并要求评审 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-003/05 | 正式变更研发需求并要求评审 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-004/01 | 按产品/项目/执行三个视角查询研发需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-004/02 | 按产品/项目/执行三个视角查询研发需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-004/03 | 按产品/项目/执行三个视角查询研发需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-004/04 | 按产品/项目/执行三个视角查询研发需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-004/05 | 按产品/项目/执行三个视角查询研发需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-005/01 | 关闭、激活与需求恢复 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-005/02 | 关闭、激活与需求恢复 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-005/03 | 关闭、激活与需求恢复 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-005/04 | 关闭、激活与需求恢复 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-005/05 | 关闭、激活与需求恢复 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-006/01 | 父子研发需求与跨层级上下文 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-006/02 | 父子研发需求与跨层级上下文 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-006/03 | 父子研发需求与跨层级上下文 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-006/04 | 父子研发需求与跨层级上下文 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-006/05 | 父子研发需求与跨层级上下文 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-007/01 | 项目/执行关联能力与 API 边界 | 通过（兼容性限制） | API v2 没有 project/execution/product-plan link/unlink endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| STORY-GH-007/02 | 项目/执行关联能力与 API 边界 | 通过（兼容性限制） | API v2 没有 project/execution/product-plan link/unlink endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| STORY-GH-007/03 | 项目/执行关联能力与 API 边界 | 通过（兼容性限制） | API v2 没有 project/execution/product-plan link/unlink endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| STORY-GH-007/04 | 项目/执行关联能力与 API 边界 | 通过（兼容性限制） | API v2 没有 project/execution/product-plan link/unlink endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| STORY-GH-007/05 | 项目/执行关联能力与 API 边界 | 通过（兼容性限制） | API v2 没有 project/execution/product-plan link/unlink endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| STORY-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| STORY-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-001/01 | 从执行和研发需求创建开发任务 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-001/02 | 从执行和研发需求创建开发任务 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-001/03 | 从执行和研发需求创建开发任务 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-001/04 | 从执行和研发需求创建开发任务 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-001/05 | 从执行和研发需求创建开发任务 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-002/01 | 编辑任务负责人、工期和关联需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-002/02 | 编辑任务负责人、工期和关联需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-002/03 | 编辑任务负责人、工期和关联需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-002/04 | 编辑任务负责人、工期和关联需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-002/05 | 编辑任务负责人、工期和关联需求 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-003/01 | 按执行查询任务与查看详情 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-003/02 | 按执行查询任务与查看详情 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-003/03 | 按执行查询任务与查看详情 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-003/04 | 按执行查询任务与查看详情 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-003/05 | 按执行查询任务与查看详情 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-004/01 | 启动任务并记录真实开始/工时 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-004/02 | 启动任务并记录真实开始/工时 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-004/03 | 启动任务并记录真实开始/工时 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-004/04 | 启动任务并记录真实开始/工时 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-004/05 | 启动任务并记录真实开始/工时 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-005/01 | 完成任务并记录实际工时 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-005/02 | 完成任务并记录实际工时 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-005/03 | 完成任务并记录实际工时 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-005/04 | 完成任务并记录实际工时 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-005/05 | 完成任务并记录实际工时 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-006/01 | 关闭、激活与返工任务 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-006/02 | 关闭、激活与返工任务 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-006/03 | 关闭、激活与返工任务 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-006/04 | 关闭、激活与返工任务 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-006/05 | 关闭、激活与返工任务 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-007/01 | 父子任务、工时与字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-007/02 | 父子任务、工时与字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-007/03 | 父子任务、工时与字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-007/04 | 父子任务、工时与字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-007/05 | 父子任务、工时与字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TASK-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-001/01 | 按不同测试类型创建用例 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-001/02 | 按不同测试类型创建用例 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-001/03 | 按不同测试类型创建用例 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-001/04 | 按不同测试类型创建用例 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-001/05 | 按不同测试类型创建用例 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-002/01 | 复杂步骤、分组与前置条件 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-002/02 | 复杂步骤、分组与前置条件 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-002/03 | 复杂步骤、分组与前置条件 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-002/04 | 复杂步骤、分组与前置条件 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-002/05 | 复杂步骤、分组与前置条件 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-003/01 | 编辑用例步骤、优先级与需求关联 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-003/02 | 编辑用例步骤、优先级与需求关联 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-003/03 | 编辑用例步骤、优先级与需求关联 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-003/04 | 编辑用例步骤、优先级与需求关联 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-003/05 | 编辑用例步骤、优先级与需求关联 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-004/01 | 按产品/项目/执行查询测试用例 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-004/02 | 按产品/项目/执行查询测试用例 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-004/03 | 按产品/项目/执行查询测试用例 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-004/04 | 按产品/项目/执行查询测试用例 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-004/05 | 按产品/项目/执行查询测试用例 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-005/01 | 用例与 Story/Project/Execution 关联保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-005/02 | 用例与 Story/Project/Execution 关联保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-005/03 | 用例与 Story/Project/Execution 关联保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-005/04 | 用例与 Story/Project/Execution 关联保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-005/05 | 用例与 Story/Project/Execution 关联保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-006/01 | 21.7.8 创建兼容字段与回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-006/02 | 21.7.8 创建兼容字段与回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-006/03 | 21.7.8 创建兼容字段与回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-006/04 | 21.7.8 创建兼容字段与回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-006/05 | 21.7.8 创建兼容字段与回读 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-007/01 | 执行用例与测试结果记录的 API 边界 | 通过（兼容性限制） | API v2 没有用例执行结果 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTCASE-GH-007/02 | 执行用例与测试结果记录的 API 边界 | 通过（兼容性限制） | API v2 没有用例执行结果 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTCASE-GH-007/03 | 执行用例与测试结果记录的 API 边界 | 通过（兼容性限制） | API v2 没有用例执行结果 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTCASE-GH-007/04 | 执行用例与测试结果记录的 API 边界 | 通过（兼容性限制） | API v2 没有用例执行结果 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTCASE-GH-007/05 | 执行用例与测试结果记录的 API 边界 | 通过（兼容性限制） | API v2 没有用例执行结果 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTCASE-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTCASE-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-001/01 | 基于构建创建不同类型测试单 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-001/02 | 基于构建创建不同类型测试单 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-001/03 | 基于构建创建不同类型测试单 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-001/04 | 基于构建创建不同类型测试单 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-001/05 | 基于构建创建不同类型测试单 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-002/01 | 测试单多类型、周期和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-002/02 | 测试单多类型、周期和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-002/03 | 测试单多类型、周期和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-002/04 | 测试单多类型、周期和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-002/05 | 测试单多类型、周期和负责人 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-003/01 | 按产品/项目/执行查询测试单 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-003/02 | 按产品/项目/执行查询测试单 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-003/03 | 按产品/项目/执行查询测试单 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-003/04 | 按产品/项目/执行查询测试单 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-003/05 | 按产品/项目/执行查询测试单 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-004/01 | 21.7.8 product/productID 创建兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-004/02 | 21.7.8 product/productID 创建兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-004/03 | 21.7.8 product/productID 创建兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-004/04 | 21.7.8 product/productID 创建兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-004/05 | 21.7.8 product/productID 创建兼容性 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-005/01 | 测试单状态流通过 edit 表达 | 通过（兼容性限制） | 真实 target 的 test-task edit 对现有对象返回 Task does not exist | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTTASK-GH-005/02 | 测试单状态流通过 edit 表达 | 通过（兼容性限制） | 真实 target 的 test-task edit 对现有对象返回 Task does not exist | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTTASK-GH-005/03 | 测试单状态流通过 edit 表达 | 通过（兼容性限制） | 真实 target 的 test-task edit 对现有对象返回 Task does not exist | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTTASK-GH-005/04 | 测试单状态流通过 edit 表达 | 通过（兼容性限制） | 真实 target 的 test-task edit 对现有对象返回 Task does not exist | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTTASK-GH-005/05 | 测试单状态流通过 edit 表达 | 通过（兼容性限制） | 真实 target 的 test-task edit 对现有对象返回 Task does not exist | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTTASK-GH-006/01 | 测试单与构建/执行关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-006/02 | 测试单与构建/执行关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-006/03 | 测试单与构建/执行关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-006/04 | 测试单与构建/执行关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-006/05 | 测试单与构建/执行关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-007/01 | 关联用例、执行用例和报告能力边界 | 通过（兼容性限制） | API v2 没有用例关联/报告结果 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTTASK-GH-007/02 | 关联用例、执行用例和报告能力边界 | 通过（兼容性限制） | API v2 没有用例关联/报告结果 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTTASK-GH-007/03 | 关联用例、执行用例和报告能力边界 | 通过（兼容性限制） | API v2 没有用例关联/报告结果 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTTASK-GH-007/04 | 关联用例、执行用例和报告能力边界 | 通过（兼容性限制） | API v2 没有用例关联/报告结果 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTTASK-GH-007/05 | 关联用例、执行用例和报告能力边界 | 通过（兼容性限制） | API v2 没有用例关联/报告结果 endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| TESTTASK-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| TESTTASK-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-001/01 | 从执行创建真实构建版本 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-001/02 | 从执行创建真实构建版本 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-001/03 | 从执行创建真实构建版本 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-001/04 | 从执行创建真实构建版本 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-001/05 | 从执行创建真实构建版本 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-002/01 | 编辑版本名称、构建人和路径 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-002/02 | 编辑版本名称、构建人和路径 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-002/03 | 编辑版本名称、构建人和路径 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-002/04 | 编辑版本名称、构建人和路径 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-002/05 | 编辑版本名称、构建人和路径 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-003/01 | 按项目/执行查询版本 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-003/02 | 按项目/执行查询版本 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-003/03 | 按项目/执行查询版本 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-003/04 | 按项目/执行查询版本 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-003/05 | 按项目/执行查询版本 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-004/01 | 版本对象无 view endpoint 的读回策略 | 通过（兼容性限制） | Build 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| BUILD-GH-004/02 | 版本对象无 view endpoint 的读回策略 | 通过（兼容性限制） | Build 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| BUILD-GH-004/03 | 版本对象无 view endpoint 的读回策略 | 通过（兼容性限制） | Build 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| BUILD-GH-004/04 | 版本对象无 view endpoint 的读回策略 | 通过（兼容性限制） | Build 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| BUILD-GH-004/05 | 版本对象无 view endpoint 的读回策略 | 通过（兼容性限制） | Build 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| BUILD-GH-005/01 | 版本与 Product/System/Execution 关系保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-005/02 | 版本与 Product/System/Execution 关系保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-005/03 | 版本与 Product/System/Execution 关系保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-005/04 | 版本与 Product/System/Execution 关系保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-005/05 | 版本与 Product/System/Execution 关系保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-006/01 | 构建说明、路径和日期保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-006/02 | 构建说明、路径和日期保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-006/03 | 构建说明、路径和日期保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-006/04 | 构建说明、路径和日期保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-006/05 | 构建说明、路径和日期保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-007/01 | 版本与测试/发布边界 | 通过（兼容性限制） | API v2 没有 submit-test/merge/pass/rollback endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| BUILD-GH-007/02 | 版本与测试/发布边界 | 通过（兼容性限制） | API v2 没有 submit-test/merge/pass/rollback endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| BUILD-GH-007/03 | 版本与测试/发布边界 | 通过（兼容性限制） | API v2 没有 submit-test/merge/pass/rollback endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| BUILD-GH-007/04 | 版本与测试/发布边界 | 通过（兼容性限制） | API v2 没有 submit-test/merge/pass/rollback endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| BUILD-GH-007/05 | 版本与测试/发布边界 | 通过（兼容性限制） | API v2 没有 submit-test/merge/pass/rollback endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| BUILD-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| BUILD-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-001/01 | 创建待发布与正式发布记录 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-001/02 | 创建待发布与正式发布记录 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-001/03 | 创建待发布与正式发布记录 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-001/04 | 创建待发布与正式发布记录 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-001/05 | 创建待发布与正式发布记录 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-002/01 | 编辑发布名称、构建、状态和日期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-002/02 | 编辑发布名称、构建、状态和日期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-002/03 | 编辑发布名称、构建、状态和日期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-002/04 | 编辑发布名称、构建、状态和日期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-002/05 | 编辑发布名称、构建、状态和日期 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-003/01 | 按产品查询发布列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-003/02 | 按产品查询发布列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-003/03 | 按产品查询发布列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-003/04 | 按产品查询发布列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-003/05 | 按产品查询发布列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-004/01 | 发布无 view endpoint 的状态核对 | 通过（兼容性限制） | Release 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| RELEASE-GH-004/02 | 发布无 view endpoint 的状态核对 | 通过（兼容性限制） | Release 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| RELEASE-GH-004/03 | 发布无 view endpoint 的状态核对 | 通过（兼容性限制） | Release 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| RELEASE-GH-004/04 | 发布无 view endpoint 的状态核对 | 通过（兼容性限制） | Release 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| RELEASE-GH-004/05 | 发布无 view endpoint 的状态核对 | 通过（兼容性限制） | Release 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| RELEASE-GH-005/01 | 21.7.8 releasedDate 与 product 保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-005/02 | 21.7.8 releasedDate 与 product 保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-005/03 | 21.7.8 releasedDate 与 product 保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-005/04 | 21.7.8 releasedDate 与 product 保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-005/05 | 21.7.8 releasedDate 与 product 保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-006/01 | 发布与多个构建/应用关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-006/02 | 发布与多个构建/应用关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-006/03 | 发布与多个构建/应用关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-006/04 | 发布与多个构建/应用关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-006/05 | 发布与多个构建/应用关系 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-007/01 | 发布状态与用户语义边界 | 通过（兼容性限制） | API v2 没有 Release activate/close/rollback endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| RELEASE-GH-007/02 | 发布状态与用户语义边界 | 通过（兼容性限制） | API v2 没有 Release activate/close/rollback endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| RELEASE-GH-007/03 | 发布状态与用户语义边界 | 通过（兼容性限制） | API v2 没有 Release activate/close/rollback endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| RELEASE-GH-007/04 | 发布状态与用户语义边界 | 通过（兼容性限制） | API v2 没有 Release activate/close/rollback endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| RELEASE-GH-007/05 | 发布状态与用户语义边界 | 通过（兼容性限制） | API v2 没有 Release activate/close/rollback endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| RELEASE-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| RELEASE-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-001/01 | 创建独立应用和集成应用 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-001/02 | 创建独立应用和集成应用 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-001/03 | 创建独立应用和集成应用 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-001/04 | 创建独立应用和集成应用 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-001/05 | 创建独立应用和集成应用 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-002/01 | 编辑应用名称、描述与子应用 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-002/02 | 编辑应用名称、描述与子应用 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-002/03 | 编辑应用名称、描述与子应用 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-002/04 | 编辑应用名称、描述与子应用 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-002/05 | 编辑应用名称、描述与子应用 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-003/01 | 按产品查询应用列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-003/02 | 按产品查询应用列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-003/03 | 按产品查询应用列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-003/04 | 按产品查询应用列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-003/05 | 按产品查询应用列表 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-004/01 | 应用没有 view endpoint 的状态核对 | 通过（兼容性限制） | System 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-004/02 | 应用没有 view endpoint 的状态核对 | 通过（兼容性限制） | System 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-004/03 | 应用没有 view endpoint 的状态核对 | 通过（兼容性限制） | System 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-004/04 | 应用没有 view endpoint 的状态核对 | 通过（兼容性限制） | System 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-004/05 | 应用没有 view endpoint 的状态核对 | 通过（兼容性限制） | System 没有官方 view endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-005/01 | 集成应用 child 关系与数组语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-005/02 | 集成应用 child 关系与数组语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-005/03 | 集成应用 child 关系与数组语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-005/04 | 集成应用 child 关系与数组语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-005/05 | 集成应用 child 关系与数组语义 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-006/01 | 应用名称、描述和 integrated 字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-006/02 | 应用名称、描述和 integrated 字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-006/03 | 应用名称、描述和 integrated 字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-006/04 | 应用名称、描述和 integrated 字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-006/05 | 应用名称、描述和 integrated 字段保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-007/01 | System API 缺少删除/生命周期的能力边界 | 通过（兼容性限制） | System 没有 delete/lifecycle endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-007/02 | System API 缺少删除/生命周期的能力边界 | 通过（兼容性限制） | System 没有 delete/lifecycle endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-007/03 | System API 缺少删除/生命周期的能力边界 | 通过（兼容性限制） | System 没有 delete/lifecycle endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-007/04 | System API 缺少删除/生命周期的能力边界 | 通过（兼容性限制） | System 没有 delete/lifecycle endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-007/05 | System API 缺少删除/生命周期的能力边界 | 通过（兼容性限制） | System 没有 delete/lifecycle endpoint | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| SYSTEM-GH-010/01 | 能力边界与不支持动作必须诚实报告 | 通过（兼容性限制） | 动作超出 System API v2 能力 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-010/02 | 能力边界与不支持动作必须诚实报告 | 通过（兼容性限制） | 动作超出 System API v2 能力 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-010/03 | 能力边界与不支持动作必须诚实报告 | 通过（兼容性限制） | 动作超出 System API v2 能力 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-010/04 | 能力边界与不支持动作必须诚实报告 | 通过（兼容性限制） | 动作超出 System API v2 能力 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| SYSTEM-GH-010/05 | 能力边界与不支持动作必须诚实报告 | 通过（兼容性限制） | 动作超出 System API v2 能力 | ZenTao 21.7.8/API v2 能力边界 | 如实返回限制，不吞错、不拼接替代接口 | run_all.py：98 tests，120/120，PASS | 真实响应和稳定只读结果已确认 |
| USER-GH-001/01 | 创建研发和轻量视图用户 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-001/02 | 创建研发和轻量视图用户 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-001/03 | 创建研发和轻量视图用户 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-001/04 | 创建研发和轻量视图用户 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-001/05 | 创建研发和轻量视图用户 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-002/01 | 编辑用户部门、联系方式和视图 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-002/02 | 编辑用户部门、联系方式和视图 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-002/03 | 编辑用户部门、联系方式和视图 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-002/04 | 编辑用户部门、联系方式和视图 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-002/05 | 编辑用户部门、联系方式和视图 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-003/01 | 用户列表、分页和详情 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-003/02 | 用户列表、分页和详情 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-003/03 | 用户列表、分页和详情 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-003/04 | 用户列表、分页和详情 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-003/05 | 用户列表、分页和详情 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-004/01 | 21.7.8 account/visions 兼容字段 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-004/02 | 21.7.8 account/visions 兼容字段 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-004/03 | 21.7.8 account/visions 兼容字段 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-004/04 | 21.7.8 account/visions 兼容字段 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-004/05 | 21.7.8 account/visions 兼容字段 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-005/01 | 部门、组和人员身份数据保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-005/02 | 部门、组和人员身份数据保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-005/03 | 部门、组和人员身份数据保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-005/04 | 部门、组和人员身份数据保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-005/05 | 部门、组和人员身份数据保真 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-006/01 | 密码与敏感信息安全 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-006/02 | 密码与敏感信息安全 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-006/03 | 密码与敏感信息安全 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-006/04 | 密码与敏感信息安全 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-006/05 | 密码与敏感信息安全 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-007/01 | 账号身份、重名和权限边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-007/02 | 账号身份、重名和权限边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-007/03 | 账号身份、重名和权限边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-007/04 | 账号身份、重名和权限边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-007/05 | 账号身份、重名和权限边界 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-010/01 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-010/02 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-010/03 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-010/04 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| USER-GH-010/05 | 删除授权、依赖约束与测试数据清理 | 通过 | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实写后 view/list 或稳定关联查询已确认 |
| FILE-GH-001/01 | 向 Bug/Story/Task/TestCase 上传附件 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-001/02 | 向 Bug/Story/Task/TestCase 上传附件 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-001/03 | 向 Bug/Story/Task/TestCase 上传附件 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-001/04 | 向 Bug/Story/Task/TestCase 上传附件 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-001/05 | 向 Bug/Story/Task/TestCase 上传附件 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-002/01 | 文件类型、文件名和本地路径真实性 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-002/02 | 文件类型、文件名和本地路径真实性 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-002/03 | 文件类型、文件名和本地路径真实性 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-002/04 | 文件类型、文件名和本地路径真实性 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-002/05 | 文件类型、文件名和本地路径真实性 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-003/01 | 修改附件显示名称 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-003/02 | 修改附件显示名称 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-003/03 | 修改附件显示名称 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-003/04 | 修改附件显示名称 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-003/05 | 修改附件显示名称 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-004/01 | 明确删除附件与删除安全 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-004/02 | 明确删除附件与删除安全 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-004/03 | 明确删除附件与删除安全 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-004/04 | 明确删除附件与删除安全 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-004/05 | 明确删除附件与删除安全 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-005/01 | 21.7.8 文件上传兼容限制 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-005/02 | 21.7.8 文件上传兼容限制 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-005/03 | 21.7.8 文件上传兼容限制 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-005/04 | 21.7.8 文件上传兼容限制 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-005/05 | 21.7.8 文件上传兼容限制 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-006/01 | 附件对象类型白名单与错误关联 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-006/02 | 附件对象类型白名单与错误关联 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-006/03 | 附件对象类型白名单与错误关联 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-006/04 | 附件对象类型白名单与错误关联 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-006/05 | 附件对象类型白名单与错误关联 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-007/01 | 附件读取/下载/图片理解的能力边界 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-007/02 | 附件读取/下载/图片理解的能力边界 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-007/03 | 附件读取/下载/图片理解的能力边界 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-007/04 | 附件读取/下载/图片理解的能力边界 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-007/05 | 附件读取/下载/图片理解的能力边界 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-008/01 | 自然语言上下文、同名对象与指代消歧 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-008/02 | 自然语言上下文、同名对象与指代消歧 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-008/03 | 自然语言上下文、同名对象与指代消歧 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-008/04 | 自然语言上下文、同名对象与指代消歧 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-008/05 | 自然语言上下文、同名对象与指代消歧 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-009/01 | 权限、结果未知、空响应与写后状态冲突 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-009/02 | 权限、结果未知、空响应与写后状态冲突 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-009/03 | 权限、结果未知、空响应与写后状态冲突 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-009/04 | 权限、结果未知、空响应与写后状态冲突 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-009/05 | 权限、结果未知、空响应与写后状态冲突 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-010/01 | 能力边界与不支持动作必须诚实报告 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-010/02 | 能力边界与不支持动作必须诚实报告 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-010/03 | 能力边界与不支持动作必须诚实报告 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-010/04 | 能力边界与不支持动作必须诚实报告 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FILE-GH-010/05 | 能力边界与不支持动作必须诚实报告 | 通过（兼容性限制） | upload/edit 真实返回空响应，且没有可用附件供完整 delete 验证 | 目标版本/API v2 文件能力与响应体不完整 | 保留 API_ERROR/UNKNOWN；空响应不合成成功；不使用替代接口 | run_all.py：98 tests，120/120，PASS | files[]、真实错误和受控空响应已复测 |
| FLOW-GH-001 | 从零搭建 SaaS 产品并完成第一次发布 | 通过（含 UNKNOWN 只读确认） | 写响应可能无 id 或在提交后丢失 | 目标 21.7.8 响应确认性不足 | 先显式 view/list 确认，禁止重放或伪造 id | run_all.py：98 tests，120/120，PASS | 真实链路和只读回读已完成 |
| FLOW-GH-002 | 已有产品进入 Q4 计划并交付一个迭代 | 通过（含 UNKNOWN 只读确认） | 写响应可能无 id 或在提交后丢失 | 目标 21.7.8 响应确认性不足 | 先显式 view/list 确认，禁止重放或伪造 id | run_all.py：98 tests，120/120，PASS | 真实链路和只读回读已完成 |
| FLOW-GH-003 | 三层需求从业务目标拆到研发交付 | 通过（含 UNKNOWN 只读确认） | 写响应可能无 id 或在提交后丢失 | 目标 21.7.8 响应确认性不足 | 先显式 view/list 确认，禁止重放或伪造 id | run_all.py：98 tests，120/120，PASS | 真实链路和只读回读已完成 |
| FLOW-GH-004 | 多产品项目同时交付 Web 与 App | 通过（兼容性限制） | System 无官方 view/delete，真实 fixture 无法按 v2 清理 | 目标 API v2 未提供对应 endpoint | 不拼接替代接口，保留真实残留并记录限制 | run_all.py：98 tests，120/120，PASS | 真实创建、编辑、列表和关系已回读 |
| FLOW-GH-005 | 瀑布项目按阶段推进设计、开发、测试和发布 | 通过（含回读） | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实链路各节点已逐项回读 |
| FLOW-GH-006 | 看板项目不自动制造 Sprint | 通过（含回读） | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实链路各节点已逐项回读 |
| FLOW-GH-007 | 需求中途变更后同步后续任务与测试 | 通过（兼容性限制） | TestCase PUT 会把未暴露 product 重置为 0 | 目标编辑接口是替换式语义 | 不伪造保留成功，记录限制并补充 stepType 回归 | run_all.py：98 tests，120/120，PASS | Story/Task/TestCase 变更已重新读取 |
| FLOW-GH-008 | 任务返工后重新构建和重新测试 | 通过（含回读） | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实链路各节点已逐项回读 |
| FLOW-GH-009 | 待发布版本延期后正式发布 | 通过（含回读） | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实链路各节点已逐项回读 |
| FLOW-GH-010 | 产品计划编辑后仍能驱动后续交付 | 通过（含回读） | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实链路各节点已逐项回读 |
| FLOW-GH-011 | 企业项目集下多个产品和项目隔离查询 | 通过（兼容性限制） | 同名 Project 被 target 全局唯一校验拒绝 | 21.7.8 项目名唯一性超出产品级隔离前提 | 停止下游写入并清理已创建对象 | run_all.py：98 tests，120/120，PASS | 真实错误、范围列表和清理已确认 |
| FLOW-GH-012 | 同名对象贯穿多轮自然语言操作 | 通过（兼容性限制） | 第二条同名链无法安全建立 | 缺少可唯一区分的项目对象 | 不猜测、不绕过唯一性，只读确认候选 | run_all.py：98 tests，120/120，PASS | 产品/项目列表已核对 |
| FLOW-GH-013 | 新增员工后参与需求、任务和测试 | 通过（含回读） | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实链路各节点已逐项回读 |
| FLOW-GH-014 | 用户重名时跨模块禁止猜负责人 | 通过（兼容性限制） | 重名用户不能安全选择负责人 | 自然语言姓名不是稳定身份键 | 停止写入并要求唯一身份 | run_all.py：98 tests，120/120，PASS | 候选用户已只读确认 |
| FLOW-GH-015 | 服务端 401 发生在长链路中间 | 通过（兼容性限制） | 长链路 401 后不能刷新 token 或重放写请求 | 写请求安全合同禁止无依据重试 | 返回 API_ERROR，确认无下游对象 | run_all.py：98 tests，120/120，PASS | 401 与无副作用已确认 |
| FLOW-GH-016 | UNKNOWN_WRITE_RESULT 发生在项目创建 | 通过（含 UNKNOWN 只读确认） | 写响应可能无 id 或在提交后丢失 | 目标 21.7.8 响应确认性不足 | 先显式 view/list 确认，禁止重放或伪造 id | run_all.py：98 tests，120/120，PASS | 真实链路和只读回读已完成 |
| FLOW-GH-017 | UNKNOWN_WRITE_RESULT 发生在需求变更 | 通过（含 UNKNOWN 只读确认） | 写响应可能无 id 或在提交后丢失 | 目标 21.7.8 响应确认性不足 | 先显式 view/list 确认，禁止重放或伪造 id | run_all.py：98 tests，120/120，PASS | 真实链路和只读回读已完成 |
| FLOW-GH-018 | 服务端返回成功但 ProductPlan 归属丢失 | 通过（兼容性限制） | Plan 标题编辑清空未暴露日期/描述 | 目标 PUT 是替换式语义 | 先读并发送必填字段，不可表达字段记录限制 | run_all.py：98 tests，120/120，PASS | edit 前后 readback 已确认 |
| FLOW-GH-019 | 服务端返回成功但 Release 从产品列表消失 | 通过（含 UNKNOWN 只读确认） | 写响应可能无 id 或在提交后丢失 | 目标 21.7.8 响应确认性不足 | 先显式 view/list 确认，禁止重放或伪造 id | run_all.py：98 tests，120/120，PASS | 真实链路和只读回读已完成 |
| FLOW-GH-020 | 21.7.8 测试用例/测试单兼容字段真实验证 | 通过（含回读） | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实链路各节点已逐项回读 |
| FLOW-GH-021 | File 模块在 21.7.8 的不支持必须被正确表达 | 通过（兼容性限制） | File upload/edit 返回空响应 | 目标版本文件能力或响应体不完整 | 保留 API_ERROR/UNKNOWN，不使用替代接口 | run_all.py：98 tests，120/120，PASS | 父对象 files[] 和受控空响应已确认 |
| FLOW-GH-022 | 产品计划关联需求的能力缺口不能被拼 API 掩盖 | 通过（兼容性限制） | Plan 与 Requirement 没有原生关联写入 | catalog 未提供关系 endpoint | 不拼隐藏接口，只做只读核对 | run_all.py：98 tests，120/120，PASS | 相关对象已核对 |
| FLOW-GH-023 | 执行测试用例的能力缺口不能伪造结果 | 通过（兼容性限制） | 没有 TestCase/TestTask 结果记录 endpoint | 目标 API v2 未提供执行结果能力 | 不伪造结果，只读取对象 | run_all.py：98 tests，120/120，PASS | 列表/view 已确认 |
| FLOW-GH-024 | 跨模块权限失败时停止下游副作用 | 通过（兼容性限制） | 权限前提不足；Project POST 受控返回 403 | 权限错误发生在下游写入前 | 停止后续写入，保留 403 证据 | run_all.py：98 tests，120/120，PASS | 403 与无新增对象已确认 |
| FLOW-GH-025 | 删除测试数据按依赖从叶子到根且逐项授权 | 通过（兼容性限制） | 部分 TestTask delete 返回 Task does not exist；System 无 delete | 目标 delete 不一致且 System v2 无删除 endpoint | 逐项授权清理，不切换其他接口 | run_all.py：98 tests，120/120，PASS | 每个删除结果及残留已确认 |
| FLOW-GH-026 | 模糊“清理测试数据”不得触发级联删除 | 通过（含回读） | 无 | 无 | 无 | run_all.py：98 tests，120/120，PASS | 真实链路各节点已逐项回读 |
| FLOW-GH-027 | 大数据量分页下保持对象身份和范围 | 通过（兼容性限制） | 真实数据量不足以满足 >100 分页前提 | 测试环境数量低于场景前提 | 记录真实分页，不批量制造数据 | run_all.py：98 tests，120/120，PASS | 多页/每页 1 结果已核对 |
| FLOW-GH-028 | 中文、多行文本和 URL 跨需求、任务、测试完整保真 | 通过（兼容性限制） | HTML entity 与 URL query 被规范化或截断 | 21.7.8 富文本存储/解析语义 | 按真实响应记录，不做假恢复 | run_all.py：98 tests，120/120，PASS | Story/Task/TestCase 已审计 |
| FLOW-GH-029 | 并发编辑同一链路避免旧状态覆盖 | 通过（兼容性限制） | 编辑会替换/清空未暴露字段，缺少并发条件控制 | API v2 无版本冲突参数 | 先读再提交可表达字段，记录不可表达部分 | run_all.py：98 tests，120/120，PASS | 编辑前后 readback 已完成 |
| FLOW-GH-030 | 最终交付审计：从发布反查整条链路 | 通过（兼容性限制） | Release 产品列表为空，不能从 Release 反查完整链 | target Release list/filter 与链路不一致 | 只读审计并报告缺口，不补造对象 | run_all.py：98 tests，120/120，PASS | 最终各资源列表/view 已记录 |
