#!/usr/bin/env python3
"""Build low-fidelity wireframes, screenshots, and ue-spec.json for the page map.

Usage:
  python docs/product/ue/build_ue.py
  python <frontend-to-ue>/scripts/render_map.py docs/product/ue --out docs/product/ue/page-map.html --title "i揭东"

Requires: playwright (Python) + local Chrome/Chromium.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCREENS = ROOT / "screens"
SCREENS.mkdir(parents=True, exist_ok=True)

CSS = r"""
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff;color:#202020}
body{font:13px/1.5 "Microsoft YaHei","PingFang SC",Arial,sans-serif}
.phone{width:375px;height:812px;display:flex;flex-direction:column;background:#fff;border:1px solid #cfcfcf;overflow:hidden}
.status{height:26px;display:flex;align-items:center;justify-content:space-between;padding:0 14px;font-size:10px;color:#666;border-bottom:1px solid #eee;flex:none}
.nav{height:48px;display:flex;align-items:center;gap:10px;padding:0 14px;border-bottom:1px solid #e6e6e6;font-weight:600;flex:none}
.nav .back{font-size:18px;color:#555;font-weight:400}
.nav .grow{flex:1}
.content{flex:1;padding:13px;display:flex;flex-direction:column;gap:11px;overflow:hidden;min-height:0}
.bottom{height:54px;border-top:1px solid #e6e6e6;display:flex;align-items:center;justify-content:space-around;font-size:10px;color:#777;flex:none}
.bottom span{display:flex;flex-direction:column;align-items:center;gap:3px}
.bottom .active{color:#111;font-weight:700}
.bottom i{display:block;width:16px;height:16px;border:1px solid #aaa;border-radius:3px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.metric{border:1px solid #d8d8d8;background:#fafafa;padding:9px;display:flex;flex-direction:column;gap:3px;min-height:58px}
.metric span{font-size:10px;color:#666}
.metric b{font-size:18px;font-weight:650}
.wire{border:1px dashed #bbb;background:#f7f7f7;display:flex;align-items:center;justify-content:center;color:#777;text-align:center;padding:8px;font-size:11px}
.card{border:1px solid #d8d8d8;background:#fff;padding:10px;display:flex;flex-direction:column;gap:8px;min-height:0}
.card-title{font-size:11px;font-weight:700;color:#444;display:flex;justify-content:space-between;align-items:center}
.section-title{font-size:12px;font-weight:700;color:#333;display:flex;justify-content:space-between;align-items:center}
.tiny{font-size:10px;color:#777}
.muted{color:#777}
.list{display:flex;flex-direction:column;gap:0;border:1px solid #ddd}
.list .item{display:flex;align-items:center;justify-content:space-between;padding:10px;border-bottom:1px solid #eee;font-size:12px;background:#fff}
.list .item:last-child{border-bottom:0}
.tabs{display:flex;border:1px solid #ddd;background:#fafafa}
.tab{flex:1;text-align:center;padding:7px 0;font-size:11px;color:#666;border-right:1px solid #eee}
.tab:last-child{border-right:0}
.tab.active{background:#fff;color:#111;font-weight:700}
.input{border:1px solid #ccc;background:#fff;padding:9px 10px;font-size:11px;color:#888;min-height:36px;display:flex;align-items:center}
.input-bar{display:flex;gap:6px;margin-top:auto}
.input-bar .input{flex:1}
.btn{border:1px solid #999;background:#fff;padding:7px 10px;font-size:11px;text-align:center;display:inline-flex;align-items:center;justify-content:center;color:#222}
.btn.primary{background:#f0f0f0;border-color:#666;font-weight:700}
.btn.block{width:100%}
.chart{border:1px solid #ddd;background:#fafafa;padding:10px;display:flex;align-items:flex-end;gap:8px;height:150px}
.chart .bar{flex:1;background:#d9d9d9;border:1px solid #bbb;display:flex;align-items:flex-start;justify-content:center;font-size:9px;color:#555;padding-top:3px}
.chart .bar:nth-child(2){height:45%}.chart .bar:nth-child(3){height:70%}.chart .bar:nth-child(4){height:55%}.chart .bar:nth-child(5){height:85%}.chart .bar:nth-child(6){height:35%}
.table{width:100%;border-collapse:collapse;font-size:11px;background:#fff}
.table th,.table td{border:1px solid #e2e2e2;padding:7px 8px;text-align:left;vertical-align:top}
.table th{background:#f5f5f5;font-weight:700;color:#444}
.table td{color:#555}
.pill{display:inline-block;border:1px solid #ccc;background:#f7f7f7;padding:1px 6px;font-size:9px;color:#555}
.bubble{max-width:88%;border:1px solid #d8d8d8;background:#fafafa;padding:9px 10px;font-size:11px;line-height:1.6}
.bubble.user{align-self:flex-end;background:#f0f0f0}
.bubble.bot{align-self:flex-start}
.cite{border:1px dashed #bbb;background:#fafafa;padding:7px 8px;font-size:10px;color:#666}
.chip{display:inline-block;border:1px solid #ccc;background:#fff;padding:4px 7px;font-size:10px;color:#555;margin:2px 2px 0 0}
.empty{border:1px dashed #bbb;background:#fafafa;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;padding:22px;text-align:center;color:#666;font-size:11px}
.center{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:10px}
.logo-wire{width:66px;height:66px;border:1px dashed #999;background:#f5f5f5;display:flex;align-items:center;justify-content:center;font-size:10px;color:#777}
.admin{width:1440px;height:900px;display:grid;grid-template-columns:210px 1fr;grid-template-rows:52px 1fr;border:1px solid #cfcfcf;background:#fff;overflow:hidden}
.admin .top{grid-column:1/3;display:flex;align-items:center;gap:14px;padding:0 18px;border-bottom:1px solid #ddd;font-size:12px}
.admin .side{grid-row:2;border-right:1px solid #ddd;background:#fafafa;padding:12px 10px;display:flex;flex-direction:column;gap:3px}
.admin .side .s{padding:9px 10px;font-size:12px;color:#555;border:1px solid transparent}
.admin .side .s.active{background:#fff;border-color:#ddd;font-weight:700;color:#111}
.admin .main{grid-row:2;padding:16px 18px;display:flex;flex-direction:column;gap:12px;overflow:hidden;min-height:0}
.page-head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.page-head h2{font-size:16px;margin:0}
.row{display:flex;gap:8px;align-items:center}
.between{display:flex;align-items:center;justify-content:space-between;gap:10px}
.grow{flex:1}
.col{display:flex;flex-direction:column;gap:8px}
.filter{border:1px solid #ddd;background:#fafafa;padding:8px;display:flex;gap:6px;flex-wrap:wrap}
.filter .input{min-width:120px;flex:1}
.drawer{position:absolute;right:0;top:0;bottom:0;width:380px;background:#fff;border-left:1px solid #bbb;padding:14px;display:flex;flex-direction:column;gap:10px}
.overlay{position:absolute;inset:0;background:#f2f2f2cc}
.admin-main-wrap{position:relative;flex:1;min-height:0;display:flex;flex-direction:column;gap:12px}
.login-page{display:flex;align-items:center;justify-content:center;background:#fafafa;grid-template-columns:1fr;grid-template-rows:1fr}
.login-card{width:360px;border:1px solid #ccc;background:#fff;padding:26px;display:flex;flex-direction:column;gap:12px}
.login-card h2{margin:0;font-size:18px;text-align:center}
.login-card p{margin:0;text-align:center}
.pager{display:flex;justify-content:flex-end;gap:4px;align-items:center;font-size:10px;color:#666}
.pager span{border:1px solid #ccc;padding:3px 6px;background:#fff}
.note{border-left:3px solid #bbb;padding:6px 8px;background:#fafafa;font-size:10px;color:#666}
"""


GALLERY_CSS = r"""
html,body{margin:0;background:#f2f2f2;color:#222}
body{font:13px/1.5 "Microsoft YaHei","PingFang SC",Arial,sans-serif}
.wf-wrap{max-width:1500px;margin:0 auto;padding:28px}
.wf-head{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;border-bottom:1px solid #d0d0d0;padding-bottom:14px}
.wf-head h1{font-size:22px;margin:0 0 4px}
.wf-head p{margin:0;color:#666;font-size:12px}
.wf-nav{display:flex;gap:8px;flex-wrap:wrap}
.wf-nav a{border:1px solid #bbb;background:#fff;color:#333;text-decoration:none;padding:7px 10px;font-size:12px}
.wf-section{margin-top:26px}
.wf-section h2{font-size:15px;margin:0 0 10px;color:#444}
.wf-grid{display:grid;gap:16px}
.wf-grid.mobile{grid-template-columns:repeat(auto-fill,minmax(200px,1fr))}
.wf-grid.admin{grid-template-columns:repeat(auto-fill,minmax(460px,1fr))}
.wf-card{border:1px solid #d0d0d0;background:#fff;padding:12px;display:flex;flex-direction:column;gap:8px;min-width:0}
.wf-card-head{display:flex;align-items:center;gap:8px}
.wf-id{font:11px/1 ui-monospace,Consolas,monospace;background:#eee;border:1px solid #d5d5d5;padding:4px 6px;color:#555}
.wf-title{font-weight:700;font-size:13px;flex:1}
.wf-pill{font-size:9px;border:1px solid #ccc;background:#fafafa;padding:1px 5px;color:#666}
.wf-purpose{font-size:11px;color:#666;margin:0;min-height:32px}
.wf-preview{border:1px solid #ddd;overflow:hidden;background:#fff;align-self:center;flex:none}
.wf-scaled{transform-origin:top left}
.wf-open{font-size:11px;color:#333;text-decoration:none;border-top:1px solid #eee;padding-top:7px;margin-top:auto}
.wf-open:hover{text-decoration:underline}
.wf-note{font-size:11px;color:#777;margin:8px 0 0}
@media(max-width:700px){.wf-wrap{padding:14px}.wf-head{display:block}.wf-nav{margin-top:10px}.wf-grid.admin{grid-template-columns:1fr}}
"""


def build_gallery() -> None:
    modules: list[str] = []
    for meta in META:
        if meta["module"] not in modules:
            modules.append(meta["module"])
    sections = []
    for module in modules:
        items = [m for m in META if m["module"] == module]
        mobile = items[0]["viewport"]["width"] < 600
        kind = "mobile" if mobile else "admin"
        cards = []
        for meta in items:
            vw = meta["viewport"]["width"]
            vh = meta["viewport"]["height"]
            scale = 0.44 if mobile else 0.29
            width = round(vw * scale)
            height = round(vh * scale)
            cards.append(
                f'<article class="wf-card">'
                f'<div class="wf-card-head"><span class="wf-id">{esc(meta["id"])}</span>'
                f'<span class="wf-title">{esc(meta["title"])}</span>'
                f'<span class="wf-pill">{esc(meta["priority"])}</span></div>'
                f'<p class="wf-purpose">{esc(meta["purpose"])}</p>'
                f'<div class="wf-preview" style="width:{width}px;height:{height}px">'
                f'<div class="wf-scaled" style="width:{vw}px;height:{vh}px;transform:scale({scale})">'
                f'{FRAGMENTS[meta["id"]]}</div></div>'
                f'<a class="wf-open" href="page-map.html#{meta["id"]}">在结构地图中查看 →</a>'
                f'</article>'
            )
        sections.append(
            f'<section class="wf-section"><h2>{esc(module)}</h2>'
            f'<div class="wf-grid {kind}">{"".join(cards)}</div></section>'
        )
    html = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>i揭东 · 低保真页面线框</title><style>{CSS}{GALLERY_CSS}</style></head><body>'
        '<div class="wf-wrap"><header class="wf-head"><div><h1>i揭东 · 低保真页面线框</h1>'
        '<p>灰度、无品牌风格；只表达结构、入口与交互。P1 页面为占位线框。</p></div>'
        '<nav class="wf-nav"><a href="page-map.html">打开页面结构地图</a>'
        '<a href="../05-page-structure.md">页面结构说明</a>'
        '<a href="README.md">本目录说明</a></nav></header>'
        + "".join(sections) +
        '<p class="wf-note">提示：点击每张卡片底部“在结构地图中查看”可跳到对应页面详情；地图支持缩放/搜索/导出 PNG。</p>'
        '</div></body></html>'
    )
    (ROOT / "wireframes.html").write_text(html, encoding="utf-8")


def esc(value: str) -> str:
    return (value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def status() -> str:
    return '<div class="status"><span>9:41</span><span>●●●</span></div>'


def bottom(active: str = "") -> str:
    items = [("首页", "MP01"), ("区域", "MP02"), ("问答", "MP05"), ("我的", "MP08")]
    out = []
    for label, _ in items:
        cls = "active" if label == active else ""
        out.append(f'<span class="{cls}"><i></i>{label}</span>')
    return '<div class="bottom">' + "".join(out) + "</div>"


def phone(title: str, body: str, active: str = "", back: bool = False, nav: bool = True, bottom_bar: bool = True) -> str:
    nav_html = ""
    if nav:
        back_html = '<span class="back">←</span>' if back else ""
        nav_html = f'<div class="nav">{back_html}<span>{esc(title)}</span><span class="grow"></span><span class="tiny">⋯</span></div>'
    bottom_html = bottom(active) if bottom_bar else ""
    return f'<div class="phone">{status()}{nav_html}<div class="content">{body}</div>{bottom_html}</div>'


def admin(title: str, active: str, body: str) -> str:
    items = [("总览", "AD02"), ("数据", "AD03"), ("导入", "AD05"), ("审计", "AD07"), ("用户", "AD08"), ("问答", "AD09")]
    side = "".join(f'<div class="s {"active" if label == active else ""}">{label}</div>' for label, _ in items)
    return f'''<div class="admin">
  <div class="top"><b>i揭东 · 管理后台</b><span class="tiny">演示环境</span><span class="grow"></span><span class="tiny">admin</span><span class="tiny">退出</span></div>
  <aside class="side">{side}</aside>
  <main class="main"><div class="page-head"><h2>{esc(title)}</h2><span class="tiny">2025 年 · 演示数据</span></div>{body}</main>
</div>'''


def metric(label: str, value: str = "—") -> str:
    return f'<div class="metric"><span>{esc(label)}</span><b>{esc(value)}</b></div>'


def table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in rows)
    return f'<table class="table"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


def chart(labels=("A", "B", "C", "D", "E", "F")) -> str:
    bars = "".join(f'<div class="bar">{esc(l)}</div>' for l in labels)
    return f'<div class="chart">{bars}</div>'


FRAGMENTS: dict[str, str] = {}
META: list[dict] = []


def add(sid: str, title: str, module: str, priority: str, entry: str, purpose: str,
        layout: list[str], rules: list[str], reads: list[str], writes: list[str],
        viewport: dict, map_box: dict, html: str, state: str = "default") -> None:
    FRAGMENTS[sid] = html
    META.append({
        "id": sid, "module": module, "title": title, "kind": "page", "state": state,
        "entry": entry, "purpose": purpose,
        "evidence": {"level": "proposed", "anchor": "docs/product/05-page-structure.md"},
        "preconditions": [], "reads": reads, "writes": writes,
        "notes": ["低保真结构线框，不代表最终视觉。"],
        "annotation": {"layout": layout, "rules": rules},
        "capture": f"screens/{sid}.png", "view": f"screens/{sid}.html",
        "viewport": viewport, "map": map_box, "priority": priority,
    })


# ---------------- Mobile screens ----------------

add(
    "MP00", "启动/登录", "小程序 · 入口", "P0", "小程序启动/粤政易工作台（后期）",
    "完成登录或进入帮助；不登录也能看帮助/说明。",
    ["品牌占位区居中，下方说明与登录按钮；无底部导航。", "登录按钮是全宽主操作；帮助入口是弱操作。"],
    ["未登录只能看帮助；登录成功后才进入首页。", "不收集无关个人信息。"],
    ["user", "token"], ["login_audit"],
    {"width": 375, "height": 812}, {"x": 0, "y": 0, "w": 375, "h": 812},
    f'''<div class="phone">{status()}<div class="content" style="justify-content:center;align-items:center;text-align:center">
      <div class="logo-wire">LOGO</div>
      <h1 style="margin:6px 0 0;font-size:22px">i揭东</h1>
      <p class="muted" style="margin:0">公职人员数据门户</p>
      <div class="wire" style="height:42px;width:100%">微信登录（测试号）</div>
      <p class="tiny" style="margin:2px 0 0">登录即表示同意使用说明 · 无权限？查看帮助</p>
    </div></div>''',
)

add(
    "MP01", "首页", "小程序 · 浏览", "P0", "登录成功/底部“首页”",
    "一眼看到揭东区核心指标，快速进入镇街或 AI 问答。",
    ["顶部标题/年份；4 个指标卡 2×2；镇街入口列表；AI 提问框；底部 4 项导航。", "内容区纵向滚动；指标卡与列表不固定。"],
    ["无数据时显示“数据准备中”，不显示 0。", "首页到指标详情 ≤3 次点击。"],
    ["dashboard.overview", "regions"], [],
    {"width": 375, "height": 812}, {"x": 0, "y": 1100, "w": 375, "h": 812},
    phone("i揭东 · 2025", f'''
      <div class="grid2">{metric("区域面积")}{metric("常住人口")}{metric("地区生产总值")}{metric("镇街数量", "15")}</div>
      <div class="section-title">镇街入口 <span class="tiny">查看全部</span></div>
      <div class="list"><div class="item"><span>曲溪街道</span><span class="tiny">查看 ›</span></div><div class="item"><span>云路镇</span><span class="tiny">查看 ›</span></div><div class="item"><span>玉湖镇</span><span class="tiny">查看 ›</span></div></div>
      <div class="ai-entry" style="border:1px solid #ccc;background:#fafafa;padding:9px;display:flex;justify-content:space-between;align-items:center;gap:8px"><span class="tiny">问一句：哪个镇 GDP 最高？</span><span class="btn">提问</span></div>
    ''', active="首页"),
)

add(
    "MP02", "区域列表", "小程序 · 浏览", "P0", "首页“镇街”/底部“区域”",
    "按区/镇街/村居浏览与搜索区域。",
    ["顶部返回/标题；层级 tabs；搜索框；列表；底部导航。", "列表区域独立滚动；底部导航固定。"],
    ["经开区/生态城没有村居时，村居入口隐藏或提示“无村居”。", "搜索无结果时显示关键词与清空入口。"],
    ["regions"], [],
    {"width": 375, "height": 812}, {"x": 500, "y": 1100, "w": 375, "h": 812},
    phone("区域", f'''
      <div class="tabs"><span class="tab active">镇街</span><span class="tab">村居</span><span class="tab">区</span></div>
      <div class="input">搜索区域名称</div>
      <div class="list"><div class="item"><span>曲溪街道</span><span class="tiny">21 个村居 ›</span></div><div class="item"><span>云路镇</span><span class="tiny">21 个村居 ›</span></div><div class="item"><span>玉滘镇</span><span class="tiny">11 个村居 ›</span></div><div class="item"><span>玉湖镇</span><span class="tiny">21 个村居 ›</span></div><div class="item"><span>新亨镇</span><span class="tiny">14 个村居 ›</span></div></div>
    ''', active="区域", back=True),
)

add(
    "MP03", "区域详情", "小程序 · 浏览", "P0", "区域列表/首页",
    "看区域简介、特色与适用指标。",
    ["顶部返回/区域名；简介与特色文本块；指标卡列表；底部导航。", "文本块内容自适应；指标列表可滚动。"],
    ["只显示该区域适用指标；无值显示“暂无数据”。", "文本超长时截断并提示，不破坏布局。"],
    ["region", "region_intro", "region_feature", "data_values"], [],
    {"width": 375, "height": 812}, {"x": 1000, "y": 1100, "w": 375, "h": 812},
    phone("曲溪街道", f'''
      <div class="wire" style="height:66px;align-items:flex-start;justify-content:flex-start">地区简介（文本占位，≤150 字）</div>
      <div class="wire" style="height:56px;align-items:flex-start;justify-content:flex-start">地区特色（文本占位，≤300 字）</div>
      <div class="section-title">适用指标</div>
      <div class="grid2">{metric("区域面积")}{metric("常住人口")}{metric("耕地面积")}{metric("林地面积")}</div>
      <div class="btn block">查看全部指标</div>
    ''', active="区域", back=True),
)

add(
    "MP04", "指标详情", "小程序 · 浏览", "P0", "区域详情/首页指标卡/AI 引用",
    "看指标值、单位、年份、来源与图表。",
    ["顶部返回/指标名；值卡片；图表区；表格；对比按钮；底部导航。", "图表与表格可切换；内容区滚动。"],
    ["空值显示“暂无数据”，不画 0。", "图表失败时降级为表格；来源必须显示。"],
    ["indicator", "data_values", "source"], [],
    {"width": 375, "height": 812}, {"x": 1500, "y": 1100, "w": 375, "h": 812},
    phone("常住人口", f'''
      <div class="card"><div class="between"><span class="tiny">2025 年 · 单位：人</span><span class="pill">来源：导入</span></div><b style="font-size:28px">—</b><span class="tiny">演示数据 / 待导入</span></div>
      {chart(("曲溪", "云路", "玉滘", "玉湖", "新亨", "锡场"))}
      <table class="table"><thead><tr><th>区域</th><th>值</th></tr></thead><tbody><tr><td>曲溪街道</td><td>—</td></tr><tr><td>云路镇</td><td>—</td></tr><tr><td>玉滘镇</td><td>—</td></tr></tbody></table>
      <div class="btn block">对比其他区域</div>
    ''', active="区域", back=True),
)

add(
    "MP05", "AI 问答（空）", "小程序 · AI", "P0", "首页 AI 入口/底部“问答”",
    "输入问题或从示例开始。",
    ["顶部标题；空状态说明 + 示例 chips；底部输入条；底部导航。", "输入条固定在内容底部，不遮挡最后一条消息。"],
    ["提交后先显示 thinking/tool_calling，不立即清空问题。", "问题为空时禁用发送。"],
    ["session(optional)"], [],
    {"width": 375, "height": 812}, {"x": 0, "y": 2200, "w": 375, "h": 812},
    phone("AI 问答", f'''
      <div class="empty" style="flex:1"><div class="logo-wire" style="width:48px;height:48px">AI</div><b>问我揭东数据</b><span class="tiny">例如：2025 年哪个镇 GDP 最高？</span><div><span class="chip">常住人口</span><span class="chip">镇街排名</span><span class="chip">区域对比</span></div></div>
      <div class="input-bar"><div class="input">输入问题…</div><div class="btn primary">发送</div></div>
    ''', active="问答"),
)

add(
    "MP06", "AI 问答（答案）", "小程序 · AI", "P0", "MP05 提交后/会话列表",
    "看答案、图表、引用并追问。",
    ["消息流：用户气泡 → 助手气泡（结论/图表/引用/追问）；底部输入条。", "消息区独立滚动；输入条固定。"],
    ["答案必须带引用；无数据明确说明。", "图表只渲染 ChartSpec；失败降级表格。"],
    ["answer_markdown", "chart_spec", "citations", "follow_up_questions"], ["chat_messages"],
    {"width": 375, "height": 812}, {"x": 500, "y": 2200, "w": 375, "h": 812},
    phone("AI 问答", f'''
      <div class="bubble user">2025 年揭东区各镇街地区生产总值排名前 5 是哪些？</div>
      <div class="bubble bot"><b>结论</b><br>按 2025 年地区生产总值排序，前 5 为……（演示）。<br><span class="tiny">数据：演示数据</span></div>
      {chart(("经开区", "生态城", "曲溪", "云路", "玉湖"))}
      <div class="cite">引用：地区生产总值 · 2025 · 镇街 · data_values</div>
      <div><span class="chip">换成常住人口</span><span class="chip">看完整排名</span></div>
      <div class="input-bar"><div class="input">继续问…</div><div class="btn primary">发送</div></div>
    ''', active="问答"),
)

add(
    "MP07", "会话列表", "小程序 · AI", "P1", "首页“历史”/底部“问答”",
    "查看历史问答。",
    ["顶部返回/标题；新建对话按钮；会话列表。", "列表可滚动。"],
    ["空列表显示“还没有问答”。", "删除/重命名 P1。"],
    ["chat_sessions"], [],
    {"width": 375, "height": 812}, {"x": 1000, "y": 2200, "w": 375, "h": 812},
    phone("会话", f'''
      <div class="btn block">＋ 新建对话</div>
      <div class="list"><div class="item"><span>镇街 GDP 排名</span><span class="tiny">今天</span></div><div class="item"><span>曲溪街道人口</span><span class="tiny">昨天</span></div><div class="item"><span>玉湖镇介绍</span><span class="tiny">昨天</span></div></div>
    ''', active="问答", back=True),
)

add(
    "MP08", "无权限/帮助", "小程序 · 入口", "P0", "无权限跳转/“我的”帮助",
    "解释无权限、提供申请/联系入口与应用说明。",
    ["状态占位 + 标题/说明 + 联系/申请按钮 + 应用简介/指南/维护电话。", "内容可滚动；返回入口清晰。"],
    ["无权限不泄露数据内容。", "维护中显示维护时间/联系人。"],
    ["app_config"], [],
    {"width": 375, "height": 812}, {"x": 500, "y": 0, "w": 375, "h": 812},
    phone("帮助", f'''
      <div class="empty"><div class="logo-wire" style="width:48px;height:48px">!</div><b>暂无访问权限</b><span class="tiny">请联系本单位管理员开通，或从粤政易工作台进入。</span><div class="btn">联系管理员</div></div>
      <div class="card"><div class="card-title">应用简介</div><div class="tiny">i揭东用于揭东区数据查询、图表与智能问答。</div></div>
      <div class="card"><div class="card-title">使用指南</div><div class="tiny">首页 → 区域 → 指标 → 图表；问答可直接输入问题。</div></div>
      <div class="tiny">维护电话：XXXX-XXXXXXX · 技术支持：XXX</div>
    ''', active="我的", back=True),
)

# ---------------- Admin screens ----------------

add(
    "AD01", "登录", "后台 · 登录", "P0", "后台地址",
    "管理员登录后台。",
    ["居中登录卡：账号/密码/登录；错误提示；无侧栏。", "登录卡宽度固定，页面居中。"],
    ["密码错误不提示账号是否存在。", "连续失败限流。"],
    ["user", "token"], ["login_audit"],
    {"width": 1440, "height": 900}, {"x": 0, "y": 3400, "w": 1440, "h": 900},
    f'''<div class="admin login-page"><div class="login-card"><div class="logo-wire" style="margin:0 auto">LOGO</div><h2>i揭东 · 管理后台</h2><p class="muted">公职人员数据门户</p><div class="input">用户名</div><div class="input">密码</div><div class="btn primary block">登录</div><p class="tiny">演示环境 · 请联系管理员开通账号</p></div></div>''',
)

add(
    "AD02", "总览", "后台 · 数据", "P0", "登录成功/侧栏“总览”",
    "看数据覆盖率、最近导入与问答量。",
    ["顶栏 + 左侧导航 + 4 个统计卡 + 覆盖率表 + 最近导入 + 问答量。", "主区纵向滚动；统计卡不固定。"],
    ["数字与数据库一致；空数据显示 0 或“暂无”。", "导入成功后统计刷新。"],
    ["dashboard.overview", "import_jobs", "chat_stats"], [],
    {"width": 1440, "height": 900}, {"x": 0, "y": 4550, "w": 1440, "h": 900},
    admin("总览", "总览", f'''
      <div class="grid4">{metric("区域数", "227")}{metric("指标数", "15")}{metric("数据行", "1608")}{metric("本月导入", "0")}</div>
      <div class="card"><div class="card-title">数据覆盖率 <span class="tiny">区 / 镇街 / 村居</span></div>{table(["层级", "区域数", "应有数据", "已填", "覆盖率"], [["揭东区", "1", "15", "—", "—"], ["镇街", "15", "116", "—", "—"], ["村居", "211", "1477", "—", "—"]])}</div>
      <div class="row" style="align-items:stretch"><div class="card grow"><div class="card-title">最近导入</div>{table(["文件", "状态", "时间"], [["模板.xlsx", "成功", "今天"], ["补录.csv", "部分", "昨天"]])}</div><div class="card" style="width:380px"><div class="card-title">问答量</div>{chart(("周一", "周二", "周三", "周四", "周五"))}</div></div>
    '''),
)

add(
    "AD03", "数据列表", "后台 · 数据", "P0", "总览/侧栏“数据”",
    "筛选、查看、编辑数据值。",
    ["顶栏 + 侧栏 + 筛选行 + 表格 + 分页。", "表格区域可滚动；筛选行不固定。"],
    ["筛选组合为空显示“无匹配数据”。", "编辑保存后回到列表并刷新。"],
    ["data_values", "regions", "indicators"], [],
    {"width": 1440, "height": 900}, {"x": 1800, "y": 4550, "w": 1440, "h": 900},
    admin("数据管理", "数据", f'''
      <div class="filter"><div class="input">区域：全部</div><div class="input">指标：全部</div><div class="input">年份：2025</div><div class="btn">查询</div><div class="btn">重置</div><div class="grow"></div><div class="btn primary">导入</div></div>
      {table(["区域", "指标", "年份", "值", "单位", "状态", "操作"], [["曲溪街道", "常住人口", "2025", "—", "人", "已发布", "编辑"], ["云路镇", "常住人口", "2025", "—", "人", "已发布", "编辑"], ["玉滘镇", "区域面积", "2025", "—", "平方公里", "已发布", "编辑"], ["玉湖镇", "耕地面积", "2025", "—", "亩", "已发布", "编辑"], ["经开区", "地区生产总值", "2025", "—", "亿元", "已发布", "编辑"]])}
      <div class="pager"><span>‹</span><span>1</span><span>2</span><span>3</span><span>›</span><span class="tiny">共 1608 条</span></div>
    '''),
)

add(
    "AD04", "数据编辑（抽屉）", "后台 · 数据", "P0", "AD03 点“编辑”",
    "修订单条数据并写入审计。",
    ["AD03 列表 + 右侧抽屉；抽屉内字段只读 + 值输入 + 保存/取消。", "抽屉覆盖右侧，列表仍可见；抽屉内部可滚动。"],
    ["保存前校验类型/单位；失败留在抽屉。", "保存后写 audit_logs（before/after）。"],
    ["data_value"], ["data_values", "audit_logs"],
    {"width": 1440, "height": 900}, {"x": 3600, "y": 4550, "w": 1440, "h": 900},
    admin("数据管理", "数据", f'''
      <div class="admin-main-wrap">
        <div class="filter"><div class="input">区域：曲溪街道</div><div class="input">指标：常住人口</div><div class="input">年份：2025</div><div class="btn">查询</div></div>
        {table(["区域", "指标", "年份", "值", "单位", "状态"], [["曲溪街道", "常住人口", "2025", "—", "人", "已发布"], ["云路镇", "常住人口", "2025", "—", "人", "已发布"]])}
        <div class="overlay"></div>
        <aside class="drawer"><div class="between"><b>编辑数据值</b><span class="tiny">×</span></div><div class="tiny">区域</div><div class="input">曲溪街道（只读）</div><div class="tiny">指标</div><div class="input">常住人口（只读）</div><div class="tiny">年份</div><div class="input">2025（只读）</div><div class="tiny">值</div><div class="input">请输入数值</div><div class="note">单位：人；空值表示无数据，不写 0。</div><div class="row"><div class="btn primary grow">保存</div><div class="btn grow">取消</div></div><div class="tiny">保存后写入审计日志（before/after）。</div></aside>
      </div>
    '''),
)

add(
    "AD05", "导入", "后台 · 数据", "P0", "总览/AD03/侧栏“导入”",
    "上传 Excel、校验、查看错误报告。",
    ["上传区 + 模板下载 + 模式选择 + 开始导入 + 结果统计 + 错误表。", "上传区高度固定；错误表可滚动。"],
    ["默认 atomic：有错误整批不写。", "错误报告含行/列/错误码/建议。"],
    ["file", "mode"], ["import_jobs", "data_values", "audit_logs"],
    {"width": 1440, "height": 900}, {"x": 0, "y": 5650, "w": 1440, "h": 900},
    admin("导入", "导入", f'''
      <div class="row" style="align-items:stretch"><div class="card grow"><div class="card-title">上传文件</div><div class="wire" style="height:120px">拖拽 .xls/.xlsx 到这里，或点击选择</div><div class="row"><div class="btn">下载模板</div><span class="tiny">≤10MB · ≤5000 行</span></div></div><div class="card" style="width:380px"><div class="card-title">导入模式</div><div class="input">● 整批校验（atomic）</div><div class="input">○ 允许部分写入（partial）</div><div class="btn primary block">开始导入</div></div></div>
      <div class="card"><div class="card-title">校验结果 <span class="pill">演示</span></div><div class="grid4">{metric("总行数", "1608")}{metric("成功", "—")}{metric("失败", "—")}{metric("警告", "—")}</div>{table(["行", "区域", "指标", "列", "错误", "建议"], [["18", "玉窖镇-饶美村", "区域面积", "单位", "UNIT_MISMATCH", "检查模板列"], ["22", "玉滘镇", "耕地面积", "值", "VALUE_TYPE_INVALID", "填写数字"]])}</div>
    '''),
)

add(
    "AD06", "导入记录", "后台 · 数据", "P0", "AD05/总览",
    "查看历史导入与错误报告。",
    ["顶部标题 + 筛选 + 表格（文件/时间/操作者/状态/成功/失败/错误下载）。", "表格可滚动。"],
    ["状态与统计准确；错误报告可下载。", "失败/部分成功可回到导入重试。"],
    ["import_jobs"], [],
    {"width": 1440, "height": 900}, {"x": 1800, "y": 5650, "w": 1440, "h": 900},
    admin("导入记录", "导入", f'''
      <div class="filter"><div class="input">状态：全部</div><div class="input">时间：本月</div><div class="btn">查询</div></div>
      {table(["文件", "来源", "时间", "操作者", "状态", "成功/失败", "错误报告"], [["模板_2025.xlsx", "Excel", "今天 10:20", "admin", "成功", "1608 / 0", "下载"], ["补录_曲溪.xlsx", "Excel", "昨天 16:05", "admin", "部分", "120 / 3", "下载"]])}
    '''),
)

add(
    "AD07", "审计日志", "后台 · 数据", "P0", "总览/侧栏“审计”",
    "追查谁在什么时候改了什么。",
    ["筛选（用户/动作/资源/时间）+ 表格（时间/用户/动作/资源/详情）。", "表格可滚动。"],
    ["写操作都有记录；敏感字段脱敏。", "只读，不可编辑/删除。"],
    ["audit_logs"], [],
    {"width": 1440, "height": 900}, {"x": 3600, "y": 5650, "w": 1440, "h": 900},
    admin("审计日志", "审计", f'''
      <div class="filter"><div class="input">用户：全部</div><div class="input">动作：全部</div><div class="input">资源：全部</div><div class="input">时间：本月</div><div class="btn">查询</div></div>
      {table(["时间", "用户", "动作", "资源", "详情"], [["今天 10:21", "admin", "import", "import_jobs#12", "成功 1608 行"], ["今天 10:25", "admin", "update", "data_values#88", "before/after"], ["昨天 16:06", "admin", "login", "user#1", "成功"]])}
    '''),
)

add(
    "AD08", "用户与权限", "后台 · 管理", "P1", "总览/侧栏“用户”",
    "管理 admin/editor/viewer。",
    ["用户表（用户名/显示名/角色/状态/最后登录）+ 新增/编辑。", "表格可滚动。"],
    ["不能删除最后一个 admin。", "禁用用户不能登录。"],
    ["users"], ["users", "audit_logs"],
    {"width": 1440, "height": 900}, {"x": 0, "y": 6750, "w": 1440, "h": 900},
    admin("用户与权限", "用户", f'''
      <div class="between"><span class="tiny">角色：admin / editor / viewer</span><div class="btn primary">新增用户</div></div>
      {table(["用户名", "显示名", "角色", "状态", "最后登录", "操作"], [["admin", "管理员", "admin", "启用", "今天", "编辑"], ["editor01", "数据员", "editor", "启用", "昨天", "编辑"], ["viewer01", "查看员", "viewer", "禁用", "—", "编辑"]])}
    '''),
)

add(
    "AD09", "问答记录", "后台 · 管理", "P1", "总览/侧栏“问答”",
    "查看问题、答案摘要、工具调用与反馈。",
    ["筛选 + 表格（时间/用户/问题/答案摘要/工具/耗时/反馈）。", "表格可滚动。"],
    ["不展示密钥/系统提示。", "可标记问题（P1）。"],
    ["chat_messages"], ["feedback"],
    {"width": 1440, "height": 900}, {"x": 1800, "y": 6750, "w": 1440, "h": 900},
    admin("问答记录", "问答", f'''
      <div class="filter"><div class="input">用户：全部</div><div class="input">时间：本月</div><div class="input">是否有反馈：全部</div><div class="btn">查询</div></div>
      {table(["时间", "用户", "问题", "答案摘要", "工具", "耗时", "反馈"], [["今天 10:30", "viewer01", "哪个镇 GDP 最高？", "前 5 名…", "rank_regions", "3.2s", "—"], ["昨天 15:10", "admin", "曲溪街道人口", "常住人口…", "get_indicator_values", "2.1s", "有帮助"]])}
    '''),
)

TRANSITIONS = [
    # Mobile
    ("TR_MP00_01", "MP00", "MP01", "点击“微信登录/测试号”", ["user", "token"], ["login_audit"], "登录成功，进入首页；携带 user/token", "进入首页", "登录失败留在登录页", "重试/切换测试号"),
    ("TR_MP00_02", "MP00", "MP08", "点击“无权限？查看帮助”", [], [], "打开帮助/无权限页", "打开帮助", "—", "返回登录"),
    ("TR_MP01_02", "MP01", "MP02", "点击镇街/区域入口", ["level=town"], [], "切换区域列表；携带 level=town", "打开区域列表", "加载失败可重试", "返回首页"),
    ("TR_MP01_04", "MP01", "MP04", "点击核心指标卡", ["region_id", "indicator_id", "period"], [], "切换指标详情；携带 region_id/indicator_id/period", "打开指标详情", "无数据展示空状态", "返回首页"),
    ("TR_MP01_05", "MP01", "MP05", "点击 AI 提问框", [], [], "打开 AI 问答；可带 prompt", "打开问答", "—", "返回首页"),
    ("TR_MP01_07", "MP01", "MP07", "点击“历史”", [], [], "打开会话列表", "打开会话", "空列表提示", "返回首页"),
    ("TR_MP02_03", "MP02", "MP03", "选择区域行", ["region_id"], [], "切换区域详情；携带 region_id", "打开区域详情", "区域不存在提示", "返回列表"),
    ("TR_MP03_04", "MP03", "MP04", "点击指标卡", ["region_id", "indicator_id"], [], "切换指标详情；携带 region_id/indicator_id", "打开指标详情", "无数据展示空状态", "返回区域详情"),
    ("TR_MP04_03", "MP04", "MP03", "点击返回", ["region_id"], [], "返回区域详情", "返回", "—", "—"),
    ("TR_MP05_06", "MP05", "MP06", "提交问题", ["question", "session_id"], ["chat_sessions", "chat_messages", "audit_logs"], "调用 /ai/chat；返回 answer/chart_spec/citations", "显示 thinking→答案", "超时/额度/无效输出提示", "重试/改写问题"),
    ("TR_MP06_05", "MP06", "MP05", "点击追问/新问题", ["session_id"], [], "回到输入态，保留会话上下文", "回到输入", "—", "—"),
    ("TR_MP06_04", "MP06", "MP04", "点击引用指标", ["region_id", "indicator_id", "period"], [], "打开引用指标详情", "打开指标", "无数据提示", "返回问答"),
    ("TR_MP07_06", "MP07", "MP06", "点击会话", ["session_id"], [], "打开会话消息", "打开会话", "加载失败重试", "返回列表"),
    ("TR_MP08_00", "MP08", "MP00", "点击返回/重新登录", [], [], "回到登录页", "返回", "—", "—"),
    # Admin
    ("TR_AD01_02", "AD01", "AD02", "点击登录", ["user", "token"], ["login_audit"], "登录成功，进入总览", "进入总览", "失败提示，不泄露账号存在性", "重试"),
    ("TR_AD02_03", "AD02", "AD03", "点击侧栏“数据”", [], [], "打开数据列表", "切换页面", "—", "—"),
    ("TR_AD02_05", "AD02", "AD05", "点击侧栏“导入”/最近导入", [], [], "打开导入页", "切换页面", "—", "—"),
    ("TR_AD02_07", "AD02", "AD07", "点击侧栏“审计”", [], [], "打开审计日志", "切换页面", "—", "—"),
    ("TR_AD02_08", "AD02", "AD08", "点击侧栏“用户”", [], [], "打开用户/权限（P1）", "切换页面", "—", "—"),
    ("TR_AD02_09", "AD02", "AD09", "点击侧栏“问答”", [], [], "打开问答记录（P1）", "切换页面", "—", "—"),
    ("TR_AD03_04", "AD03", "AD04", "点击行“编辑”", ["data_value_id"], [], "打开右侧编辑抽屉；携带 data_value_id", "打开抽屉", "记录不存在提示", "关闭抽屉"),
    ("TR_AD04_03", "AD04", "AD03", "点击保存", ["data_value"], ["data_values", "audit_logs"], "保存成功，回到列表并刷新；写审计", "保存成功", "校验失败留在抽屉", "修正/取消"),
    ("TR_AD04_03C", "AD04", "AD03", "点击取消", [], [], "关闭抽屉，不写入", "关闭", "—", "重新打开"),
    ("TR_AD03_05", "AD03", "AD05", "点击“导入”", [], [], "打开导入页；可带筛选条件", "切换页面", "—", "—"),
    ("TR_AD05_06", "AD05", "AD06", "点击“查看记录”", [], [], "打开导入记录", "切换页面", "—", "—"),
    ("TR_AD06_05", "AD06", "AD05", "点击错误/重试", ["import_job_id"], [], "回到导入页，带 job 上下文", "回到导入", "—", "—"),
    ("TR_AD05_03", "AD05", "AD03", "导入成功后点击“查看数据”", [], [], "刷新数据列表", "刷新列表", "—", "—"),
    ("TR_AD05_MP01", "AD05", "MP01", "导入/发布成功", [], ["data_values"], "小程序首页读取最新数据（跨端数据更新）", "数据更新", "—", "重新导入"),
    ("TR_AD01_02R", "AD01", "AD02", "已登录直接进入", ["token"], [], "跳过登录进入总览", "进入总览", "token 失效回登录", "重新登录"),
]


def main() -> None:
    (SCREENS / "source.css").write_text(CSS, encoding="utf-8")
    for sid, html in FRAGMENTS.items():
        (SCREENS / f"{sid}.html").write_text(html, encoding="utf-8")

    # screenshots via Playwright/Chrome
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        print("Playwright not available:", exc)
        raise SystemExit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        for meta in META:
            page = browser.new_page(viewport=meta["viewport"], device_scale_factor=1)
            page.set_content(f"<style>{CSS}</style>{FRAGMENTS[meta['id']]}", wait_until="load")
            page.screenshot(path=str(SCREENS / f"{meta['id']}.png"), full_page=False)
            page.close()
        browser.close()

    model = {
        "schemaVersion": "1.1",
        "source": {"label": "低保真结构线框（设计稿，不是运行截图）", "runtime": "static-wireframe"},
        "viewport": {"width": 1440, "height": 1000},
        "screens": META,
        "transitions": [
            {
                "id": tid, "from": frm, "to": to, "trigger": trigger,
                "preconditions": [], "read": read, "write": write,
                "effect": effect, "feedback": feedback, "failure": failure,
                "recovery": recovery, "evidence": "proposed", "isReturn": "返回" in trigger or "取消" in trigger,
            }
            for (tid, frm, to, trigger, read, write, effect, feedback, failure, recovery) in TRANSITIONS
        ],
        "entities": [
            {"name": "Region", "fields": ["id", "code", "name", "level", "parent_id"]},
            {"name": "Indicator", "fields": ["id", "code", "name", "unit", "value_type", "applicable_levels"]},
            {"name": "DataValue", "fields": ["region_id", "indicator_id", "period_year", "value_number", "value_text", "source_id"]},
            {"name": "ImportJob", "fields": ["job_type", "filename", "status", "stats", "errors"]},
            {"name": "ChatMessage", "fields": ["session_id", "role", "content", "chart_spec", "citations"]},
            {"name": "AuditLog", "fields": ["user_id", "action", "resource", "detail"]},
        ],
        "dataFlows": [
            {"from": "AD05", "to": "MP01", "trigger": "导入/发布成功", "fields": ["data_values"], "note": "跨端数据更新"},
            {"from": "MP05", "to": "MP06", "trigger": "提交问题", "fields": ["question", "session_id"], "note": "答案/图表/引用返回"},
            {"from": "MP06", "to": "MP04", "trigger": "点击引用", "fields": ["region_id", "indicator_id", "period"], "note": "从答案追溯到指标"},
        ],
        "coverage": {
            "included": [m["id"] for m in META],
            "excluded": ["地图/大屏", "导出/多年趋势", "粤政易 SSO 页面", "公众版"],
            "note": "P1 页面以占位线框呈现，不表示已实现。",
        },
        "limitations": [
            "低保真结构线框，不含品牌色/视觉风格/高保真 UI。",
            "页面与接口为设计契约；后端尚未实现。",
            "数据值为演示占位，不代表真实统计。",
        ],
    }
    (ROOT / "ue-spec.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    build_gallery()
    print(f"wrote {len(META)} screens, {len(TRANSITIONS)} transitions, wireframes.html")
    print("next: python <frontend-to-ue>/scripts/render_map.py docs/product/ue --out docs/product/ue/page-map.html --title \"i揭东\"")


if __name__ == "__main__":
    main()
