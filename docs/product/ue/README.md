# 页面结构地图（低保真）

> 入口：用浏览器打开 [`page-map.html`](page-map.html)。  
> 想直接看首页：打开 [`page-map.html#MP01`](page-map.html#MP01)。  
> 本目录输出**结构/交互/数据流**，不含品牌色、视觉风格或高保真 UI。

## 1. 产物

| 文件 | 说明 |
|---|---|
| `page-map.html` | 可离线打开的单文件页面地图；支持平移/缩放/搜索/模块定位/点击页面看详情/导出 PNG |
| `wireframes.html` | 18 页低保真线框总览（灰度、无品牌风格）；每页可跳到地图详情 |
| `ue-spec.json` | UE 模型：18 个页面、29 条跳转、实体/数据流/限制 |
| `screens/*.html` | 每页低保真线框（静态、无脚本） |
| `screens/*.png` | 每页截图（地图缩略图/导出用） |
| `screens/source.css` | 灰度线框样式（无品牌风格） |
| `build_ue.py` | 重新生成线框、截图、`ue-spec.json`、`wireframes.html` |
| `verify_map.py` | Playwright 冒烟：页面数/跳转/搜索/缩放/导出 |
| `verify_wireframes.py` | Playwright 冒烟：线框总览 18 卡片/18 地图链接 |
| `verification/` | 验证截图与导出样例 |

## 2. 怎么用

0. 只想逐页看线框：打开 `wireframes.html`；每张卡片底部可跳到地图详情。
1. 直接双击/浏览器打开 `page-map.html`。
2. 滚轮/触控缩放；拖动平移；`0` 或“全览”复位。
3. 顶部“全部页面”按模块定位：小程序入口/浏览/AI、后台登录/数据/管理。
4. 搜索页面名/ID（`/` 快捷键）。
5. 点击页面框 → 右侧出现“布局 / 入口 / 交互”三个页签：
   - **布局**：页面板块、滚动归属；
   - **入口**：从哪个页面、点什么、带什么数据；
   - **交互**：点什么 → 到哪个页面/状态；状态规则。
6. 点详情里的目标缩略图 → 跳到对应页面。
7. 选中页面后右上角“导出 PNG”：
   - 页面图片：只含当前页；
   - UE 标注图片：页面 + 布局/入口/交互。

## 3. 页面范围

| 端 | 页面 |
|---|---|
| 小程序 | MP00 启动/登录、MP01 首页、MP02 区域列表、MP03 区域详情、MP04 指标详情、MP05 AI 空、MP06 AI 答案、MP07 会话（P1）、MP08 无权限/帮助 |
| 后台 | AD01 登录、AD02 总览、AD03 数据列表、AD04 数据编辑、AD05 导入、AD06 导入记录、AD07 审计、AD08 用户（P1）、AD09 问答记录（P1） |

未包含：地图/大屏、导出/多年趋势、粤政易 SSO 页面、公众版。详见 `ue-spec.json` 的 `coverage` / `limitations`。

## 4. 数据流（摘要）

- `MP05 → MP06`：提交问题 → `/ai/chat` 返回 answer/chart_spec/citations → 写 `chat_messages`/`audit_logs`。
- `MP06 → MP04`：点引用 → 带 `region_id`/`indicator_id`/`period` 回到指标详情。
- `AD05 → AD03/MP01`：导入/发布成功 → 数据更新；小程序首页读取最新 `data_values`。
- `AD03 → AD04 → AD03`：编辑抽屉保存 → `data_values` + `audit_logs`。

完整表见 [`../05-page-structure.md`](../05-page-structure.md)。

## 5. 重新生成

前置：Python 3.13、Playwright、Chrome；技能目录 `frontend-to-ue` 可用。

```bash
# 1) 生成线框 + 截图 + ue-spec.json
python -X utf8 docs/product/ue/build_ue.py

# 2) 渲染单文件地图（技能自带 render_map.py）
python -X utf8 <frontend-to-ue>/scripts/render_map.py docs/product/ue \
  --out docs/product/ue/page-map.html --title "i揭东"

# 3) 冒烟
python -X utf8 docs/product/ue/verify_map.py
```

> Windows 控制台默认 GBK 会报 `UnicodeDecodeError`，所有命令加 `-X utf8`。

## 6. 验证记录（2026-11-06）

- 18 个页面、29 条跳转。
- 打开 `#MP01` 后：详情面板显示“首页”；交互页签 6 张流程卡；点目标可跳到“区域列表”。
- 模块菜单 7 项；切到“小程序 · 入口”成功。
- 搜索“导入”返回 2 条；缩放按钮生效。
- 页面图 `export-MP04.png` 与 UE 标注图 `export-MP04-annotated.png` 均导出成功。
- 浏览器 console errors：0。
- `wireframes.html`：18 张卡片、18 个地图链接、0 console errors。
- 截图/导出样例见 `verification/`。

## 7. 限制

- 低保真结构线框，不是最终 UI；颜色统一灰度，避免视觉风格干扰。
- 页面/接口为**设计契约**；后端尚未实现，数据值为演示占位。
- 未包含粤政易 SSO/工作台入口；后期接入需补页面与流程。
- 导出 PNG 依赖浏览器 Canvas；超大画布/字体差异可能导致尺寸变化。
- 线框中的“演示数据”不是真实统计。
