# DFT AI 开发效率仓库

面向 CentOS 7 的团队公共能力与桌面离线门户。包含 OMP、Claude Code 实体二进制、2 项 Skill、3 个 Worker、`/code-and-verify` 和完整使用手册。公司资料仅在“内部文档”中本地浏览，不进入公共 Git、公共页面或发布包。

**门户入口：[site/index.html](site/index.html)**（可直接双击，或启动下述本地 HTTP 服务）。

## 五个独立分区

| 分区首页 | 内容 |
|---|---|
| [开始使用](site/start/index.html) | 快速开始、CLI/TUI、工具、配置与 FAQ |
| [团队能力](site/team/index.html) | 团队工作流、Skills 和 Workers |
| [维护手册](site/maintenance/index.html) | 构建、版本、提交检查与分发 |
| [内部文档](site/internal/index.html) | 仅在本地浏览符合行数条件的公司 Markdown |
| [DFT知识](site/dft/index.html) | 六条学习路线：测试原理、扫描与时钟、压缩与功耗、访问与分层、内建自测试、工程落地 |

每个分区有独立页面地址和自己的侧栏。DFT知识含 17 个页面，覆盖概念地图、Scan/EDT 基础及 14 项核心主题。实验使用本地 JavaScript 计算状态和结果，HTML/SVG 作为显示层；禁用 JavaScript 时仍可阅读静态电路和概念说明。课程清单位于 `portal/metadata/dft-curriculum.json`，主题脚本位于 `portal/assets/labs/`，浏览和构建网站均不需要 Node.js。

首页使用独立的 `portal/templates/home.html` 和本地首页动画，支持暂停及减少动态效果；首页正文只提供开始使用、团队能力、维护手册入口。文档页使用独立阅读样式，左侧限定当前模块搜索和目录，右侧跟随当前标题；支持代码复制、基础词法着色、表格滚动和图片放大。DFT 实验置于文章前方，画布可缩放，图中读数可选择查看；Scan、EDT、MBIST、LBIST 支持播放速度调整。阅读与画布增强位于 `portal/assets/reading.*`，不修改教学模型的计算规则。

当前主题为 B 午夜蓝。模块搜索支持分批继续显示全部结果、命中章节跳转，以及正文关键词高亮、上一处/下一处定位和清除高亮；本地查询不会发送到外部。代码块中的高亮不改变复制内容。

Scan 可编辑四位刺激，按同一份逐沿状态联动电路、元件讲解及历史记录；回看会暂停，不改写实验。工程排障页可调整断点、复位、X/mask 和捕获时序，计算响应与证据；未知、屏蔽或取证结束不会冒充测试通过。

OCC 支持单步、播放和速度调整，逐个记录源沿是否放行及计数；JTAG 列出全部 TAP 分支，按完整 TCK 拍记录上升沿动作、下降沿 Update 与 TDO 采出位。两页均支持历史回看；引脚条件或已提交指令变化后，旧比较结果失效。

## 离线使用

目标机须已有 Python 3.11+；二进制兼容性采用团队已确认结果。默认分发 Linux x64。

### 启动本地网站

三个独立入口分别负责生成网站（`scripts/build_site.py`）、同步安装（`scripts/sync.py`）和启动服务（`scripts/serve_site.py`）。启动服务只需 Python 标准库，不安装额外软件、不联网、不重新构建或同步，脚本随离线 ZIP 分发。

```bash
python3 scripts/serve_site.py
```

Windows 可用 `py -3 scripts/serve_site.py`，或自己的 Python 3.11+ 解释器。浏览器访问 **http://127.0.0.1:9333/**，终端保持运行，按 **Ctrl+C** 停止。脚本支持从任意目录通过绝对路径启动；缺少已生成首页或端口被占用时会报错退出。

服务仅监听本机，不对其他电脑开放。首页自动跳转至 `/site/index.html`，保留公共页面、内部生成页和原文附件之间的相对链接；只提供 `site/`、`yellow/.site/` 和 `yellow/docs/` 内的静态文件，不提供目录列表或 `yellow/docs.db`。公共离线包仍不包含内部文档。

### 同步安装

```bash
python3 scripts/sync.py --dry-run
python3 scripts/sync.py
export PATH="$HOME/.local/bin:$PATH"
cd /path/to/your/project
omp
```

支持从任意目录使用脚本绝对路径运行。正式同步先预检再停止当前用户 OMP，覆盖 `~/.omp/agent/` 中团队同名文件和 `~/.local/bin/` 中二进制；不删除其他用户文件，不改模型配置或 Shell 启动文件。缺少 `yellow/docs.db` 时保留个人数据库；异常数据库或活动 WAL/SHM/journal 不覆盖。

内部原始文档在公司环境接入 `yellow/docs/`，实际绝对路径写入同步后的团队上下文。默认同步不处理命名 profile 或 `PI_CODING_AGENT_DIR` 重定向目录。

```text
/code-and-verify <需求>
/skill:generate-unit-tests <修改范围>
/skill:generate-dft-circuit <目标工程和需求>
```

两项 Skill 也可自动选择。电路 Skill 默认 `TOP → CORE_A → CORE_B`，不预置 DFT 结构；缺少真实 PAD 库时不伪造单元。本仓库不创建 tiny_base 电路工程。

## 二进制

`dist/` 只保留 `omp/omp`、`claude-code/claude` 两个 Linux 实体文件，不保存版本、来源、校验清单或更新状态。版本可在目标机运行 `omp --version`、`claude --version` 查看。

二进制使用 Git LFS：Git 获取者在外围运行 `git lfs pull`；离线 ZIP 已包含实体，不需要 LFS。Claude Code 不保证具有 OMP 的定制 Wiki 和团队命令。

## 仓库结构

| 目录 | 内容 |
|---|---|
| dist/ | 仅 OMP、Claude Code 两个实体二进制 |
| licenses/ | 随仓库保留的 OMP 许可与第三方声明 |
| omp/ | 团队规则、Skills、Markdown 命令和 OMP 原生 Worker |
| portal/ | 公共 Markdown、中文说明表、版本快照、模板和本地资源 |
| site/ | 已生成的公共门户与公共全文搜索资源，全部纳入 Git |
| scripts/ | 顶层为网站构建、同步安装和启动本地服务；维护入口及公共代码放子目录 |
| tests/ | 隔离测试、静态验证与桌面浏览器验收 |
| yellow/ | 公共版仅有 .gitignore；docs/ 放公司原文，.site/ 放本地生成的内部文档页面，两者均忽略 |
| .tmp/ | 忽略的参考 clone、下载缓存、测试输出和离线发布包 |

## 维护

所有脚本直接使用本地已安装的 Python 3.11+。同步、二进制维护、静态验证和打包仅用标准库；网页构建依赖 Jinja2/Markdown。先用 `python3 --version` 确认版本至少为 3.11；Windows 用 `py -3 --version`，并将下列命令中的 `python3` 换成 `py -3`。默认版本不满足要求时，改用本地已安装的 Python 3.11+ 解释器绝对路径，安装依赖和运行脚本使用同一个解释器。

```bash
python3 -m pip install --cache-dir .tmp/pip-cache -r requirements-build.txt
python3 scripts/build_site.py
python3 tests/verify.py
python3 scripts/maintenance/package.py
```

离线重建前须预先安装 `requirements-build.txt` 中依赖或带入适合维护机的 wheel；普通用户只浏览已生成页面，无需构建环境。`package.py` 在 `.tmp/releases/` 生成 ZIP、SHA-256 和包清单，核对 ZIP CRC 与包内实体哈希；不读取或收录黄区数据。

### 内部文档

将公司 Markdown 和附件放入 `yellow/docs/`，执行 `scripts/build_site.py` 后，点击网站顶部“内部文档”。默认只为**行数不超过 3000** 的 Markdown 生成网页；左侧每个已收录文件对应一个导航项，可筛选文件名并搜索正文。内部输出仅在 `yellow/.site/`，不会混入公共网站或发布包；原文不变。文档有增删改后重新构建即可。

用 `--max-lines N` 修改内部 Markdown 的行数阈值，例如：

```bash
python3 scripts/build_site.py --max-lines 3000
```

阈值必须为正整数，按 `<= N` 筛选：默认 3000 行允许，3001 行及以上跳过。行数包含空行，兼容 LF/CRLF，末尾无换行的一行也计入。超限文档不生成页面、不进入导航或网页搜索；降低阈值后会清理此前生成的超限页面。跳过的文件及行数记录在 `yellow/.site/manifest.json`，原始 Markdown 和 `yellow/docs.db` 不变。此参数仅在构建时过滤公司文档，不筛选公共手册。

只构建公共部分且不访问黄区时使用 `python3 scripts/build_site.py --public-only`。

### 公共手册提交检查

“开始使用／团队能力／维护手册／DFT知识”等公共手册位于 `portal/content/`，行数检查放在 Git 提交前，**不是网页生成时**。每份 Markdown 默认不能超过 3000 行；超限须按主题拆成多个互相链接的页面，不能靠跳过页面通过检查。

```bash
python3 scripts/maintenance/install_hooks.py
python3 tests/check_docs.py
```

安装后 `pre-commit` 自动检查**暂存区中的 Markdown**，未暂存修改不会改变检查结果，也不读取内部文档。新 clone 需安装一次；迁移 Python 环境后重新安装。现有其他钩子不会被覆盖。公共提交阈值可用 `git config dft.docsMaxLines 3000` 配置，手动检查可用 `python3 tests/check_docs.py --staged --max-lines 3000`。这些操作不自动提交或推送。

外围更新二进制：

```bash
python3 scripts/maintenance/maintain_binaries.py
```

这一个脚本仅依赖 Python 标准库，下载 OMP 最新正式发行版和 Claude Code stable，校验发行方 SHA-256 后替换两个二进制。默认 Linux x64，可加 `--arch arm64`。临时下载自动清理，不生成状态文件，也不需要克隆源码、安装 AST 依赖或更新文档快照。

门户内容单独维护：`portal/content/` 保存正文，`portal/catalog/` 保存中文说明，`portal/metadata/omp.json` 保存手册引用的命令资料。手册标注自身参考版本，不与 `dist/` 绑定；更新二进制无需重建网站。

## 验证

```bash
python3 tests/test_sync.py
python3 tests/test_metadata.py
```

桌面浏览器检查需要提前准备 Playwright 及其 Chromium，浏览器安装位置通过 `PLAYWRIGHT_BROWSERS_PATH=.tmp/browsers` 指定。运行 `tests/test_portal.py`，截图与结果保存到 `.tmp/browser-check/`。所有同步测试使用隔离目录；Linux 下另测真实 `/proc` 识别及仅对测试进程的 SIGTERM。

详见 [VALIDATION.md](VALIDATION.md)。公司模型、CentOS 7、真实 PAD 库与 Sailor 验证单独记录；本地验证不能替代现场结果。不自动提交、推送或发布。

DFT 新主题的纯计算测试由 Python 入口调用维护机的 Node.js（仅测试需要），不启动浏览器或服务器：

```bash
python3 -m unittest tests.test_dft_curriculum tests.test_dft_scan tests.test_dft_faults tests.test_dft_clocks tests.test_dft_access tests.test_dft_bist tests.test_dft_compression_power tests.test_dft_flow
```

此命令检查教学模型的已知数值、状态和边界，以及生成页面的课程/资源绑定；不能代替真实浏览器交互与视觉验收。

页面呈现契约及可选纯 DOM 检查：`python3 -B -m unittest tests.test_presentation`。纯 DOM 检查需要维护机安装 `linkedom@0.18.12` 到 `.tmp/dom-check/`（安装命令见测试文件）；未安装时该项明确跳过。它不启动浏览器，不验证 CSS 排版、实际图片放大或视觉效果。网站运行和构建不依赖此包。

完整设计与实施要求见 [最终版文档](本仓库项目自身相关文档/DFT_OMP_AI开发提效方案与实施计划_最终版.md)，已同步 Python 入口、脚本分层、桌面门户、内部文档分区存储及电路生成 Skill 等确认事项。
