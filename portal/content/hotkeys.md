# 常用快捷键

在 OMP 主输入框中按下组合键，不要把键名输入或粘贴进去。以下整理自[场景使用指南](usage-guide.html)，参考版本为 `v18.1.10+fork.172`；个人配置可能修改键位，使用 `/hotkeys` 查看当前绑定。

## 模型与推理

| 想做什么 | 默认快捷键 | 接下来怎么做 |
|---|---|---|
| 切换当前模型 | **Ctrl+T** | 输入模型名筛选，↑／↓ 选择，Enter 确认 |
| 配置 slow、Advisor 等模型角色 | **Alt+M** | 打开模型中心，选择角色与模型 |
| 在常用模型间轮换 | **Ctrl+P** | 按轮换列表切换，查看状态栏确认当前模型 |
| 显示或隐藏思考内容 | **Alt+P** | 只改变 thinking blocks 的显示，不改变推理强度 |
| 调整推理强度 | **Alt+,**（Alt 加逗号） | 循环切换 thinking level，查看状态栏确认档位 |

## 计划与执行

| 想做什么 | 默认快捷键 | 接下来怎么做 |
|---|---|---|
| 切换 Plan 模式状态 | **Shift+Tab** | 依次开启、暂停、关闭；看状态栏确认 |
| 切换 Main／Discuss | **Ctrl+0** | 空闲时切换；讨论用 Discuss，实施切回 Main |
| 查看 Agent 工作情况 | **← ←**（快速连按两次左箭头） | 输入框为空时打开 Agent Hub，查看任务和状态 |
| 展开工具调用详情 | **Ctrl+O** | 阅读执行输出；再次按下收起 |
| 打断当前执行 | **Esc** | 停止本轮，补充或纠正要求后继续 |

`Plan ⏸` 表示暂停，不是关闭。已有计划草稿时，离开规划还会要求确认；切换模式不等于批准计划，开始实施使用计划审阅界面的执行选项。

## 快捷键不可用时

先用 `/hotkeys` 查看当前绑定，确认是否被个人配置修改或终端拦截。模型选择可用 `/switch`，模型中心可用 `/model`，Plan 模式可用 `/plan`。

没有默认快捷键的操作仍使用斜杠命令，例如 Vibe、Advisor 开关、压缩和新会话。完整入口见[内置命令](commands.html)，实际工作流程见[场景使用指南](usage-guide.html)。

## 参考版本

键位依据：[fork.md](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.10%2Bfork.172/docs-zh-CN/fork.md)；通用键位补充参考[同版本键位定义](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.10%2Bfork.172/packages/coding-agent/src/config/keybindings.ts)。本机实际绑定以 `/hotkeys` 为准。
