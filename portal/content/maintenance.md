# 维护与版本

## 日常离线重建

普通使用者浏览已生成的 `site/` 无需安装构建依赖。维护者直接使用本地已安装的 Python 3.11+，在仓库根目录向同一个解释器安装 `requirements-build.txt` 中的依赖。先运行 `python3 --version`（Windows 用 `py -3 --version`）确认版本至少为 3.11；若默认命令对应旧版本，请改用已安装的 Python 3.11+ 解释器绝对路径。首次安装依赖需要可访问的软件源；离线重建前须预先安装依赖或准备适合维护机的 wheel。

Linux（Python 3.11+）：

```bash
python3 -m pip install --cache-dir .tmp/pip-cache -r requirements-build.txt
python3 scripts/build_site.py
```

Windows PowerShell（使用本地 Python 3 启动器）：

```powershell
py -3 -m pip install --cache-dir .tmp/pip-cache -r requirements-build.txt
py -3 scripts/build_site.py
```

后续重建直接运行同一个本地解释器的构建命令，无需重复安装依赖；仅生成公共网站时，在命令末尾加 `--public-only`。`site/` 删除后也可通过上述命令重新生成，前提是保留 `portal/` 等构建源文件。

构建完成后可校验并打包（Windows 将下面的 `python3` 换为 `py -3`）：

```bash
python3 tests/verify.py
python3 scripts/maintenance/package.py
```

构建公共页面后，默认另将 `yellow/docs/` 中行数不超过 3000 的 Markdown 生成为本地内部文档页；不会在线更新 Fork 资料。打包必须有经过校验的真实二进制。

## 内部文档浏览

将公司 Markdown 及其本地附件放入 `yellow/docs/`，运行 `python3 scripts/build_site.py`，再点击顶部“内部文档”。左侧每个导航项对应一个符合行数条件的 Markdown 文件，支持文件名筛选、正文搜索和文档间跳转。

`--max-lines N` 控制内部 Markdown 的行数阈值，默认 `3000`，必须是正整数。例如：

```bash
python3 scripts/build_site.py --max-lines 3000
```

按行数 **不超过 N** 收录：3000 行允许，3001 行及以上默认跳过。空行计入行数；LF/CRLF 换行均支持，末尾没有换行的非空行也计入。超限文档不生成网页，也不进入导航和网页搜索；原始 Markdown 与 Wiki 数据库不变，正文中指向超限文档的链接回到原始文件。跳过清单及实际行数仅保存在 `yellow/.site/manifest.json`。降低阈值重新构建后，会清除原先生成的超限页面。此参数仅在构建时过滤公司文档，公共手册不在构建时过滤或做行数限制校验。

内部输出单独保存在 `yellow/.site/`，不写入公共 `site/`、公共搜索索引或发布包，且由黄区 Git 忽略规则覆盖。原始文件保持不变。新增、修改或删除文档后重新构建即可更新导航和页面。

仅重建公共部分且完全不访问黄区时使用：

```bash
python3 scripts/build_site.py --public-only
```

## 外围更新发行版

```bash
python3 scripts/maintenance/maintain_binaries.py
```

只需这一个 Python 脚本，使用标准库下载 OMP 最新正式发行版和 Claude Code `stable`，验证发行方 SHA-256 后替换实体。默认 Linux x64，可指定 `--arch arm64`。

`dist/` 只有 `omp/omp`、`claude-code/claude` 两个二进制，不保存 VERSION、JSON、校验清单或更新状态。临时文件在下载结束或失败后自动清理；两个下载都通过校验后才开始替换。更新不需要克隆源码、安装 AST 依赖、更新元数据或重建网站，也不安装到用户环境。

版本直接在目标机运行 `omp --version`、`claude --version` 查看。

## 内容维护

门户有五个独立分区：首页位于 `site/start/`、`site/team/`、`site/maintenance/`、`site/internal/`、`site/dft/`，各自拥有独立导航。公共文章保留在 `site/pages/`；内部正文只在 `yellow/.site/`。

公共 Markdown 的行数在提交前检查，默认最多 3000 行。新 clone 安装一次钩子：

```bash
python3 scripts/maintenance/install_hooks.py
```

Git 提交时，钩子运行 `tests/check_docs.py --staged`，检查 `portal/content/` 的暂存内容；超过阈值则报错，须拆成多个页面、更新相关导航和链接，再重新暂存提交。不检查公司文档，也不在网站生成时执行公共行数限制。

可提前运行 `python3 tests/check_docs.py` 检查工作区；公共提交阈值由 `git config dft.docsMaxLines 3000` 配置，默认为 3000，等于阈值允许。公共提交阈值与内部构建参数分别设置。检查只报告问题，不自动提交、截断内容或代替语义拆页。

`portal/content/` 维护 Markdown 正文；`portal/catalog/` 维护命令中文解释；`portal/metadata/omp.json` 保存手册引用的命令资料与参考版本。文档按需单独更新，不与二进制版本绑定。新增项缺说明或本地链接失效时验证失败。

公共页面和 CSS/JavaScript 均在 `site/` 交付并纳入 Git；内部页面及搜索数据仅保存在 `yellow/.site/`。两者搜索均采用本地 JS 数据，不使用 fetch、CDN 或在线字体。内部文档的外部图片不会自动加载；外部来源链接仅在用户主动打开时联网。

## 公共发布包

`scripts/maintenance/package.py` 输出 `.tmp/releases/` 中的 ZIP 与 SHA-256；包内有共享能力、维护脚本、公共源码、生成门户和 Linux 实体二进制。仅按文件白名单选入内容，合成一个空黄区的 `.gitignore`；不读取公司数据或打包 `.tmp/`。

OMP 已有许可和第三方声明保留在 `licenses/omp/`，随公共包交付。Claude Code 为原厂客户端，本仓库不对其声明自有许可证。打包不会向远端发布。

## 公司红区内部交付

公共发布包继续使用白名单，不读取黄区。内部交付由公司批准的工具单独完成，不放宽公共打包脚本。

在黄区完成生成后，检查 `yellow/.site/build-report.html`，处理读取失败、缺失引用、隐藏附件目录和被清理的表现形式；超限文件须确认是否拆分或调整 `--max-lines`。超过阈值的原文须保留。

内部包保留完整目录关系：`site/`、隐藏目录 `yellow/.site/`、`yellow/docs/`（原文、图片及附件）及 `scripts/`。需要安装能力时再随公共包保留 `omp/`、`dist/` 等；需要 OMP Wiki 时加入经批准的 `yellow/docs.db`，并完成数据库检查。不能只复制 `site/`，也不能漏掉 `.site`。

用公司工具生成最终包，解压到另一个目录后，从维护仓库执行：

```bash
python3 tests/verify_delivery.py --root /path/to/extracted-delivery
```

检查生成文件哈希、公共/内部构建一致性、原文和被引用附件、链接、锚点、内部搜索、HTTP 路径兼容及清单计数。存在被清理的引用或读取失败时验收不通过。私有报告只写维护仓库 `.tmp/delivery-verification.json`，不放公共 `site/`；报告保留构建标识、内部生成时间、文档计数和问题明细。

在解压目录启动 `scripts/serve_site.py` 后，再加 `--http-base http://127.0.0.1:9333` 验证实际 HTTP 文件内容。还须在目标浏览器断网检查直接打开与 HTTP 打开、内部入口、搜索、交互和网络请求；脚本静态验收不替代浏览器或公司环境验收。

交付清单由维护者记录源码 commit（有未提交修改须注明）、门户构建标识、资料批次、内部生成时间、最终包 SHA-256、上述验收报告，以及目标机实际 `omp --version` / `claude --version` 输出。基础手册版本、各文章参考提交和实际软件版本分别记录，不相互替代。

## 本地与集中访问

个人使用：每人获取完整交付包，直接打开网页或在自己的机器启动服务。`127.0.0.1:9333` 只指向当前机器，管理员启动后不能用其他同事的回环地址访问它。

集中访问：由公司批准的静态服务以交付根目录为根提供内部地址，保留上述路径关系并限定资源范围。个人服务仍固定监听 `127.0.0.1:9333`。

只读共享目录下安装前，先复制交付内容到个人可写目录。同步会在停止 OMP 前检查暂存目录，正式执行还会先创建暂存文件；`--dry-run` 只读检查权限，不承诺之后的磁盘状态不变。

## 验证边界

本机隔离测试不触碰真实个人 OMP 目录。Windows 可执行 Python 逻辑和浏览器 `file://` 测试，Linux /proc 进程机制需在 Linux 下验证。CentOS 7、公司模型、PAD 库及 Sailor 的现场运行结果必须单独记录，不能用本地测试替代。
