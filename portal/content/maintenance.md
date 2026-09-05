# 维护与版本

## 日常离线重建

普通使用者无需安装任何构建依赖。维护者具备 Python 3.11+，提前准备 `requirements-build.txt` 所列依赖即可离线重建：

```bash
python3.11 scripts/build_site.py
python3.11 tests/verify.py
python3.11 scripts/maintenance/package.py
```

构建公共页面后，默认另将 `yellow/docs/` 中行数不超过 3000 的 Markdown 生成为本地内部文档页；不会在线更新 Fork 资料。打包必须有经过校验的真实二进制。

## 内部文档浏览

将公司 Markdown 及其本地附件放入 `yellow/docs/`，运行 `python3.11 scripts/build_site.py`，再点击顶部“内部文档”。左侧每个导航项对应一个符合行数条件的 Markdown 文件，支持文件名筛选、正文搜索和文档间跳转。

`--max-lines N` 控制内部 Markdown 的行数阈值，默认 `3000`，必须是正整数。例如：

```bash
python3.11 scripts/build_site.py --max-lines 3000
```

按行数 **不超过 N** 收录：3000 行允许，3001 行及以上默认跳过。空行计入行数；LF/CRLF 换行均支持，末尾没有换行的非空行也计入。超限文档不生成网页，也不进入导航和网页搜索；原始 Markdown 与 Wiki 数据库不变，正文中指向超限文档的链接回到原始文件。跳过清单及实际行数仅保存在 `yellow/.site/manifest.json`。降低阈值重新构建后，会清除原先生成的超限页面。此参数仅在构建时过滤公司文档，公共手册不在构建时过滤或做行数限制校验。

内部输出单独保存在 `yellow/.site/`，不写入公共 `site/`、公共搜索索引或发布包，且由黄区 Git 忽略规则覆盖。原始文件保持不变。新增、修改或删除文档后重新构建即可更新导航和页面。

仅重建公共部分且完全不访问黄区时使用：

```bash
python3.11 scripts/build_site.py --public-only
```

## 外围更新发行版

```bash
python3.11 scripts/maintenance/maintain_binaries.py
```

只需这一个 Python 脚本，使用标准库下载 OMP 最新正式发行版和 Claude Code `stable`，验证发行方 SHA-256 后替换实体。默认 Linux x64，可指定 `--arch arm64`。

`dist/` 只有 `omp/omp`、`claude-code/claude` 两个二进制，不保存 VERSION、JSON、校验清单或更新状态。临时文件在下载结束或失败后自动清理；两个下载都通过校验后才开始替换。更新不需要克隆源码、安装 AST 依赖、更新元数据或重建网站，也不安装到用户环境。

版本直接在目标机运行 `omp --version`、`claude --version` 查看。

## 内容维护

门户有五个独立分区：首页位于 `site/start/`、`site/team/`、`site/maintenance/`、`site/internal/`、`site/dft/`，各自拥有独立导航。公共文章保留在 `site/pages/`；内部正文只在 `yellow/.site/`。

公共 Markdown 的行数在提交前检查，默认最多 3000 行。新 clone 安装一次钩子：

```bash
python3.11 scripts/maintenance/install_hooks.py
```

Git 提交时，钩子运行 `tests/check_docs.py --staged`，检查 `portal/content/` 的暂存内容；超过阈值则报错，须拆成多个页面、更新相关导航和链接，再重新暂存提交。不检查公司文档，也不在网站生成时执行公共行数限制。

可提前运行 `python3.11 tests/check_docs.py` 检查工作区；公共提交阈值由 `git config dft.docsMaxLines 3000` 配置，默认为 3000，等于阈值允许。公共提交阈值与内部构建参数分别设置。检查只报告问题，不自动提交、截断内容或代替语义拆页。

`portal/content/` 维护 Markdown 正文；`portal/catalog/` 维护命令中文解释；`portal/metadata/omp.json` 保存手册引用的命令资料与参考版本。文档按需单独更新，不与二进制版本绑定。新增项缺说明或本地链接失效时验证失败。

公共页面和 CSS/JavaScript 均在 `site/` 交付并纳入 Git；内部页面及搜索数据仅保存在 `yellow/.site/`。两者搜索均采用本地 JS 数据，不使用 fetch、CDN 或在线字体。内部文档的外部图片不会自动加载；外部来源链接仅在用户主动打开时联网。

## 公共发布包

`scripts/maintenance/package.py` 输出 `.tmp/releases/` 中的 ZIP 与 SHA-256；包内有共享能力、维护脚本、公共源码、生成门户和 Linux 实体二进制。仅按文件白名单选入内容，合成一个空黄区的 `.gitignore`；不读取公司数据或打包 `.tmp/`。

OMP 已有许可和第三方声明保留在 `licenses/omp/`，随公共包交付。Claude Code 为原厂客户端，本仓库不对其声明自有许可证。打包不会向远端发布。

## 验证边界

本机隔离测试不触碰真实个人 OMP 目录。Windows 可执行 Python 逻辑和浏览器 `file://` 测试，Linux /proc 进程机制需在 Linux 下验证。CentOS 7、公司模型、PAD 库及 Sailor 的现场运行结果必须单独记录，不能用本地测试替代。
