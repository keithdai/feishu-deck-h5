---
name: pptx-exporter
description: |
  Export a feishu-deck-h5 deck to PPTX. Two SELF-CONTAINED modes (no ppt-master
  needed): snapshot (faithful image-per-slide, not editable) and native/hybrid
  (schema pages → editable vector shapes via the vendored svg_to_pptx; raw pages
  → snapshot). Use only after the deck is validated/delivered and the user wants
  a .pptx. Do not validate/fix/render/publish — it consumes a confirmed deck.json
  or index.html.
---

# pptx-exporter

把 feishu-deck-h5 deck 导出成 PPTX。**两种模式都自洽**——svg_to_pptx +
svg_finalize 已 vendor 进 `deck-json/`，**不需要安装 ppt-master**。

## 两种模式（先认清取舍，再选）

| | snapshot（默认） | native/hybrid（进阶） |
|---|---|---|
| 命令 | `html-to-pptx.py` | `deck-to-svg.py --pptx` |
| 源 | 一份确认的 `index.html` | `deck.json`（+ `index.html` 用于 raw 页截图） |
| schema 页（cover/3up/table…） | 图（不可编辑） | **原生矢量形状，可编辑** |
| raw 页（自由 HTML/iframe） | 图 | 图（snapshot 兜底） |
| 还原度 | 像素级 | schema 页贴近、raw 页忠实 |
| 何时用 | "发一份长得对的 .pptx" | "客户要拿去改字" |

## 模式 1 — snapshot（自洽，任何确认的 HTML）

```bash
python3 skills/feishu-deck-h5/assets/html-to-pptx.py <index.html | run-dir> [--out deck.pptx] [--pages 1,2,cover]
```
用 skill 自带的 `deck-json/shoot.py`（Playwright）逐页截 present 模式（已藏 chrome）→
python-pptx 拼成 PPTX。每页一张满版图，**文字不可编辑**。

## 模式 2 — native/hybrid（自洽，可编辑 schema 页）

```bash
python3 skills/feishu-deck-h5/deck-json/deck-to-svg.py <deck.json> <out_dir> [--html index.html] --pptx
# → <out_dir>/svg_output/*.svg（schema 原生 + raw 截图）→ <out_dir>/exports/*.pptx
```
- schema 布局（cover/agenda/section/content·3up·2col/table/quote/stats/end）→
  原生 SVG 矢量 → vendored `svg_to_pptx` → **可编辑形状/文本**（PowerPoint 里改字）。
- raw slide → `--html` 给了就调 shoot.py 截那一页嵌成图（保真）；没给就占位。
- 字体：CJK 栈写 `PingFang SC, Microsoft YaHei`（svg_to_pptx 的 EA_FONTS 认 →
  映射成 Microsoft YaHei 写进 `<a:ea>`）；别用方正兰亭黑打头（不在 EA_FONTS，会被误判成 latin）。
- 底图/logo：按页型用飞书官方 `lark-{cover,section,content}-bg.jpg` + 彩色 `lark-logo.png`。

## 职责边界

- **只导出**：消费已确认的 deck.json/index.html，产出 .pptx。
- **不校验/不修/不渲染 HTML/不发布**：质量在 deck 阶段就该到位。
- **raw 不可编辑是边界**：raw slide 没有结构可翻译成矢量，永远走 snapshot。
  要可编辑就改用 schema 布局（别用 raw）。

## 前置依赖

- `python-pptx`（`pip install python-pptx`）
- Playwright + chromium（snapshot 和 native 的 raw 截图都用）：
  `pip install playwright && python -m playwright install chromium`
- Python 3.9+（shoot.py / svg_to_pptx 都加了 `from __future__ import annotations`）。
- **不需要 ppt-master**——svg_to_pptx + svg_finalize 已 vendor 在 `deck-json/`。

## 已知限制（诚实写明）

- native 模式目前实现 8 个 schema 布局（cover/agenda/section/content·3up·2col/
  table/quote/stats/end）；flow/arch-stack/image-text/logo-wall/story-case 待补，
  未实现的会落占位（可临时用 snapshot 兜底）。
- SVG 是手算坐标（vs HTML 的 CSS 自动布局），视觉密度与 HTML 有差距；密集流式
  文字的换行是按字宽估算，不是真文本测量。
- demo iframe 页走 snapshot 时，shoot.py 默认拦外部 http → 可能空白；要截真 demo
  得给那几页加 `--allow-external`。

## 触发词

- "转 PPT / 导出 pptx / 要一份 ppt 文件"（默认 snapshot）→ 模式 1。
- "可编辑的 PPT / 原生 pptx / 能改字的 PPT"（要编辑性）→ 模式 2。
- 先复述取舍（snapshot 不可编辑 / native 的 raw 页仍不可编辑），得到确认再导。
