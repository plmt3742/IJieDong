# scripts · 跨端脚本

> 状态：占位（B-002 起逐步补充）。

## 职责

- 开发启动/构建编排。
- OpenAPI 导出/类型生成。
- 文档链接检查、目录校验。
- 数据导入/种子（如跨端）。

## 计划文件

```text
export-openapi.sh / .ps1
check-links.py
check-no-emoji.py
dev.ps1 / dev.sh
```

## 边界

- 不放业务逻辑。
- 一次性临时脚本放 `tools/`（gitignore）。
- 脚本要能在 Windows + Linux 跑，或提供两种实现。
- 不把密钥写进脚本；用环境变量。

## 当前

- `check-links.py`：文档内链检查。
- `check-no-emoji.py`：工程 Markdown 不使用 emoji 的校验。
