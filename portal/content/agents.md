# 内置 Agent

本版实际注册 **scout、reviewer、security-reviewer、task、sonic** 五个 Task Agent。最终方案原列出的 `designer`、`librarian` 在 `v18.1.9+fork.170` 未注册，不能按内置 Agent 调用；设计与资料整理可由主会话或通用 task 承担，也可另行定义自有 Agent。

## 五个 Agent 的职责

| Agent | 主要职责与适用任务 | 是否只读 | 用户指定方式 |
|---|---|---|---|
| scout | 快速代码勘察、模式检索、提供压缩上下文 | 工具列表为 read、grep、glob、web_search，属于源码的只读集合 | 适合；请通过 task 使用 scout 调查指定范围 |
| reviewer | 代码质量与安全审查 | 审查意图只读，但含 bash/lsp，不能当作强制只读隔离 | 适合审查，不作为实现 Worker |
| security-reviewer | 有证据的漏洞调查 | 提示意图只读；含 lsp，源码通用只读分类不会认定为严格只读 | 适合用户明确要求的安全调查 |
| task | 全能力、多步通用委派 | 否，可修改文件、执行工具并继续委派 | 适合明确范围的实现任务 |
| sonic | 机械性更新或数据收集 | 否，沿用通用 task 模板；不能因低推理定位视作只读 | 适合严格机械任务，不适合不确定设计 |

## 调用与配置

在对话中明确“请通过 task 使用 scout，只读定位模块入口并返回文件位置”。默认单任务工具参数示意：

```json
{"agent":"scout","task":"查找当前工程的复位路径及相关测试，只返回有证据的文件位置"}
```

`/agents` 是配置/查看 Agent 的面板，不是 `/scout` 命令；上述名称是 `task` 的 `agent` 选择值。批量形状和可用 Agent 受会话配置影响，按当前 schema 调用。

`scout` 和 `sonic` 使用 `@smol` 角色，`reviewer` 使用 `@slow`，`task` 使用 `@task`；角色指向个人配置，团队同步不覆盖它们。已有用户/项目同名 Agent 可以覆盖内置定义，以实际加载来源为准。

## 团队 Worker 单独管理

`document-worker`、`coding-worker`、`verification-worker` 来自本效率仓库，不是 Fork 内置 Agent。详见[团队公共能力](team.html)。

依据：[注册源码](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/task/agents.ts)、[只读分类](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/task/read-only-policy.ts)。
