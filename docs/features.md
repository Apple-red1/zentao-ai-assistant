# 功能概览

当前产品是面向 AI 的 ZenTao 项目管理 Skill 集合。

## `zentao`

基础 API Skill 覆盖 20 个资源、120 个 ZenTao API v2 endpoint；Token 是内部认证能力，其余官方资源通过统一 `<resource> <action> [scope] [parameters]` CLI 暴露。另提供对象关联资源获取和仓库内部 programmatic public facade。

## `zentao-statistics`

确定性统计、聚合、分页、去重和同类范围比较。第一版支持 Bug、Task、Story、Requirement、Test Case、Test Task、Ticket、Feedback。

## `zentao-personal`

当前或指定用户的个人工作概览、待办清单、Severity 1 / P1 Bug、逾期任务及日报/周报事实素材。

## `zentao-project-management`

Project / Execution 的资源概览、风险信号和开放事项工作量分布。默认不发明数值健康分或人员绩效结论。
