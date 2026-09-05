# 团队 Agent

这里集中展示三个团队 Agent 的职责与完整定义。日常使用不必逐一调用，先阅读[团队公共能力使用指南](team.html)，由主会话按需编排。

这些是团队提供的 Worker，不是 OMP 的[内置 Agent](agents.html)。下面的配置头与正文直接取自公共源文件，复制或阅读时不会丢失字段。

## document-worker

**职责**：只读调查规范、代码、调用方和已有测试。**输入**：明确问题与目录范围。**输出**：文件位置、接口约束、测试入口、冲突和缺口。

工具限定为 `read, grep, glob, wiki`；OMP 自动补充用于交付结果的 `yield`。不修改文件，不执行安装或构建。缺少 Wiki 时检索原文，不创建数据库。

### 完整原始文件

<!-- team-source:omp/agents/document-worker.md -->

## coding-worker

**职责**：根据已确认依据完成最小代码修改。**输入**：需求、调查结论、允许修改的文件范围。**输出**：实际变更、行为变化、已运行检查和后续测试入口。

具备 `edit/write/bash/lsp` 等能力，不自动提交、推送或升级依赖；不得与其他 Worker 同时修改相同文件。

### 完整原始文件

<!-- team-source:omp/agents/coding-worker.md -->

## verification-worker

**职责**：根据真实修改补充并执行相关测试。**输入**：diff、行为契约、既有框架和运行入口。**输出**：测试变更、实际命令、退出码、结果与未验证范围。

可修改相关测试及必要 fixture，不擅自修改产品代码，也不降低断言掩盖失败。失败时返回可复现证据，不宣称已修复。

### 完整原始文件

<!-- team-source:omp/agents/verification-worker.md -->
