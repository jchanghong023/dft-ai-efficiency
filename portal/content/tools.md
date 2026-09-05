# 内置工具

工具由 Agent 按本会话 schema 调用，不能把 `wiki` 或 `task` JSON 当作 Shell 命令。`/tools` 显示当前实际可见工具；模式、启动参数和本地依赖可能使某些工具不可用。

## 文件与代码

| 工具 | 用途 | 典型场景 / 输入 | 输出与状态影响 |
|---|---|---|---|
| read | 读取文件或资源 | 读取指定路径、行段、内部 URI | 内容及位置；URL 可联网 |
| grep | 文本检索 | 用信号名、函数名、错误消息限制目录检索 | 命中路径和行；只读 |
| glob | 按模式找文件 | 查找 RTL、测试或配置文件 | 路径列表；只读 |
| edit / write | 修改现有文件 / 写入文件 | 已确定范围的实现与测试 | 文件变更；需要核对 diff |
| ast_grep / ast_edit | 语法结构检索 / 编辑 | 避免纯文本替换误伤语法 | 结构化命中 / 实际代码修改 |
| lsp | 语言服务 | 定义、引用、诊断及重命名等操作 | 查询可只读，重命名/格式化可改文件；需语言服务可用 |
| bash | 执行实际命令 | 编译、UT、已有工具入口 | 退出码与输出；可能修改文件或运行进程 |

## Wiki：先检索，再读证据

`wiki` 读取本机 `docs.db` 中的索引。公共包不携带公司数据库。FTS 模式仅支持 `search`、`read` 和 `status`；结构化索引还可使用 `lookup`、`relations`、`conflicts`。多个索引并存时查询需指定 `index`。

Agent 工具参数示意（索引名须替换为本机真实名称）：

```json
{"op":"search","index":"team-docs","query":"dft_lgc_rst_n","limit":10}
```

命中结果含索引、section/evidence 标识和源文件位置。使用返回的标识 `read`，再从团队上下文中的实际原文目录核对接口和周边约束。FTS 命中不等于语义已证实；不可因零结果编造工具选项。

## Task：按职责委派

`task` 默认一次调用启动一个 Agent；批量形状只有启用 `task.batch` 时使用。常用输入是 `agent` 与 `task`，必要时传递已有调查摘要。不要照搬其他产品的子 Agent schema。

```json
{"agent":"document-worker","task":"只读定位当前模块复位约束，返回代码和文档位置及已有测试入口"}
```

返回的任务结果和日志并不保证成功，应核对退出状态、实际文件和测试证据。仅在独立工作能受益时并行，依赖调查结果的实现与验证顺序执行。参阅[团队公共能力](team.html)与[内置 Agent](agents.html)。

## 其他能力

`eval` 提供编程式工具编排；`web_search` 用于可联网的公开资料；`todo` 管理任务清单；`hub` 管理运行中的 Agent/后台工作；`security_scan` 运行原生安全扫描。只读意图不等于工具隔离，特别是 Shell、eval、hub 和有编辑操作的语言服务。

以下为该版工具工厂清单；部分工具按配置动态启用，隐藏工具只在相应模式暴露：

<!-- inventory:tools -->

依据：[工具工厂](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/tools/index.ts)、[Wiki schema](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/tools/wiki.ts)、[Task 实现](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/task/index.ts)。
