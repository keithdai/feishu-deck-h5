#!/usr/bin/env python3
"""deck-to-svg.py — SVG-format renderer for feishu-deck-h5 deck.json.

Sibling of render-deck.py: same deck.json + layout dispatch, emits per-page SVG
(native vector) instead of one HTML shell. SVG feeds ppt-master's finalize_svg +
svg_to_pptx → native EDITABLE PPTX. Uses feishu official bg assets (cover/section/
content) + color wordmark per page type — same visual identity as the HTML deck.

Implements schema layouts: cover, agenda, section, content/3up, content/2col,
table, quote, stats (row/hero), end. `raw` slides get a titled placeholder (raw
has no structure → those go through html-to-pptx snapshot in the hybrid flow).
"""
import argparse
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# make the vendored svg_to_pptx package (sibling in deck-json/) importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Font stacks MUST start with a font svg_to_pptx's parse_font_family classifies
# correctly: CJK fonts listed in its EA_FONTS (PingFang/YaHei) → written to <a:ea>
# and Windows-mapped. 方正兰亭黑 is NOT in EA_FONTS → it gets misclassified as a
# latin face and substitutes ugly. So lead CJK with PingFang SC (browser shows it
# on Mac) → PPTX ea = Microsoft YaHei (cross-platform clean CJK sans, closest to
# the 兰亭黑 brand font which isn't installed anyway).
CJK = 'PingFang SC, Microsoft YaHei, Arial, sans-serif'
LATIN = 'Arial, Helvetica Neue, sans-serif'
BG, SURF = '#04060F', '#071027'
PRI, CYAN, TEAL, PURP = '#3C7FFF', '#24C3FF', '#33D6C0', '#5C3FFB'
TXT, TXT2, TXT3 = '#FFFFFF', '#B8C2D6', '#7E89A8'
DIV = '#FFFFFF'
ACCENTS = [PRI, PURP, TEAL]

_ASSETS = Path(__file__).resolve().parent.parent / 'assets'


def _uri(name):
    p = _ASSETS / name
    if not p.exists():
        return None
    raw = p.read_bytes()
    mime = 'image/jpeg' if name.endswith('.jpg') else 'image/png'
    return f'data:{mime};base64,{base64.b64encode(raw).decode()}'


_BG = {k: _uri(f'lark-{k}-bg.jpg') for k in ('cover', 'section', 'content')}
_LOGO = _uri('lark-logo.png')


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def cw(ch, size):
    o = ord(ch)
    if o > 0x2E80:
        return size * 1.0
    if ch.isalnum():
        return size * 0.55
    return size * 0.4


def wrap(text, max_w, size):
    t = esc(text)
    lines, cur, w = [], '', 0.0
    for ch in t:
        c = cw(ch, size)
        if cur and w + c > max_w:
            lines.append(cur); cur, w = ch, c
        else:
            cur, w = cur + ch, w + c
    if cur:
        lines.append(cur)
    return lines


DEFS = ('<defs>'
        '<linearGradient id="kl" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#33D6C0"/><stop offset="0.5" stop-color="#3C7FFF"/>'
        '<stop offset="1" stop-color="#5C3FFB"/></linearGradient>'
        '<radialGradient id="glow" cx="50%" cy="50%" r="50%">'
        '<stop offset="0" stop-color="#3C7FFF" stop-opacity="0.20"/>'
        '<stop offset="1" stop-color="#3C7FFF" stop-opacity="0"/></radialGradient>'
        '</defs>')


def bg_layer(kind='content'):
    uri = _BG.get(kind)
    if uri:
        return (f'<image href="{uri}" x="0" y="0" width="1280" height="720" '
                f'preserveAspectRatio="xMidYMid slice"/>\n'
                f'<rect width="1280" height="720" fill="#04060F" opacity="0.55"/>\n')
    return f'<rect width="1280" height="720" fill="{BG}"/>\n'


def logo_img():
    return (f'<image href="{_LOGO}" x="1083" y="42" width="113" height="35" '
            f'preserveAspectRatio="xMidYMin meet"/>\n') if _LOGO else ''


def page(kind='content'):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">\n{DEFS}\n{bg_layer(kind)}'


def chrome(title):
    return (
        f'<ellipse cx="1100" cy="120" rx="360" ry="240" fill="url(#glow)"/>\n'
        f'<text x="64" y="86" fill="{TXT}" font-family="{CJK}" font-size="36" font-weight="700">{esc(title)}</text>\n'
        f'<rect x="64" y="104" width="96" height="5" rx="2.5" fill="url(#kl)"/>\n'
        f'{logo_img()}'
    )


def multiline(x, y, lines, size, lh, fill, family=CJK, weight='500', anchor='start'):
    out = ''
    a = f' text-anchor="{anchor}"' if anchor != 'start' else ''
    for i, ln in enumerate(lines):
        out += f'<text x="{x}" y="{y + i * lh}" fill="{fill}" font-family="{family}" font-size="{size}" font-weight="{weight}"{a}>{ln}</text>\n'
    return out


def render_cover(d):
    title = wrap(d.get('title', ''), 1100, 70)
    sub = d.get('subtitle', '')
    s = page('cover')
    s += f'<text x="80" y="120" fill="{TXT3}" font-family="{LATIN}" font-size="16" font-weight="600" letter-spacing="3">FEISHU · PRESALES</text>\n'
    s += f'<rect x="80" y="300" width="128" height="6" rx="3" fill="url(#kl)"/>\n'
    s += multiline(80, 400, title, 70, 84, TXT, CJK, '700')
    ysub = 400 + len(title) * 84 + 10
    s += f'<text x="84" y="{ysub}" fill="{TXT2}" font-family="{LATIN}" font-size="26" font-weight="500">{esc(sub)}</text>\n'
    s += f'<text x="80" y="666" fill="{TXT3}" font-family="{CJK}" font-size="20" font-weight="500">{esc(d.get("author", ""))}  ·  {esc(d.get("date", ""))}</text>\n'
    return s + logo_img() + '</svg>\n'


def render_agenda(d):
    items = d.get('items', [])
    s = page('content') + chrome(d.get('title', '议程'))
    for i, it in enumerate(items[:8]):
        col, row = i % 2, i // 2
        x, y = 80 + col * 580, 190 + row * 145
        ac = ACCENTS[i % 3]
        s += (f'<rect x="{x}" y="{y}" width="540" height="110" rx="14" fill="{SURF}" fill-opacity="0.55" stroke="{ac}" stroke-opacity="0.22"/>\n'
              f'<rect x="{x}" y="{y}" width="6" height="110" rx="3" fill="{ac}"/>\n'
              f'<text x="{x + 40}" y="{y + 70}" fill="{ac}" fill-opacity="0.65" font-family="{LATIN}" font-size="44" font-weight="500">{i + 1:02d}</text>\n'
              f'<text x="{x + 130}" y="{y + 68}" fill="{TXT}" font-family="{CJK}" font-size="30" font-weight="600">{esc(it.get("title_zh", ""))}</text>\n')
    return s + '</svg>\n'


def render_section(d):
    num, title, lede = d.get('chapter_num', ''), d.get('title', ''), d.get('lede', '')
    pills = d.get('pills', [])
    s = page('section')
    s += f'<text x="90" y="300" fill="{PURP}" fill-opacity="0.5" font-family="{LATIN}" font-size="180" font-weight="600">{esc(num)}</text>\n'
    s += f'<text x="96" y="410" fill="{TXT}" font-family="{CJK}" font-size="60" font-weight="700">{esc(title)}</text>\n'
    s += f'<rect x="100" y="444" width="120" height="6" rx="3" fill="url(#kl)"/>\n'
    lede_lines = wrap(lede, 1000, 24)
    s += multiline(100, 500, lede_lines, 24, 36, TXT2, CJK, '500')
    py = 500 + max(1, len(lede_lines)) * 36 + 20
    px = 100
    for p in pills[:6]:
        tw = int(sum(cw(c, 18) for c in p) + 44)
        s += (f'<rect x="{px}" y="{py}" width="{tw}" height="40" rx="20" fill="{SURF}" fill-opacity="0.7" stroke="{PRI}" stroke-opacity="0.4"/>\n'
              f'<text x="{px + tw // 2}" y="{py + 27}" fill="{CYAN}" font-family="{CJK}" font-size="18" font-weight="500" text-anchor="middle">{esc(p)}</text>\n')
        px += tw + 14
    return s + logo_img() + '</svg>\n'


def render_3up(d):
    title = d.get('title', '')
    cards = d.get('cards', [])
    s = page('content') + chrome(title)
    for i, card in enumerate(cards[:3]):
        x, ac = [83, 471, 859][i], ACCENTS[i]
        s += (f'<rect x="{x}" y="170" width="338" height="440" rx="18" fill="{SURF}" fill-opacity="0.78" stroke="{ac}" stroke-opacity="0.32"/>\n'
              f'<rect x="{x}" y="170" width="338" height="5" rx="2" fill="{ac}" fill-opacity="0.7"/>\n'
              f'<text x="{x + 33}" y="270" fill="{ac}" fill-opacity="0.7" font-family="{LATIN}" font-size="58" font-weight="500">{esc(card.get("num", f"{i + 1:02d}"))}</text>\n'
              f'<text x="{x + 33}" y="350" fill="{TXT}" font-family="{CJK}" font-size="32" font-weight="700">{esc(card.get("title_zh", ""))}</text>\n')
        s += multiline(x + 33, 402, wrap(card.get('body', ''), 280, 17), 17, 26, TXT2, CJK, '500')
        s += (f'<rect x="{x + 33}" y="560" width="200" height="1" fill="{DIV}" fill-opacity="0.16"/>\n'
              f'<text x="{x + 33}" y="586" fill="{TXT3}" font-family="{LATIN}" font-size="13" font-weight="500" letter-spacing="1">{esc(card.get("footer_label", ""))}</text>\n')
    return s + '</svg>\n'


def render_2col(d):
    title = d.get('title', '')
    text = d.get('text', {}) or {}
    lede, feats = text.get('lede', ''), text.get('feature_list', [])
    s = page('content') + chrome(title)
    lede_lines = wrap(lede, 540, 22)
    s += multiline(64, 200, lede_lines, 22, 34, TXT, CJK, '600')
    fy = 200 + max(1, len(lede_lines)) * 34 + 30
    for f in feats[:6]:
        s += (f'<rect x="64" y="{fy - 18}" width="6" height="6" rx="3" fill="{PRI}"/>\n'
              f'<text x="86" y="{fy}" fill="{TXT2}" font-family="{CJK}" font-size="19" font-weight="500">{esc(f)}</text>\n')
        fy += 40
    s += (f'<rect x="680" y="170" width="540" height="440" rx="16" fill="{SURF}" fill-opacity="0.6" stroke="{PRI}" stroke-opacity="0.22"/>\n'
          f'<text x="710" y="220" fill="{TXT3}" font-family="{LATIN}" font-size="14" font-weight="600" letter-spacing="1">VISUAL PANEL</text>\n')
    return s + '</svg>\n'


def render_table(d):
    title, headers, rows = d.get('title', ''), d.get('headers', []), d.get('rows', [])
    s = page('content') + chrome(title)
    x0, y0, total = 64, 180, 1152
    widths = [300, total - 300] if len(headers) == 2 else [total // max(1, len(headers))] * max(1, len(headers))
    cx = x0
    s += f'<rect x="{x0}" y="{y0}" width="{total}" height="56" rx="8" fill="{PRI}" fill-opacity="0.20"/>\n'
    for hi, h in enumerate(headers):
        s += f'<text x="{cx + 22}" y="{y0 + 36}" fill="{CYAN}" font-family="{CJK}" font-size="20" font-weight="700">{esc(h)}</text>\n'
        cx += widths[hi]
    ry, rh = y0 + 56, min(72, (520 - 56) // max(1, len(rows)))
    for ri, row in enumerate(rows):
        if ri % 2 == 1:
            s += f'<rect x="{x0}" y="{ry}" width="{total}" height="{rh}" fill="{SURF}" fill-opacity="0.35"/>\n'
        cx = x0
        for ci, cell in enumerate(row):
            s += multiline(cx + 22, ry + 30, wrap(cell, widths[ci] - 40, 17)[:3], 17, 24, TXT if ci == 0 else TXT2, CJK, '600' if ci == 0 else '500')
            cx += widths[ci]
        ry += rh
    return s + '</svg>\n'


def render_quote(d):
    title = d.get('title', '')
    q = d.get('quote', {}) or {}
    lead, acc, tail, attr = q.get('lead', ''), q.get('accent', ''), q.get('tail', ''), d.get('attribution', '')
    s = page('section')
    s += f'<ellipse cx="640" cy="360" rx="560" ry="320" fill="url(#glow)"/>\n'
    s += f'<text x="100" y="320" fill="{PRI}" fill-opacity="0.35" font-family="{LATIN}" font-size="180" font-weight="700">"</text>\n'
    qlines = wrap(lead, 1000, 30)
    s += multiline(110, 330, qlines, 30, 46, TXT, CJK, '600')
    ybase = 330 + len(qlines) * 46
    s += f'<text x="110" y="{ybase}" fill="{TXT}" font-family="{CJK}" font-size="30" font-weight="600"><tspan fill="{CYAN}" font-weight="700">{esc(acc)}</tspan>{esc(tail)}</text>\n'
    s += f'<text x="112" y="{ybase + 70}" fill="{TXT3}" font-family="{CJK}" font-size="20" font-weight="500">— {esc(attr)}</text>\n'
    return s + logo_img() + '</svg>\n'


def render_stats(d):
    title = d.get('title', '')
    cols = d.get('cols', [])
    stat = d.get('stat')
    s = page('content') + chrome(title)
    if stat:
        s += f'<text x="640" y="380" fill="{PRI}" font-family="{LATIN}" font-size="200" font-weight="700" text-anchor="middle">{esc(stat.get("number", ""))}</text>\n'
        s += f'<text x="640" y="440" fill="{CYAN}" font-family="{CJK}" font-size="34" font-weight="600" text-anchor="middle">{esc(stat.get("unit", ""))}</text>\n'
        s += multiline(200, 540, wrap(d.get('body', ''), 880, 22), 22, 36, TXT2, CJK, '500')
        return s + '</svg>\n'
    n = max(1, len(cols[:4]))
    col_w = 1152 // n
    for i, c in enumerate(cols[:4]):
        x, ac = 64 + i * col_w, ACCENTS[i % 3]
        s += (f'<rect x="{x + 14}" y="200" width="{col_w - 28}" height="300" rx="16" fill="{SURF}" fill-opacity="0.55" stroke="{ac}" stroke-opacity="0.22"/>\n'
              f'<text x="{x + col_w // 2}" y="330" fill="{ac}" font-family="{LATIN}" font-size="62" font-weight="700" text-anchor="middle">{esc(c.get("num", ""))}<tspan font-size="30" fill="{TXT2}"> {esc(c.get("unit", ""))}</tspan></text>\n')
        s += multiline(x + 30, 390, wrap(c.get('label', ''), col_w - 60, 17), 17, 26, TXT2, CJK, '500')
    foot = d.get('footnote', '')
    if foot:
        s += multiline(64, 620, wrap(foot, 1150, 15), 15, 22, TXT3, CJK, '400')
    return s + '</svg>\n'


def render_end(d):
    contact = d.get('contact', '')
    s = page('cover')
    s += f'<ellipse cx="640" cy="320" rx="520" ry="300" fill="url(#glow)"/>\n'
    s += f'<text x="640" y="300" fill="{TXT}" font-family="{CJK}" font-size="58" font-weight="700" text-anchor="middle">下一步</text>\n'
    s += f'<rect x="560" y="330" width="160" height="6" rx="3" fill="url(#kl)"/>\n'
    s += multiline(640, 410, wrap(contact, 900, 24), 24, 38, TXT2, CJK, '500', 'middle')
    return s + logo_img() + '</svg>\n'


def render_placeholder(slide):
    layout = slide.get('variant') or slide.get('layout', '')
    title = slide.get('data', {}).get('title', '')
    return (page('content') + chrome(title) +
            f'<text x="640" y="400" fill="{TXT3}" font-family="{CJK}" font-size="24" text-anchor="middle">'
            f'[ raw / {esc(layout)} — 走 snapshot 兜底 ]</text>\n</svg>\n')


SHOOT = Path(__file__).resolve().parent / 'shoot.py'


def render_image_slide(png_path):
    """full-bleed image SVG (for raw slides → snapshot via shoot.py)"""
    b64 = base64.b64encode(Path(png_path).read_bytes()).decode()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">\n'
            f'<image href="data:image/png;base64,{b64}" x="0" y="0" width="1280" height="720" '
            f'preserveAspectRatio="xMidYMid meet"/>\n</svg>\n')


LAYOUTS = {'cover': render_cover, 'agenda': render_agenda, 'section': render_section,
           'quote': render_quote, 'table': render_table, 'end': render_end}

_SCHEMA_PRED = lambda l, v: l in LAYOUTS or (l == 'content' and v in ('3up', '2col')) or l == 'stats'


def _render_schema(slide):
    layout, variant, d = slide.get('layout'), slide.get('variant'), slide.get('data', {})
    if layout in LAYOUTS:
        return LAYOUTS[layout](d)
    if layout == 'content' and variant == '3up':
        return render_3up(d)
    if layout == 'content' and variant == '2col':
        return render_2col(d)
    if layout == 'stats':
        return render_stats(d)
    return None


def main():
    ap = argparse.ArgumentParser(description='deck.json → per-page SVG (schema native; raw → snapshot if --html)')
    ap.add_argument('deck_json')
    ap.add_argument('out_dir')
    ap.add_argument('--html', help='rendered index.html; if given, raw slides are snapshotted from it (hybrid export)')
    ap.add_argument('--pptx', action='store_true', help='also run the vendored svg_to_pptx → editable PPTX in <out_dir>/exports/')
    args = ap.parse_args()
    dp, out = Path(args.deck_json), Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    svg_dir = out / 'svg_output'
    svg_dir.mkdir(parents=True, exist_ok=True)
    deck = json.loads(dp.read_text(encoding='utf-8'))
    slides = deck.get('slides', [])

    raw, native = [], 0
    for i, slide in enumerate(slides, 1):
        key = slide.get('key', f'slide{i}')
        svg = _render_schema(slide)
        if svg is None:
            raw.append((i, key, slide))
            continue
        (svg_dir / f'{i:02d}_{key}.svg').write_text(svg, encoding='utf-8')
        native += 1

    shot = 0
    if raw and args.html and SHOOT.is_file():
        with tempfile.TemporaryDirectory(prefix='deck_svg_shoot_') as tmp:
            pages = ','.join(str(i) for i, _, _ in raw)
            rc = subprocess.run([sys.executable, str(SHOOT), args.html, '--pages', pages, '--out', tmp]).returncode
            if rc == 0:
                for i, key, slide in raw:
                    cands = list(Path(tmp).glob(f'p{i:02d}-*.png'))
                    if cands:
                        (svg_dir / f'{i:02d}_{key}.svg').write_text(render_image_slide(cands[0]), encoding='utf-8')
                        shot += 1
                        continue
            # fall through to placeholder if shoot failed
            for i, key, slide in raw:
                if not (svg_dir / f'{i:02d}_{key}.svg').exists():
                    (svg_dir / f'{i:02d}_{key}.svg').write_text(render_placeholder(slide), encoding='utf-8')
    else:
        for i, key, slide in raw:
            (svg_dir / f'{i:02d}_{key}.svg').write_text(render_placeholder(slide), encoding='utf-8')

    n = len(slides)
    ph = len(raw) - shot
    print(f'[done] {n} slides → SVG ({native} native · {shot} raw→snapshot' +
          (f' · {ph} placeholder' if ph else '') + ')')
    if args.pptx:
        from svg_to_pptx import main as _svg2pptx
        rc = _svg2pptx([str(out)])
        if rc == 0:
            exports = out / 'exports'
            pptxs = sorted(exports.glob('*.pptx'), key=lambda p: p.stat().st_mtime) if exports.is_dir() else []
            print(f'[pptx] → {pptxs[-1]}' if pptxs else '[pptx] no .pptx in exports/', file=sys.stderr if not pptxs else sys.stdout)
        else:
            print(f'[pptx] svg_to_pptx failed (exit {rc})', file=sys.stderr)
        return rc
    return 0


if __name__ == '__main__':
    sys.exit(main())
