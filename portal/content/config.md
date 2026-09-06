# 常用配置

模型入口（TUI，参考上游 `61fb07d`）：`/switch` 仅切换本会话模型；`/model` 打开模型中心，角色与默认模型在确认相应操作后保存。详见[命令依据](command-model.html)；实际分发版本需在目标机核对。

同步不替用户选择模型、填入凭据或修改审批策略。以下路径是默认 profile 的路径，个人命名 profile 与环境变量可改变实际位置。

## 配置文件位置

| 内容 | 默认位置 |
|---|---|
| 常用配置 | ~/.omp/agent/config.yml，兼容已有 config.yaml |
| 模型提供方 | ~/.omp/agent/models.yml，兼容 models.yaml |
| 认证存储 | ~/.omp/agent/agent.db |
| 文档索引 | ~/.omp/agent/docs.db |
| 团队能力 | ~/.omp/agent/skills、commands、agents |
| 项目配置 | 当前工作目录下 .omp/config.yml |

`omp config path` 输出实际 Agent 目录。全局配置、项目配置、`--config` 覆盖层和运行时参数逐层生效；本仓库不迁移用户的模型和认证数据。

## 模型接入

用 `/setup providers` 或 `omp setup` 配置已有服务，用 `/model` 选择本机可用模型。自定义网关需依据网关实际协议、模型 ID 和上下文规格编写 `models.yml`。以下只表示 YAML 结构，不是可直接工作的公司配置：

```yaml
providers:
  team-gateway:
    baseUrl: https://gateway.example.invalid/v1
    apiKey: TEAM_MODEL_API_KEY
    api: openai-completions
    models:
      - id: actual-model-id
        name: Team model
        reasoning: false
        input: [text]
        contextWindow: 32768
        maxTokens: 4096
        cost:
          input: 0
          output: 0
          cacheRead: 0
          cacheWrite: 0
```

占位域名、模型 ID、协议和窗口值均须按真实服务替换，示意成本不代表实际费用。`apiKey` 可填写本地环境变量名；不要把真实密钥提交到效率仓库。

## 并发、Skill 与审批

```bash
omp config get task.maxConcurrency
omp config get task.maxRecursionDepth
omp config get skills.enabled
omp config get skills.enableSkillCommands
omp config get tools.approvalMode
```

该版 `task.maxConcurrency` 默认 8，`task.maxRecursionDepth` 默认 2；`skills.enabled` 和 `skills.enableSkillCommands` 默认开启。实际值以本机查询为准。

需要修改时使用 `/settings` 或 `omp config set <key> <value>`，这是个人配置变更，不属于同步行为。审批值为 `always-ask`、`write`、`yolo`；源码默认 `yolo`，仍可受用户策略约束。审批策略与用户授权不是同一件事。

## Wiki 与内部原文

同步后的 `docs.db` 可通过 `omp docs list`、`omp docs status` 或 `/docs` 检查。文档索引记录的源路径可能来自建库机器；迁移后找不到原文时使用团队上下文记录的 `yellow/docs/` 实际路径。

`--public-only` 构建不读取内部资料；默认网站构建仅将 Markdown 另行生成到本地内部文档栏目，不修改 Wiki 数据库。公司维护者如需重建 Wiki 索引，应使用该版 `omp docs init <dir> --name <name> --mode fts` 或 `omp docs reinit <name>` 的已确认条件；建库后关闭写入程序、完成 checkpoint，再复制数据库。不要把运行中的 WAL 数据库只拷走主文件。

依据：[设置说明](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/docs/settings.md)、[设置 schema](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/config/settings-schema.ts)、[模型配置](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/docs/models.md)。
