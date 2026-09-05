# 快速开始

面向 CentOS 7 的离线使用入口。目标机器已具备 Python 3.11+；OMP 与 Claude Code 的系统兼容性采用团队已确认的结果。本包默认携带 Linux x64 二进制，arm64 机器需维护者下载对应架构后重新打包。

## 1. 获取完整发布包

解压离线包到长期保留的位置。Git 用户在外围先执行 `git lfs pull`，不能把未拉取的 LFS 指针带入离线环境。发布包内已经是二进制实体，使用者无需 Git LFS。

本门户可以直接双击打开 `site/index.html`；不需要 Web 服务器，也不需要安装网站构建依赖。

## 2. 预览并同步

在仓库根目录运行。先用 `python3 --version` 确认本地 Python 至少为 3.11；若默认版本较旧，将 `python3` 替换为已安装的 Python 3.11+ 解释器绝对路径：

```bash
python3 scripts/sync.py --dry-run
python3 scripts/sync.py
```

也可从任意工作目录用脚本绝对路径运行，路径有空格时加引号。预览不会停止进程或修改目标目录；正式同步会终止当前用户的 OMP 进程。先保存正在进行的任务。

| 来源 | 目标 |
|---|---|
| omp/AGENTS.md | ~/.omp/agent/AGENTS.md，并追加本机原文目录 |
| omp/skills/ | ~/.omp/agent/skills/ 中团队同名文件 |
| omp/commands/ | ~/.omp/agent/commands/ 中团队同名文件 |
| omp/agents/ | ~/.omp/agent/agents/ 中团队同名文件 |
| dist/omp/omp、dist/claude-code/claude | ~/.local/bin/omp、~/.local/bin/claude |
| yellow/docs.db（若存在） | ~/.omp/agent/docs.db |

不删除其他个人文件，不覆盖 `config.yml`、`models.yml` 或认证数据库。缺少 `yellow/docs.db` 时明确跳过并保留个人数据库。内部 Markdown 不复制到个人目录。

## 3. 在目标代码仓启动

```bash
export PATH="$HOME/.local/bin:$PATH"
cd /path/to/your/project
omp
```

PATH 只影响当前 Shell；同步脚本不修改启动文件。也可直接运行 `~/.local/bin/omp`。模型及凭据沿用本机配置，首次使用参阅[常用配置](config.html)。离线门户与客户端离线分发不等于模型可离线推理；实际模型服务须在目标网络可达。

此同步入口针对默认 `~/.omp/agent/`，不自动分发至命名 profile 或 `PI_CODING_AGENT_DIR` 指定目录。在特殊 profile 中找不到团队能力时先检查实际配置目录。

## 4. 执行一次开发任务

```text
/code-and-verify 修复当前模块复位后输出延迟异常，并验证已有行为
```

通过 `/agents` 查看团队 Worker，通过 `/extensions` 检查 Skill，通过 `/tools` 检查 Wiki 是否可用。新启动的会话读取同步后的文件；在未退出会话中手工调整扩展文件时可用 `/reload-plugins`。

原文路径会追加到同步后的团队上下文，即使 Agent 从其他代码仓启动也能定位。索引无结果时按关键词在原文目录中 `grep` / `read`，不要把“没有命中”等同于“没有规定”。

## 同步输出怎么理解

`UPDATE` 表示已替换；`SKIP unchanged` 表示内容一致；数据库缺失的 `SKIP` 表示保留个人版本。`FAIL` 后不继续执行；若此前已有 UPDATE，那些变更已实施。脚本不维护安装历史或自动回退系统。

源码依据：[原生发现规则](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/discovery/builtin.ts)、[Agent 发现](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/task/discovery.ts)。
