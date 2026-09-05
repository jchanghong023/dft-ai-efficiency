# 内置命令

以下命令依据本页标注的手册参考版本，不含团队自行定义的 `/code-and-verify`。命令资料和中文解释独立维护，新增命令缺少说明时构建失败；二进制升级不自动更新本页内容。

## TUI 注册命令

所有名称都是在 OMP 输入框中的斜杠命令，而非 Linux 可执行文件。是否可用还受当前模式、扩展禁用项、模型和工具配置影响。

<!-- inventory:commands -->

## 内置模板与模块命令

除主注册表外，该版还加载 `init` 提示模板，以及 `green`、`review` 两个模块命令；它们也纳入版本快照。

<!-- inventory:extras -->

## fullsend 与 JCH

`/fullsend` 把任务转换为 magic keyword 提示，目标是在不限制模型资源成本的条件下追求速度与经验证的质量；并不是“跳过验证”的别名。实际通知还受 `magicKeywords` 设置控制。

`/jchcatchup` 默认运行本地 status/log；`full` 会先 fetch。`/jchgs` 会 fetch；`/jchgitpull` 会 pull；`/jchgitdiscardall` 会硬重置到 upstream 并执行 `clean -xdf`，会删除未跟踪和被忽略的本地内容。`/jchcifix` 包含提交和推送。这些说明是能力目录，不是建议日常使用破坏性操作。

依据：[主注册表](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/slash-commands/builtin-registry.ts)、[JCH Git 实现](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/jch-commands/git.ts)。
