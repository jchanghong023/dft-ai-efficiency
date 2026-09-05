# DFT 小团队 OMP AI 开发提效仓库建设方案与实施计划

## 1. 建设目标

本方案面向 DFT 团队日常开发，重点解决内部知识检索、代码开发、测试验证、团队能力共享和新人使用入口。

| 目标 | 建设内容 |
|---|---|
| AI 有依据 | OMP 可检索公司内部工具、接口、流程和测试资料 |
| 开发有验证 | 修改代码后补充并执行相关 UT，必要时执行已有集成测试 |
| 团队可共享 | Skill、Agent、自定义命令和团队规则统一维护、统一同步 |
| 能力可演进 | OMP Fork 持续开发，稳定通用能力逐步内置 |
| 新人有入口 | 通过离线门户学习 OMP、查资料和查看实际使用方法 |

### 1.1 OMP 与 Claude Code 的定位

OMP 基于上游项目 Fork 持续维护。团队可以根据实际需求修改源码，增加模型适配、Wiki、命令、工具及其他通用能力。

能力分为两层：

| 层次 | 内容 |
|---|---|
| OMP 内置能力 | 模型接入、Markdown Wiki、全文索引、内置命令和工具等 |
| 效率仓库共享能力 | Skill、Agent、自定义命令、团队规则、手册和最佳实践 |

容易调整的任务方法优先放在 Skill、Agent 和自定义命令中；需要稳定执行、多人长期复用的能力，再内置到 OMP。

Claude Code 在外网侧同步维护最新稳定版本并以离线客户端形式传入公司环境。已经习惯 Claude Code 的同事可以继续使用，但本方案新增的 OMP Wiki、团队命令和其他 OMP 定制能力不保证在 Claude Code 中等价可用。

### 1.2 公共仓库、黄区、红区边界

公共效率仓库可以放到互联网，因此**不得包含公司内部 Markdown、内部 Wiki 索引或其他内部资料**。

网站、OMP 手册、Skill/Agent/命令说明等公共内容均在外围开发阶段完成并生成，不使用公司内部资料生成网站内容。

整体流程：

```text
互联网 / 公共效率仓库
    ├── OMP 二进制
    ├── Claude Code 二进制
    ├── Skill、Agent、自定义命令
    ├── 已生成好的离线门户
    └── yellow/ 预留目录
                  ↓
             传入公司黄区
                  ↓
       在 yellow/ 中复制内部 Markdown
       和对应的 docs.db
                  ↓
             形成红区发布内容
                  ↓
               传入红区
                  ↓
        红区用户离线使用 OMP 和门户
```

公司内部资料只在公司环境中使用：

- 原始 Markdown 供 AI Agent 直接 `read` / `grep`，适合精确查找命令、路径、信号和上下文；
- `docs.db` 供 OMP Wiki 快速全文检索；
- 内部资料不生成网站页面，也不进入公共 Git 仓库。


---

## 2. 公共效率仓库目录

```text
dft-ai-efficiency/
├── README.md                       # 仓库入口、同步方法、使用说明
├── AGENTS.md                       # 维护本仓库时的规则
├── .gitignore                      # 忽略临时文件等不应提交的内容
│
├── dist/
│   ├── omp/
│   │   ├── omp                     # 团队使用的 OMP 二进制
│   │   └── VERSION
│   └── claude-code/
│       ├── claude                  # 外网维护的最新稳定版客户端
│       └── VERSION
│
├── omp/                            # 同步到个人 OMP 目录的公共能力
│   ├── AGENTS.md                   # 团队日常编程约定
│   ├── skills/
│   │   └── generate-unit-tests/
│   │       └── SKILL.md
│   ├── commands/
│   │   └── code-and-verify.md
│   └── agents/
│       ├── document-worker.md
│       ├── coding-worker.md
│       └── verification-worker.md
│
├── site/                           # 外围已经生成好的完整离线门户
│   ├── index.html
│   ├── pages/
│   └── assets/
│
├── yellow/                         # 公司内部资料预留目录
│   └── .gitignore                  # 公共仓库中保持为空，禁止提交内部内容
│
└── scripts/
    ├── sync.sh                     # 同步 OMP 公共能力、二进制和 docs.db
    └── build_site.py               # 外围维护公共门户时使用
```

仓库根目录 `.gitignore` 至少包含：

```gitignore
.tmp/
```

所有构建中间文件、临时下载、临时解压、调试输出等统一放在 `.tmp/`，不提交 Git。

`yellow/.gitignore` 用于保证 `yellow/` 目录本身保留在仓库中，但黄区接入的实际数据不被提交，例如：

```gitignore
*
!.gitignore
```

`yellow/` 随公共仓库一起交付，但公共版本中不包含业务数据。其 `.gitignore` 忽略目录下除自身以外的所有实际内容，防止黄区接入内部资料后被误提交。

项目传入黄区后，在该目录加入：

```text
yellow/
├── docs/                            # 公司内部 Markdown 及附件
└── docs.db                          # 对应的 OMP Wiki 索引
```

其中 `docs/` 和 `docs.db` 均不纳入 Git。


---

## 3. 黄区接入与红区同步

### 3.1 黄区维护者

公共效率仓库开发完成并传入黄区后，黄区只增加内部 AI 知识数据：

1. 将公司内部 Markdown 及附件复制到 `yellow/docs/`。
2. 将对应的 `docs.db` 复制到 `yellow/docs.db`。
3. 检查内部内容未被 Git 跟踪，临时处理文件统一放入 `.tmp/`。
4. 将包含公共工具、公共门户和 `yellow/` 数据的版本传入红区。

公司内部 Markdown 不参与门户构建。离线门户在外围已经生成完成，进入黄区后保持不变。

### 3.2 红区普通用户

```text
获取传入红区的效率仓库
        ↓
执行 scripts/sync.sh
        ↓
同步 OMP、公共能力和 docs.db
        ↓
浏览器打开 site/index.html
        ↓
进入目标代码仓启动 OMP
        ↓
Wiki 快速检索 + 必要时 grep/read 原始 Markdown
```

统一入口：

```bash
./scripts/sync.sh
```

### 3.3 `sync.sh` 的职责

同步脚本只完成必要操作：

1. 检测当前用户是否存在 OMP 进程；如存在，先终止，避免覆盖正在使用的数据库。
2. 将团队 OMP 公共能力复制到个人 OMP 目录，同名团队文件直接覆盖。
3. 将 `yellow/docs.db` 覆盖到：

```text
~/.omp/agent/docs.db
```

4. 按需要更新 OMP 二进制。
5. 不删除用户其他文件，不维护复杂安装状态，不提供回退系统。

内部 Markdown 保留在仓库的 `yellow/docs/` 中，供 AI Agent 按需 `read` / `grep`；`docs.db` 用于 Wiki 快速搜索。


---

## 4. 文档驱动的开发与验证

日常代码任务采用统一流程：

```text
用户提出需求
      ↓
查内部文档、现有代码和已有测试
      ↓
确定修改范围
      ↓
完成最小修改
      ↓
补充并执行相关 UT
      ↓
必要时运行已有集成测试
      ↓
汇总修改和验证结果
```

统一入口：

```text
/code-and-verify <开发需求>
```

复杂任务可按职责拆分为三个 Worker：

| Agent | 职责 | 主要输出 |
|---|---|---|
| `document-worker` | 只读查 Wiki、代码和已有测试 | 文档依据、相关文件、接口和约束 |
| `coding-worker` | 根据调查结果完成最小代码修改 | 修改文件、修改摘要 |
| `verification-worker` | 补充并执行相关测试 | 实际命令、测试结果、日志位置、未验证项 |

```text
                 ┌─ document-worker ─── 查依据
用户需求 → OMP ─┼─ coding-worker ───── 做修改
                 └─ verification-worker ─ 验证
                           ↓
                        汇总结果
```

简单任务由主会话直接完成，不强制拆分多个 Agent。

---

## 5. 团队共享能力

第一阶段只维护少量高价值公共能力。

| 内容 | 作用 |
|---|---|
| `omp/AGENTS.md` | 统一调查、最小修改、测试和结果报告原则 |
| `generate-unit-tests` | 根据当前修改补充并执行相关 UT |
| `/code-and-verify` | 统一日常开发入口 |
| `document-worker` | 文档与代码调查 |
| `coding-worker` | 代码修改 |
| `verification-worker` | 测试与结果检查 |

这些内容统一保存在公共 Git 仓库中，通过发布包和 `sync.sh` 分发，不通过个人目录或聊天附件维护多套版本。

需要稳定、机械执行的能力，后续再逐步内置到 OMP。

---

## 6. 离线门户

离线门户是团队统一的 OMP 使用说明入口，全部内容在外围开发阶段完成并生成。公司内部 Markdown 不参与门户生成，只供 AI Agent 检索。

### 6.1 门户内容

第一版至少包含以下栏目：

| 栏目 | 内容 |
|---|---|
| 快速开始 | 获取发布包、执行 `sync.sh`、启动 OMP、打开门户 |
| OMP 常用命令 | 日常 CLI / TUI 命令、用途、参数和示例 |
| OMP 内置工具 | `read`、`grep`、`wiki`、`task`、LSP 等工具的作用和典型场景 |
| OMP 常用配置 | 模型、Wiki、Agent、并发、权限等常用配置 |
| Skills | Skill 列表、功能、适用场景、是否必须手动调用、Agent 是否可自动选择 |
| 内置命令 | 当前 OMP Fork 实际提供的内置命令、功能和使用方式 |
| 内置 Agent | 当前 OMP Fork 实际提供的 Agent、职责、适用场景和调用方式 |
| 团队公共能力 | `/code-and-verify`、团队 Worker、团队 Skill 的使用说明 |
| FAQ / 最佳实践 | 常见问题和团队已经验证有效的方法 |

### 6.2 Skill 页面要求

每个 Skill 至少说明：

```text
名称
用途
适用场景
不适用场景
Agent 是否可自动选择
是否必须手动调用
手动调用方法
输入
输出
示例
```

需要明确区分：

- Agent 是否可以根据 Skill 描述自行选择使用；
- 用户是否可以显式调用；
- 哪些 Skill 必须手动调用；
- 哪些 Skill 通常无需手动指定。

### 6.3 内置命令页面要求

内置命令页面以**当前 OMP Fork 实际注册的命令**为准，不手写一份长期不更新的固定清单。

页面至少记录：

```text
命令
功能
典型场景
是否修改文件或外部状态
主要参数
示例
```

Fork 新增或保留的命令也必须纳入，例如 `fullsend` 相关命令和团队实际保留的 JCH 命令。

### 6.4 内置 Agent 页面要求

OMP 当前内置 Task Agent 包括：

```text
scout
designer
reviewer
security-reviewer
librarian
task
sonic
```

门户中逐项说明：

- 主要职责；
- 适合什么任务；
- 是否只读；
- 是否适合直接由用户指定；
- 如何通过 `task` 或相关入口使用。

团队自定义的 `document-worker`、`coding-worker`、`verification-worker` 单独列在“团队公共能力”中，避免与 OMP 内置 Agent 混淆。

### 6.5 门户交付要求

- 直接通过浏览器打开，不依赖服务器。
- 样式、脚本、图片和搜索资源全部本地提供。
- 不使用 CDN、在线字体或运行时下载。
- 门户全部属于公共内容，可以进入互联网仓库。
- 公司内部 Markdown、附件和 `docs.db` 不生成门户页面，也不进入公共仓库。
- 普通用户不需要安装网站构建环境。

---

## 7. 实施计划

| 阶段 | 主要工作 | 交付物 |
|---|---|---|
| 1. OMP 工具维护 | 整理 Fork、模型接入、Wiki 和日常开发能力 | OMP 二进制 |
| 2. 公共仓库建设 | 建立目录、根 `.gitignore`、`.tmp/` 约定、Skill、Agent、自定义命令和 `yellow/` 预留目录 | 公共效率仓库 |
| 3. 离线门户 | 在外围完成快速开始、命令、工具、配置、Skill、Agent 等手册并生成网站 | 完整 `site/` |
| 4. 黄区知识接入 | 在 `yellow/` 中复制内部 Markdown 和 `docs.db` | `yellow/docs/`、`yellow/docs.db` |
| 5. 红区同步机制 | 同步 OMP、公共能力和个人 `docs.db` | `scripts/sync.sh` |
| 6. 最小 DFT Base 验证 | 使用 `tiny_base` 在 Sailor 中打通关键流程 | 可重复运行的 Base Case |
| 7. 后续项目试用 | Base 稳定后，再选择实际项目验证 AI 工作流 | 问题记录、改进项、最佳实践 |
| 持续维护 | 跟踪 OMP 上游和 Claude Code 版本，更新公共能力与资料 | 持续版本更新 |

第一阶段不直接拿复杂真实项目作为入口。先用结构清晰、规模可控的最小 DFT Base 在 Sailor 中把开发、文档检索和验证链路跑通，再进入其他项目。

---

## 8. 最小 DFT 测试 Base Case

### 8.1 目标

Base 命名为 `tiny_base`。

目的：

- 提供稳定、可重复的最小 DFT 测试输入；
- 在 Sailor 中打通关键 DFT 流程；
- 用于验证后续 OMP 代码修改、Skill 和 Agent 工作流；
- 避免一开始直接依赖大型真实项目。

### 8.2 目标 DFT 结构

```text
                                  ┌─────────────── MBIST
JTAG ──→ TAP ──→ IJTAG ──────────┤
                                  └─────────────── 其他内部 TDR

scan_in/channel_in
        │
        ▼
      PIPE ──→ EDT ──→ Scan Chains / Logic ──→ EDT ──→ PIPE
                    │                           │
                    └──── Wrapper Chains ──────┘
        ▲
        │
dft_se / edt_update / dft_se_occ

PLL / 功能时钟
        │
        ▼
      ROOT OCC ──→ Branch OCC / ICG ──→ 被测逻辑时钟

scan_out/channel_out ◀──────────────────────────────────────
```

Base 不要求第一版一次覆盖全部能力，而是按 Sailor 流程逐步增加特征。

### 8.3 原始电路

```text
TOP
└── CORE_A
    └── CORE_B
```

原始电路包含少量普通 DFF、组合逻辑、真实 Input/Output PAD、JTAG 接口预留和 Scan/EDT 后续复用接口。

原始电路不预先包含 Scan Chain、EDT、Wrapper Chain、IJTAG、TAP 或 Boundary Cell。

```text
                         TOP：DFT 插入前
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│ TCK     → [Input PAD] → JTAG 预留点                         │
│ TMS     → [Input PAD] → JTAG 预留点                         │
│ TDI     → [Input PAD] → JTAG 预留点                         │
│ TRST_N  → [Input PAD] → JTAG 预留点                         │
│                         JTAG 预留输出 → [Output PAD] → TDO  │
│                                                             │
│ scan_clk      → [Input PAD] → CORE_A / CORE_B 功能时钟      │
│ dft_lgc_rst_n → [Input PAD] → CORE_A / CORE_B 功能复位      │
│                                                             │
│ scan_in        → [Input PAD] ──┐                            │
│ dft_se         → [Input PAD] ──┤                            │
│ dft_edt_update → [Input PAD] ──┤ 功能输入/控制              │
│ dft_se_occ     → [Input PAD] ──┘                            │
│                              ↓                              │
│        ┌────────────── CORE_A ───────────────┐              │
│        │ 输入寄存器 / 组合逻辑               │              │
│        │              ↓                       │              │
│        │       ┌──── CORE_B ────┐             │              │
│        │       │ DFF → Logic → DFF            │              │
│        │       └────────┬───────┘             │              │
│        │                ↓                     │              │
│        │             输出寄存器                │              │
│        └────────────────┬─────────────────────┘              │
│                         └──→ [Output PAD] → scan_out         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 8.4 接口

| 接口 | 方向 | 原始用途 |
|---|---|---|
| `TCK`、`TMS`、`TDI`、`TRST_N` | Input | JTAG 预留 |
| `TDO` | Output | JTAG 输出预留 |
| `scan_clk` | Input | 原始功能时钟，后续复用为 Scan 时钟 |
| `dft_lgc_rst_n` | Input | 原始功能复位，后续作为 DFT 复位控制 |
| `scan_in` | Input | 原始功能输入，后续复用为 Scan/EDT 输入 |
| `dft_se` | Input | 原始控制输入，后续作为 Scan Enable |
| `dft_edt_update` | Input | 原始控制输入，后续作为 EDT Update |
| `dft_se_occ` | Input | OCC 控制预留 |
| `scan_out` | Output | 原始功能输出，后续复用为 Scan/EDT 输出 |

初始按单路 Scan/EDT 数据接口构造；实际 Sailor 配置需要更多 channel 时，再增加对应 PAD。

### 8.5 Sailor 打通顺序

第一版不追求一次覆盖全部 DFT 能力，建议按以下顺序逐步扩展：

```text
tiny_base
   ↓
基础 Scan
   ↓
EDT
   ↓
JTAG / Boundary Scan
   ↓
IJTAG
   ↓
OCC / 时钟相关结构
   ↓
必要时增加 Memory / MBIST
```

每增加一项能力，都保留对应输入、配置、运行入口和结果，形成稳定的可重复 Case。

### 8.6 DFT 插入后的主要通路

```text
JTAG：
TDI → PAD → TAP → 指令寄存器 / 选中的数据寄存器 → TDO PAD → TDO
                     │
                     └→ IJTAG → 内部 TDR / MBIST 控制

Scan / EDT：
scan_in → PAD → IO 复用 → EDT 解压 → Scan Chains
        → EDT 响应压缩 → IO 复用 → PAD → scan_out

Clock：
scan_clk / dft_atpg_clk
        → ROOT OCC / Branch OCC / ICG
        → Scan shift / launch / capture 时钟

Control：
dft_se / dft_edt_update / dft_se_occ / dft_lgc_rst_n
        → Scan、EDT、OCC 及相关测试控制
```

JTAG 根据当前指令选择对应的数据寄存器，并不是把 BSCAN、IJTAG、BYPASS 等全部固定串联。内部 Scan ATPG 数据默认走 Scan/EDT 通路；JTAG 主要用于指令、Boundary Scan 和 IJTAG 配置/读回。

### 8.7 后续扩展

```text
tiny_base
├── scanbus_base
├── memory_base
├── mbist_base
├── sharebus_base
└── occ_base
```

每个派生 Case 只增加目标功能所需结构。Base 稳定后，再进入其他实际项目验证。
