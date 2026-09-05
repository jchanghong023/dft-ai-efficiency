# CLI 与 TUI

CLI 是终端中的 `omp ...`；TUI 命令是在已经启动的 OMP 输入框中键入 `/...`。工具如 `wiki`、`task` 由 Agent 调用，不是 Shell 命令。

## 日常启动参数

| 命令 | 用途 | 主要参数与影响 |
|---|---|---|
| `omp` | 在当前项目交互开发 | 默认可调用本会话可见工具 |
| `omp --cwd /path/to/project` | 指定项目目录 | 不搬移项目文件 |
| `omp --model <模型或角色>` | 使用已配置模型 | 模糊模型名、提供方/模型名按本地可用配置解析 |
| `omp -c` | 继续上一次会话 | 恢复该目录相关会话 |
| `omp -r` | 选择并恢复会话 | 也可接会话 ID 前缀或路径 |
| `omp -p "只读解释这个模块"` | 非交互执行后退出 | `-p` 不自动限制工具为只读 |
| `omp --config /path/to/overlay.yml` | 本次启动叠加配置 | 不持久化覆盖层，可重复传入 |
| `omp --no-tools -p "解释所给文本"` | 只用所给文本回答 | 关闭内置工具，不读取代码仓 |
| `omp --approval-mode always-ask` | 覆盖本会话工具审批策略 | 自动允许读工具，写/执行按策略确认 |
| `omp --help` | 查该版帮助 | 无需模型推理 |

## 常用 TUI 操作

`/model` 切换模型；`/settings` 调整设置；`/docs` 查看索引；`/agents` 查看 Agent；`/tools` 查看当前工具；`/context` 查看上下文占用；`/compact soft` 压缩；`/resume` 恢复；`/hotkeys` 查看当前键位。

完整 TUI 清单在[内置命令](commands.html)。每个命令页分别说明状态影响；不要仅根据名字推断其只读性。

## CLI 注册入口

下面清单由固定版本 `cli-commands.ts` 提取。各入口的详细参数以该版 `omp <入口> --help` 为准；以下逐页给出用途、影响及入口示例。

<!-- inventory:cli -->

依据：[启动参数](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/commands/launch-help.ts)。
