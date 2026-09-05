# 团队 Skills 总览

Skill 是供 Agent 按需读取的方法说明，不是后台服务。先按任务找到合适的 Skill，再查看使用示例；完整输入输出、执行边界和原始文件放在各自独立页面。

## 按任务选择

| Skill | 功能 | 什么场景下使用 |
|---|---|---|
| [generate-unit-tests](skill-generate-unit-tests.html) | 根据真实修改，复用已有框架补充并执行相关单元测试 | 功能已修改、缺陷已修复，需要补回归或验证受影响的边界行为 |
| [generate-dft-circuit](skill-generate-dft-circuit.html) | 在指定工程生成 DFT 插入前基础 RTL、文件清单与验证入口 | 需要小型电路作为后续 DFT 流程输入，还没有 Scan、EDT 等结构 |

## 怎么调用

Agent 可以根据任务自动选择 Skill，通常直接描述需求即可。希望明确采用某项方法时，在 OMP 输入框使用 `/skill:<名称> <需求>`，不在 Shell 中执行。

### 为已有修改补充测试

直接描述：

```text
请根据当前复位逻辑的修改，在项目现有测试框架中补充回归，并运行相关测试。
```

显式调用：

```text
/skill:generate-unit-tests 对当前复位逻辑的修改补充相关 UT，并执行项目已有测试入口，不修改产品代码。
```

适用于已有修改的验证，不是无目标地扩充测试数量。查看 [generate-unit-tests 的完整说明与原始文件](skill-generate-unit-tests.html)。

### 生成 DFT 插入前基础电路

直接描述：

```text
请在我指定的工程生成 TOP → CORE_A → CORE_B 的基础 RTL，提供文件清单和验证入口，先不要加入 Scan 或 EDT。当前没有 PAD 库，请明确说明未接真实 PAD。
```

显式调用：

```text
/skill:generate-dft-circuit 在 /path/to/project 生成 DFT 插入前基础 RTL、文件清单和测试平台；缺少 PAD 库或仿真工具时明确报告缺口。
```

将示例路径替换为实际目标工程。此 Skill 不会在缺少资料时假装完成真实 PAD 接入或 DFT 插入。查看 [generate-dft-circuit 的完整说明与原始文件](skill-generate-dft-circuit.html)。

## 和自定义命令有什么区别

`/code-and-verify` 是从需求到实现、验证的完整开发入口；Skill 是某类任务的具体做法。例如开发流程需要补测试时，Agent 可以选用 `generate-unit-tests`。只需要为已有修改补测试，可以直接调用该 Skill，不必重新启动完整开发流程。

## 发现与启用

两项 Skill 均允许自动选择，不设置 `hide` 或 `disable-model-invocation`。显式调用需要启用 `skills.enabled`、`skills.enableSkillCommands`。

同步位置为 `~/.omp/agent/skills/<名称>/SKILL.md`。进入目标代码仓后启动 OMP 即可发现；项目同名定义或禁用设置可能覆盖个人版本，加载情况可通过 `/extensions` 查看。

这里只列团队共享的 Skill，不是当前用户全部个人 Skill 的清单。每项 Skill 在左侧都有独立入口，后续新增能力继续按项查阅。

依据：[Skill 发现与调用](https://github.com/jchanghong023/oh-my-pi/blob/v18.1.9%2Bfork.170/packages/coding-agent/src/extensibility/skills.ts)。
