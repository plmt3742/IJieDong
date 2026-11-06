# apps/mp · 原生微信小程序

> 状态：占位（B-002 创建可运行脚手架）。

## 职责

- 首页总览、区域树、区域详情、指标详情。
- 图表（ChartSpec 渲染）。
- AI 问答、引用展示、追问。
- 微信登录（后期）；粤政易入口（更后期）。

## 技术栈

- **原生微信小程序 + TypeScript + WXML + WXSS**
- UI：TDesign Miniprogram
- 图表：echarts-for-weixin（自定义构建）
- 网络：自封装 `services/request.ts`

> 不做 H5；如粤政易强制 H5，再评估薄 H5 壳。

## 目录（计划）

```text
apps/mp/
├── project.config.json
├── project.private.config.json   # 本地，gitignore
├── package.json
├── tsconfig.json
├── .env.example
├── miniprogram/
│   ├── app.ts
│   ├── app.json
│   ├── app.wxss
│   ├── sitemap.json
│   ├── pages/                    # 首页/区域/指标/问答/我的
│   ├── components/               # chart/region-card/empty/loading
│   ├── services/                 # request/api
│   ├── utils/
│   ├── types/
│   ├── images/
│   └── styles/
└── typings/
```

## 边界

- 只放小程序代码；不放后台/后端。
- 不直连数据库/LLM；不保存 Key/AppSecret。
- 不写死 API 域名；用环境配置。
- 不把 ECharts option 写进页面；用 ChartSpec 渲染器。

## 下一步（B-002）

1. 原生小程序脚手架 + TypeScript + npm 构建。
2. 微信开发者工具打开；首页可运行。
3. request 封装 + 一次 API 联调。
4. 一张柱状图 spike（验证 echarts-for-weixin/包体）。
