# 本仓库维护规则

- 以最终实施计划及用户后续修订为准。目标是 CentOS 7，所有脚本使用 Python 3.11+。
- 二进制更新只使用 `scripts/maintenance/maintain_binaries.py`，`dist/` 仅保留两个实体，不保存版本或更新状态；无需克隆源码或更新元数据。手册资料独立维护并标注参考版本；需要核验源码时只在 `.tmp/` 作只读参考。
- 公共页面只读取 `portal/` 和公共元数据。按用户新增要求，默认网站构建另将 `yellow/docs/` Markdown 渲染到被忽略的 `yellow/.site/`，仅供本地“内部文档”入口浏览；内部正文、文件名及搜索索引不得进入公共 `site/` 或公共发布包。`--public-only` 不访问黄区；公共打包使用明确白名单且不读取黄区，公共版 `yellow/` 仅交付 `.gitignore`。
- 下载、缓存、构建中间文件、测试输出一律进入 `.tmp/`。真实二进制通过 Git LFS 管理，不接受 LFS 指针代替实体。
- 同步只覆盖团队同名文件，不改用户模型配置，不改 Shell 启动文件。同步测试必须隔离，不使用真实个人目录或真实 OMP 进程。
- 不在本仓库生成 tiny_base 工程；通过 `generate-dft-circuit` Skill 在用户指定项目生成。
- 变更需运行相关检查；不能把静态检查或模拟测试表述为公司环境验证。未经要求不提交、推送或发布远端。
- `scripts/` 顶层保留 `build_site.py`（生成网站）、`sync.py`（同步安装）和 `serve_site.py`（本地 HTTP 服务，固定监听 127.0.0.1:9333）；维护入口放 `scripts/maintenance/`，公共代码放 `scripts/_lib/`，测试与验收脚本统一放根目录 `tests/`。
- 门户分为开始使用、团队能力、维护手册、内部文档、DFT知识五个独立分区，各有独立首页及分区导航，不只切换同一份侧栏。
- 公司 Markdown 仅在网页构建时按 `--max-lines` 过滤，默认 3000，等于阈值允许。公共手册 `portal/content/` 在 Git 提交前检查暂存区，超过阈值报错，须拆成多个互相链接的页面；不在构建时过滤公共手册。用 `scripts/maintenance/install_hooks.py` 安装检查，检查逻辑放 `tests/check_docs.py`。
- DFT 交互演示以 JavaScript 驱动状态、控制和结果，显示层可用 SVG/HTML。教学模型须区分真实硬件与工具实现，不将玩具映射、示例故障或动画比较结果冒充真实 EDT、覆盖率或插入结果。
