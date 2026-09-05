# 内部文档

这里用于浏览 `yellow/docs/` 中符合行数条件的公司 Markdown 文档。左侧每个导航项对应一个已收录文件。

本地文档页面尚未生成时，将文档放入该目录并执行：

```bash
python3.11 scripts/build_site.py
```

默认只生成行数**不超过 3000** 的 Markdown 网页；可用 `--max-lines N` 调整阈值。超过阈值的文档不进入导航和网页搜索，原文仍保留。

生成后重新打开“内部文档”即可阅读。未启用 JavaScript 时，可直接打开本地 `yellow/.site/index.html`。
