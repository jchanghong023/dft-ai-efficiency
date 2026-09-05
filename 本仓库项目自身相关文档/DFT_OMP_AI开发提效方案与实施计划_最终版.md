# DFT 小团队 OMP AI 开发提效仓库建设方案与实施计划

本方案已按当前实现同步，作为仓库目标、结构与交付边界的设计基线。门户包含五个独立分区、新手场景使用指南、统一明暗主题和 DFT 交互教学；公司资料独立保存在 `yellow/`。具体操作由门户手册说明，验证结果单独记录。

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

OMP 基于上游项目 Fork 持续维护；Fork 自身的开发独立进行。本效率仓库不修改 OMP 源码。更新二进制只运行一个 Python 脚本，不要求克隆源码或更新元数据。手册、Skill、命令及 Worker 按需单独维护，说明标注参考版本；需要核验实现时可在 `.tmp/` 只读参考 Fork 源码。

目标使用环境为 **CentOS 7**，OMP 与 Claude Code 二进制兼容性以用户已确认结果为前提。同步、维护、构建、打包和验证脚本统一使用 **Python 3.11+**；普通用户浏览已生成门户不需要网站构建环境。

能力分为两层：

| 层次 | 内容 |
|---|---|
| OMP 内置能力 | 模型接入、Markdown Wiki、全文索引、内置命令和工具等 |
| 效率仓库共享能力 | Skill、Agent、自定义命令、团队规则、手册和最佳实践 |

容易调整的任务方法优先放在 Skill、Agent 和自定义命令中；需要稳定执行、多人长期复用的能力，再内置到 OMP。

Claude Code 在外网侧同步维护最新稳定版本并以离线客户端形式传入公司环境。已经习惯 Claude Code 的同事可以继续使用，但本方案新增的 OMP Wiki、团队命令和其他 OMP 定制能力不保证在 Claude Code 中等价可用。

### 1.2 公共仓库、黄区、红区边界

公共效率仓库可以放到互联网，因此**不得包含公司内部 Markdown、内部 Wiki 索引或其他内部资料**。

OMP 手册、Skill/Agent/命令说明等公共内容在外围完成，源码、生成页面及本地资源均纳入 Git。公司文档可在同一门户的“内部文档”栏目浏览，但原始 Markdown、附件、生成页面和各类内部索引全部保留在被忽略的 `yellow/` 下，不混入公共 `site/`、公共 Git 或公共发布包。

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
       在 yellow/docs/ 中复制内部 Markdown 及附件
       在 yellow/docs.db 中放置对应 Wiki 数据库
       构建 yellow/.site/ 内部页面与网页搜索索引
                  ↓
       按公司流程形成含 yellow/ 的内部交付内容
                  ↓
               传入红区
                  ↓
        红区用户离线使用 OMP 和门户
```

公司内部资料只在公司环境中使用：

- 原始 Markdown 供 AI Agent 直接 `read` / `grep`，适合精确查找命令、路径、信号和上下文；
- `docs.db` 供 OMP Wiki 快速全文检索；
- `yellow/.site/` 供浏览器阅读与全文搜索，和公共门户保持一致的界面；
- 公共构建与内部构建分开输出。`--public-only` 完全不访问 `yellow/`；公共打包仅使用公共白名单，不读取或收录内部资料。


---

## 2. 公共效率仓库目录

```text
dft-ai-efficiency/
├── README.md                       # 仓库入口、同步方法、使用说明
├── AGENTS.md                       # 维护本仓库时的规则
├── .gitignore                      # 忽略临时文件等不应提交的内容
├── .gitattributes                  # OMP、Claude Code 二进制使用 Git LFS
├── requirements-build.txt          # 网站构建依赖
├── requirements-dev.txt            # 浏览器验收等开发依赖
│
├── dist/                           # 仅两个实体，无版本或更新状态文件
│   ├── omp/omp                     # OMP 二进制
│   └── claude-code/claude          # Claude Code 二进制
│
├── omp/                            # 同步到个人 OMP 目录的公共能力
│   ├── AGENTS.md                   # 团队日常编程约定
│   ├── skills/
│   │   ├── generate-unit-tests/
│   │   │   └── SKILL.md
│   │   └── generate-dft-circuit/
│   │       ├── SKILL.md
│   │       └── references/tiny-base.md
│   ├── commands/
│   │   └── code-and-verify.md
│   └── agents/
│       ├── document-worker.md
│       ├── coding-worker.md
│       └── verification-worker.md
│
├── portal/                         # 纳入 Git 的公共网站源码
│   ├── content/                    # 公共 Markdown
│   ├── catalog/                    # 人工维护的中文说明
│   ├── metadata/                   # 固定 Fork 版本的公共注册快照
│   ├── templates/                  # Jinja2 模板
│   └── assets/                     # 本地 CSS 与原生 JavaScript
│
├── site/                           # 纳入 Git 的公共页面与公共搜索资源
│   ├── index.html
│   ├── start/index.html            # 开始使用独立首页
│   ├── team/index.html             # 团队能力独立首页
│   ├── maintenance/index.html      # 维护手册独立首页
│   ├── internal/index.html         # 内部文档公共入口，不包含公司正文
│   ├── dft/index.html              # DFT知识独立首页
│   ├── pages/
│   └── assets/
│
├── yellow/                         # 内部原文、页面和索引全部放这里
│   └── .gitignore                  # 公共版仅交付此文件，其他内容全部忽略
│
├── scripts/                        # 顶层为网站构建、同步安装和启动本地服务
│   ├── build_site.py               # 公共门户构建；默认另构建本地内部页面
│   ├── sync.py                     # 同步公共能力、二进制和 docs.db
│   ├── serve_site.py               # Python 标准库服务，仅监听 127.0.0.1:9333
│   ├── _lib/                      # 公共代码与内部文档渲染实现
│   └── maintenance/
│       ├── maintain_binaries.py    # 二进制更新与官方校验
│       ├── install_hooks.py        # 安装公共手册的提交前行数检查
│       └── package.py              # 公共离线包打包
│
├── tests/                          # 所有测试、静态验证与浏览器验收脚本
└── .tmp/                           # 参考 clone、缓存、中间文件、测试输出与离线包
```

仓库根目录 `.gitignore` 至少包含：

```gitignore
.tmp/
```

所有构建中间文件、临时下载、临时解压、调试输出等统一放在 `.tmp/`，不提交 Git。`scripts/` 顶层保留 `build_site.py`、`sync.py` 和 `serve_site.py`；其他实现与维护入口放子目录，测试相关脚本统一放最顶层 `tests/`，不放在 `scripts/` 中。

运行 `python3.11 scripts/serve_site.py` 后，浏览器访问 `http://127.0.0.1:9333/`，按 Ctrl+C 停止服务。脚本随离线包分发，使用已有 Python 3.11+ 标准库，无需额外服务软件；只提供公共网站、内部生成页面和原文附件，不提供仓库其他文件或目录列表。

`yellow/.gitignore` 用于保证 `yellow/` 目录本身保留在仓库中，但黄区接入的实际数据不被提交，例如：

```gitignore
*
!.gitignore
```

`yellow/` 随公共仓库一起交付，但公共版本中不包含业务数据。其 `.gitignore` 忽略目录下除自身以外的所有实际内容，防止黄区接入内部资料后被误提交。

项目传入黄区后，在该目录加入：

```text
yellow/
├── .gitignore                      # 唯一进入公共 Git 和公共包的文件
├── docs/                            # 公司内部 Markdown 及附件
├── .site/                           # 内部 HTML、网页全文搜索数据及生成清单
└── docs.db                          # 对应的 OMP Wiki 索引
```

其中 `docs/`、`.site/` 和 `docs.db` 均不纳入 Git。网页搜索索引与 OMP Wiki 数据库是两个用途不同的产物；构建网站不创建、覆盖或修改 `docs.db`。

二进制由 Python 维护入口获取 Fork 最新正式发行版和 Claude Code 最新稳定版，下载时验证发行方校验值，只保存两个实体，不保存版本、来源及校验状态。公共离线包携带 LFS 实体文件；同步或打包发现未拉取的 LFS 指针时必须终止，不把指针当作可执行文件。公共 ZIP、校验值和包清单输出到 `.tmp/releases/`。


---

## 3. 黄区接入与红区同步

### 3.1 黄区维护者

公共效率仓库开发完成并传入黄区后，在本地接入内部知识资料：

1. 将公司内部 Markdown 及附件复制到 `yellow/docs/`。
2. 将对应的 `docs.db` 复制到 `yellow/docs.db`。
3. 执行 `python3.11 scripts/build_site.py`，生成公共门户，并为行数不超过阈值的内部 Markdown 生成页面；内部页面、网页搜索数据单独写入 `yellow/.site/`。
4. 打开 `site/index.html`，通过“内部文档”检查文件导航、正文和本地附件。
5. 检查内部内容未被 Git 跟踪，临时处理文件统一放入 `.tmp/`。
6. 按公司流程将包含公共工具、公共门户和整个 `yellow/` 的内部交付内容传入红区；公共打包脚本不负责收录公司数据。

内部 Markdown 增删改后重新构建。默认构建允许读取 `yellow/docs/`，但内部内容不进入公共页面、公共搜索或公共构建清单；仅维护公共门户时使用 `python3.11 scripts/build_site.py --public-only`，该模式不访问黄区。`yellow/docs.db` 由独立的 Wiki 数据准备流程提供，网站构建不会将网页搜索数据当作 Wiki 数据库。

构建脚本提供 `--max-lines N`，默认 `3000`，只为**行数不超过 N** 的内部 Markdown 生成网页。例如 `python3.11 scripts/build_site.py --max-lines 3000`：3000 行允许，3001 行及以上跳过。N 必须是正整数；空行计入，支持 LF/CRLF，末尾没有换行的一行也计入。公司文档仅在生成网页时过滤，不影响原始 Markdown、Agent 原文检索或 Wiki 数据库；公共手册不在构建时过滤或做行数限制校验。

超限文档不进入网页导航或全文搜索，跳过的文件与实际行数记录在 `yellow/.site/manifest.json`。降低阈值并重新构建时，清理此前生成的超限页面，避免旧内容残留；正文链接如指向超限 Markdown，则保留原文入口，不链接不存在的 HTML。行数阈值用于控制网页体量，不等同于原始 Office/PDF 页数。

### 3.2 红区普通用户

```text
获取传入红区的效率仓库
        ↓
执行 python3.11 scripts/sync.py
        ↓
同步 OMP、公共能力和 docs.db
        ↓
浏览器打开 site/index.html，通过“内部文档”阅读公司资料
        ↓
进入目标代码仓启动 OMP
        ↓
Wiki 快速检索 + 必要时 grep/read 原始 Markdown
```

统一入口：

```bash
python3.11 scripts/sync.py --dry-run
python3.11 scripts/sync.py
```

### 3.3 `sync.py` 的职责

同步入口仅依赖 Python 标准库，无需额外安装依赖；从脚本位置定位仓库，支持从任意工作目录启动和 `--dry-run`。职责如下：

1. 先预检源文件、二进制实体与校验值、数据库状态和目标权限，预检失败不开始覆盖。
2. 识别并终止当前用户的 OMP 进程，不影响其他用户；无法确认进程已退出时不得覆盖数据库。`--dry-run` 只报告，不停止进程或写入文件。
3. 将团队规则、Skills、命令和 Workers 覆盖到 `~/.omp/agent/` 对应位置，仅覆盖团队同名文件，保留个人其他文件及模型配置。
4. 存在 `yellow/docs.db` 时，经 SQLite 一致性与 WAL 状态检查后覆盖到：

```text
~/.omp/agent/docs.db
```

5. 缺少 `yellow/docs.db` 时明确跳过并保留个人数据库；异常数据库或活动的 WAL/SHM/journal 不允许覆盖。
6. 按需将 OMP 和 Claude Code 实体同步到 `~/.local/bin/`，设置执行权限，不自动修改 Shell 启动文件。
7. 输出实际更新、跳过和失败项；不删除用户其他文件，不维护复杂安装状态，不提供回退系统。

内部 Markdown 保留在仓库的 `yellow/docs/` 中，并将实际绝对路径记录在同步后的团队上下文，供 Agent 从目标代码仓定位原文。`docs.db` 用于 Wiki 快速搜索；内部网页留在 `yellow/.site/`，不复制到个人 OMP 配置目录。所有同步测试使用隔离目录和测试进程，不改动真实个人 OMP 环境。


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
| `generate-dft-circuit` | 在用户指定工程生成 DFT 插入前电路，默认采用第 8 节 tiny_base 规范 |
| `/code-and-verify` | 统一日常开发入口 |
| `document-worker` | 文档与代码调查 |
| `coding-worker` | 代码修改 |
| `verification-worker` | 测试与结果检查 |

这些内容统一保存在公共 Git 仓库中，通过发布包和 `python3.11 scripts/sync.py` 分发，不通过个人目录或聊天附件维护多套版本。命令和三个 Worker 使用固定版 OMP 支持的原生格式，并依据只读源码核验发现路径和调用方法。

两项 Skill 均可在匹配任务中自动选择，也支持 `/skill:generate-unit-tests` 和 `/skill:generate-dft-circuit` 显式调用。Skill 说明保持聚焦，不重复通用团队规则。UT Skill 沿用目标工程已有测试框架、fixture 和运行器，依据真实修改补充相关测试，不另建无关测试体系。

需要稳定、机械执行的能力，后续再逐步内置到 OMP。

---

## 6. 离线门户

离线门户是团队统一的 OMP 使用说明与文档阅读入口。采用 Python、Markdown、Jinja2 模板和本地 CSS 构建静态多页站点；浏览器交互使用本地原生 JavaScript，不依赖服务端或前端构建运行环境。公共内容输出到 `site/`，内部内容输出到 `yellow/.site/`，两者共享页面样式与顶部导航，但数据存储、搜索索引及分发边界分离。

### 6.1 门户内容

门户采用统一视觉、不同页面形态、模块独立导航。首页首屏展示项目用途、快速开始、场景指南及可复制的常用命令，以“查依据 → 做修改 → 跑验证”表达团队开发流程；正文只提供开始使用、团队能力、维护手册入口。顶部固定为 **首页 → 开始使用 → 团队能力 → 维护手册 → 内部文档 → DFT知识**。后五者各有独立首页，搜索限定当前模块；内容页左侧导航支持独立滚动及筛选。

分区首页按任务组织：开始使用展示上手步骤，团队能力展示工作流与 Skill，维护手册展示生成网站、启动服务、同步安装三个操作，DFT知识展示六条学习路线。上述目录型首页不重复展示左侧目录；内部文档首页保留文件导航。

Markdown 页面采用安静的阅读布局和右侧页内目录；电路学习页优先展示可操作实验，紧凑组织控制、图形与结果，再阅读原理。全站以蓝色强调操作，浅色采用白色与浅灰分层，深色采用炭灰；默认按本地时间自动切换，也可手动选择并记住偏好。以台式机桌面浏览为目标，不要求小屏幕专项验收。

| 独立分区 | 首页 | 本分区主要内容 |
|---|---|---|
| 开始使用 | `site/start/index.html` | 快速开始、场景使用指南、CLI/TUI、工具、配置、内置命令与 Agent、FAQ |
| 团队能力 | `site/team/index.html` | 团队工作流、Skills、Workers |
| 维护手册 | `site/maintenance/index.html` | 版本、构建、提交检查、打包与资料维护 |
| 内部文档 | `site/internal/index.html` | 导向 `yellow/.site/`；一份符合行数条件的 Markdown 对应一个导航项 |
| DFT知识 | `site/dft/index.html` | 测试原理、扫描与时钟、压缩与功耗、访问与分层、内建自测试、工程落地六条学习路线 |

门户内容范围：

| 栏目 | 内容 |
|---|---|
| 快速开始 | 获取发布包、执行 `python3.11 scripts/sync.py`、启动 OMP、打开门户 |
| 场景使用指南 | 安装后的日常开发路径：简单任务直接输入，复杂任务先计划，按需选择模型、并发、诊断与验证 |
| OMP 常用命令 | 日常 CLI / TUI 命令、用途、参数和示例 |
| OMP 内置工具 | `read`、`grep`、`wiki`、`task`、LSP 等工具的作用和典型场景 |
| OMP 常用配置 | 模型、Wiki、Agent、并发、权限等常用配置 |
| Skills | Skill 列表、功能、适用场景、是否必须手动调用、Agent 是否可自动选择 |
| 内置命令 | 当前 OMP Fork 实际提供的内置命令、功能和使用方式 |
| 内置 Agent | 当前 OMP Fork 实际提供的 Agent、职责、适用场景和调用方式 |
| 团队公共能力 | `/code-and-verify`、团队 Worker、团队 Skill 的使用说明 |
| FAQ / 最佳实践 | 常见问题和团队已经验证有效的方法 |
| 维护手册 | 构建、二进制更新、版本快照、验证、公共打包及公司资料接入 |
| 内部文档 | 浏览 `yellow/docs/` 中符合行数阈值的 Markdown；左侧每个已收录文件对应一个导航项，支持文件名筛选与正文搜索 |
| DFT知识 | 用可操作的电路演示解释 Scan、EDT 等概念，区分教学模型与真实硬件实现 |

#### 场景使用指南定位

在“开始使用”的“快速开始”之后提供独立页面 `usage-guide.html`，纳入分区导航与搜索，复用文章目录、代码复制和主题样式。

面向已完成安装同步的新手，按场景说明什么时候用、在哪里输入、可复制示例和下一步操作。覆盖启动与续接、模型与 Advisor、Plan 与 Vibe、并发协作、诊断修复、测试检查和长任务管理；完整参数仍由参考手册承载。

常用操作优先使用快捷键，键位以对应版本的 `fork.md` 为准；区分终端命令、OMP 输入框命令和自然语言任务。内容只介绍 OMP 与 Fork 自带能力，团队 Skills、Workers 和团队工作流留在“团队能力”分区。

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

内置命令页面标注手册参考版本。命令及 Agent 资料、中文用途、场景、参数和示例按需独立维护，不与二进制更新绑定。现有公共资料保留版本及源码出处，便于核对。手册参考版本不代表用户安装版本；涉及版本差异的操作须明确适用范围，并结合对应源码与实际运行核验。

命令详情页前置用途与可复制示例，再提供场景、参数和文件／状态影响说明。页面至少记录：

```text
命令
功能
典型场景
是否修改文件或外部状态
主要参数
示例
```

维护命令资料时应覆盖 `fullsend` 等生成式注册项和 JCH 命令，新增项缺少中文说明时校验失败。普通网站构建只使用公共内容和手册资料，可离线重建，无需联网或读取参考 clone。二进制更新不依赖 AST 提取器或网站构建。

### 6.4 内置 Agent 页面要求

手册参考版本 `v18.1.9+fork.170` 实际注册五个内置 Task Agent（以该标签的 `packages/coding-agent/src/task/agents.ts` 为依据）：

```text
scout
reviewer
security-reviewer
task
sonic
```

原方案列出的 `designer`、`librarian` 在此版本未注册，门户明确标注版本差异，不展示为可调用的内置能力。以后升级时重新核验，不沿用过期清单。

门户中对实际注册项逐项说明：

- 主要职责；
- 适合什么任务；
- 是否只读；
- 是否适合直接由用户指定；
- 如何通过 `task` 或相关入口使用。

团队自定义的 `document-worker`、`coding-worker`、`verification-worker` 单独列在“团队公共能力”中，避免与 OMP 内置 Agent 混淆。

### 6.5 门户交付要求

- 支持双击 `site/index.html` 通过 `file://` 浏览，也支持运行 `scripts/serve_site.py` 后通过 `http://127.0.0.1:9333/` 访问；页面与资源使用相对路径。
- 文章页提供侧栏导航、文章目录和代码复制；长文本可换行，宽表格与代码块局部滚动，避免整页横向溢出。“内部文档”侧栏按符合行数阈值的 Markdown 文件逐项列出，包含子目录文档，超限文件不列入导航。
- 首页、分区首页、文章与交互实验共用明暗主题，保证文字、代码和实验状态在两种主题下清晰可读。
- 样式、脚本、图片和搜索资源全部本地提供，全文搜索覆盖标题、正文、命令与 Skill 名称，支持中文关键词。
- 搜索框固定、结果区单独滚动，优先展示命令精确匹配及用途直接相关的常用命令；支持继续显示全部匹配结果、章节定位和正文高亮。点击结果后的查询只保留在本地页面地址中，不向外发送。搜索数据随页面直接加载，不使用 `fetch`；内部文档使用独立的 `yellow/.site/search-data.js`，不写入公共搜索资源。
- 不使用 CDN、在线字体或运行时下载。
- 公共门户源码、页面和本地资源全部纳入 Git；“内部文档”公共入口只含通用说明，不嵌入内部文件名、正文或索引。
- 内部页面、网页搜索数据、原始 Markdown、附件和 Wiki 数据库全部在 `yellow/` 中，不进入公共 Git 或公共发布包。浏览器通过统一导航进入内部页面，继续使用相同界面。
- 内部 Markdown 间链接指向对应生成页面，附件从原始 `yellow/docs/` 相对路径读取；原文保留不变。
- 禁用 JavaScript 时正文仍可阅读，内部页面可直接打开 `yellow/.site/index.html`；筛选、全文搜索与代码复制属于可选增强。
- 普通用户不需要安装网站构建环境。

### 6.6 公共手册的提交前行数检查

“开始使用／团队能力／维护手册／DFT知识”等公共 Markdown 位于 `portal/content/`，每份默认不能超过 3000 行。检查发生在 **Git 提交前**，不是网站生成时。超过阈值就报错、阻止提交，维护者须按主题拆成多个互相链接的页面，更新分区导航后重新暂存；不能通过丢弃页面、截断正文来规避要求。

`python3.11 scripts/maintenance/install_hooks.py` 安装本地 `pre-commit` 钩子，钩子运行 `tests/check_docs.py --staged`，检查真正准备提交的暂存区内容，不受未暂存修改影响。检查范围限定为公共手册，不读取 `yellow/`。公共阈值可由 `git config dft.docsMaxLines 3000` 配置，手动检查也可指定 `--max-lines`；公共提交阈值与公司文档构建阈值分别设置，均允许等于阈值。

新 clone 需安装一次钩子；安装不覆盖已有的其他钩子，也不自动提交或推送。检查与测试脚本全部放在根目录 `tests/`。

### 6.7 DFT 科普交互演示

- 核心知识必须覆盖：故障模型与 ATPG、覆盖率与测试质量、At-speed/LOC/LOS、OCC/时钟/复位、Scan 工程结构、EDT 约束与 X 处理、Test Point、JTAG/Boundary Scan、IJTAG、Wrapper/分层 DFT、MBIST/BIRA/BISR、LBIST、测试功耗与低功耗设计、完整工程流程与调试。
- 知识区采用 17 个独立页面：概念地图、原有 Scan/EDT 基础页，以及上述 14 项核心主题。按六条学习路线分组导航，分区首页展示主题摘要，文章提供上一主题/下一主题入口；公共课程清单维护于 `portal/metadata/dft-curriculum.json`。
- 每个核心主题提供中文原理、使用场景、常见误区、模型边界和公开第一方参考，并配可计算的交互实验。不得用固定“收益分数”、固定“测试通过”文案或只有模式名称变化的图形冒充演示结果。
- 以 JavaScript 驱动状态、时钟步进、模式切换和比较结果；显示层可采用 SVG 或 HTML，不把静态图片、装饰动画或预录视频当作交互实现。
- Scan、OCC、JTAG 等时序实验支持逐步观察状态与历史；改变输入条件后，旧比较结果不得继续作为当前结论。
- Scan 示例展示移入、捕获、移出，支持可编辑四位刺激、单步、播放/暂停、重置及示例故障切换；期望响应随输入计算。电路、元件讲解、SE/SI/SO 与沿前/沿后状态来自同一份记录；回看暂停但不改写历史。SO 明确为本沿采出的旧末级值，边沿序号不冒充物理时间。
- 工程排障演示根据用户配置的扫描断点、复位释放、X/mask 和捕获时序计算证据；修改条件清除旧结论。必须区分“响应一致”“观察点被屏蔽”“无法判定”和“取证结束”，不由流程走完自动宣称故障修复或签核通过。
- EDT 示例展示少量外部通道、解压映射、多条并行扫描链和响应压缩。提供正常响应、单错误可见和双错误抵消等教学场景，说明压缩信息丢失及比较结果的边界。
- 示例组合逻辑、位数和 XOR 映射须明确标记为教学模型，不宣称是实际 EDT 编码算法、真实工艺电路、故障覆盖率报告或 Sailor 插入结果。概念说明依据公开原始资料，参考链接不在运行时自动加载。
- 全部脚本与图形资源离线交付；禁用 JavaScript 仍可阅读静态电路和正文。验证真实步进数值、模式切换、播放暂停、重置和故障结果，不只检查按钮存在。
- 交互脚本拆分为主题资源，页面仅加载对应本地脚本；公开构建检查课程、Markdown、演示模板和脚本对应关系，缺页、缺资源或未处理标记必须失败。Python 3.11+ 测试入口可调用维护机 Node.js 验证浏览器 JavaScript 的纯计算模型；Node.js 不属于浏览网站、同步或构建网站的运行依赖。纯计算测试、静态检查和真实浏览器验收必须分别报告。

---

## 7. 实施计划

公共仓库、五分区门户、场景使用指南、明暗主题、DFT 交互、同步与打包机制已实现。后续以内容核验和公司项目试用为主；实现完成与环境验收分开记录，具体测试结果见 `VALIDATION.md`。

| 阶段 | 主要工作 | 交付物 |
|---|---|---|
| 1. 工具维护 | 运行单个 Python 更新脚本，下载并校验两类客户端 | OMP、Claude Code 两个实体，无状态文件 |
| 2. 公共仓库建设 | 建立 Git LFS、忽略规则、脚本分层、Skills、Workers、命令和黄区预留目录 | 公共效率仓库 |
| 3. 离线门户 | 五个独立分区、场景指南与参考手册、可追溯注册快照、DFT 交互、明暗主题与本地搜索 | 公共 `site/` 及网站源码 |
| 4. 黄区知识接入 | 原文与 Wiki 数据库接入，生成仅存黄区的内部页面并从同一门户浏览 | `yellow/docs/`、`yellow/.site/`、`yellow/docs.db` |
| 5. 红区同步机制 | 预检、停止当前用户 OMP、同步团队文件、二进制和可选数据库 | `scripts/sync.py` |
| 6. 电路生成能力 | 交付默认遵循 tiny_base 规范的 Skill，不在本仓库创建电路工程 | `generate-dft-circuit` 及参考规范 |
| 7. 离线交付与验收 | 隔离同步验证、源码清单核对、桌面门户检查、实体二进制公共打包 | `tests/`、验证记录与公共离线包 |
| 后续公司项目试用 | 在用户指定工程生成电路，依据真实库与 Sailor 资料验证工作流 | 单独记录的公司环境结果 |
| 持续维护 | 跟踪 OMP 上游和 Claude Code 版本，更新公共能力与资料 | 持续版本更新 |

当前交付不以完成公司 Sailor 插入为前提，也不在本仓库生成 tiny_base。后续可在用户指定项目中先用最小电路验证工作流，再进入复杂真实项目。

### 7.1 验收与交付边界

- 同步验证覆盖首次安装、重复同步、同名覆盖、个人文件保留、缺失/异常数据库、进程无法退出、空格路径及 LFS 指针；不得操作真实个人环境。
- 门户在桌面浏览器通过本地 HTTP 服务联调，同时保留 `file://` 兼容性检查；验证导航、搜索排序与滚动、复制、链接、明暗主题、横向溢出、资源与禁用 JavaScript 阅读。运行时无外部资源请求，不做小屏幕专项验证。
- 场景指南验证入口顺序、输入位置、操作步骤与版本适用性；源码核验和实际模型运行分别记录，未实测的场景不宣称通过。
- 内部文档验证已收录文件一文件一导航、子目录与附件链接、独立全文搜索，以及增删改后的重新生成。验证默认 3000 行、自定义阈值、2999/3000/3001 行边界、不同换行符、非法参数，以及降低阈值后的旧页面和索引清理。公共页面、索引、清单和公共包不得泄漏内部内容；`--public-only` 与公共打包不访问黄区。
- 公共提交检查验证暂存区与工作区内容不一致、3000/3001 行边界、超限报错、内部资料排除及实际 Git 钩子执行；测试使用 `.tmp/` 隔离仓库，不在真实仓库创建测试提交。
- 验证五个独立分区地址、分区首页布局及内容页侧栏、DFT 动画的实际数值和交互、无外部资源请求及禁用 JavaScript 阅读。
- 内容清单与固定版注册源码一致；两项 Skill、三个原生 Worker 和团队命令的发现与调用规则准确。Skill 场景覆盖已有测试框架、缺少 PAD 库、基础电路与明确要求的后续扩展。
- 公共离线包包含公共网页、共享能力、Python 脚本和真实二进制，不包含内部数据、凭据或 `.tmp/` 内容；公司内部资料按独立流程随 `yellow/` 交付。
- 最终报告分别列明实施结果、实际通过的验证、未执行的 CentOS 7/公司模型/数据库/PAD/Sailor 环境验证；不以静态检查冒充现场结果，不自动提交、推送或发布远端。

---

## 8. DFT 电路生成 Skill 与 tiny_base 默认规范

### 8.1 目标

本仓库交付 `generate-dft-circuit` Skill，**不直接创建 tiny_base 电路工程**。Skill 根据用户需求在指定目标工程生成 DFT 插入前电路；未要求其他结构时，默认采用本节 `tiny_base` 规范。

目的：

- 提供稳定、可重复的最小 DFT 测试输入；
- 为后续按真实 Sailor 资料验证 DFT 流程提供输入；
- 用于验证后续 OMP 代码修改、Skill 和 Agent 工作流；
- 避免一开始直接依赖大型真实项目。

按目标需求提供 RTL、文件清单、测试平台和 Python 3.11+ 验证入口，报告实际执行结果与缺口。不编造 Sailor 命令，不把缺少工具、库或环境的工作报告为完成。

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

上图仅表示后续可能扩展的目标，不属于初始电路交付内容。只有用户明确要求扩展时，才依据目标工程和真实 Sailor 资料增加对应特征。

### 8.3 原始电路

```text
TOP
└── CORE_A
    └── CORE_B
```

原始电路包含少量普通 DFF、组合逻辑、真实 Input/Output PAD、JTAG 接口预留和 Scan/EDT 后续复用接口。

真实 PAD 单元名称、方向、端口及连接方法必须从用户目标工程和指定库资料识别。缺少库信息时明确列出缺口，可先提供不依赖工艺库的核心逻辑，但不得伪造工艺单元或宣称已完成真实 PAD 接入。下图中的 Input/Output PAD 表示结构位置，不是可直接使用的工艺单元名称。

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

### 8.5 明确要求扩展时的 Sailor 验证顺序

以下为后续请求扩展时的参考顺序，不要求 Skill 在生成基础电路时自动执行：

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

每增加一项能力，都依据实际工具文档及库信息保留对应输入、配置、运行入口和结果，形成可重复 Case。未执行的插入、仿真或测试必须明确标记，不宣称插入成功。

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

派生 Case 不属于当前仓库交付项。只有用户明确请求时，才在指定工程增加目标功能所需结构；Base 稳定后再进入其他实际项目验证。
