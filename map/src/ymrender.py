"""Render the Yandex Metro Moscow scheme data into one compact SVG (light theme, normal state)."""
import json, sys, re, html
SRC, RES, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(SRC))['data']; sd = d['schemeData']; meta = d['schemeMeta']
res = json.load(open(RES))['data']
G = sd['graphics']
W, H = meta['size']['width'], meta['size']['height']
SKIP_IMG = set(sys.argv[4].split(',')) if len(sys.argv) > 4 and sys.argv[4] else set()

ROLE = ['background', 'backLine', 'oveground', 'frontLine', 'hollowOverlayLine', 'connection', 'border', 'mainCircle', 'image', 'textStroke', 'text']
rank = {r: i for i, r in enumerate(ROLE)}
f = lambda v: ('%.2f' % v).rstrip('0').rstrip('.') if isinstance(v, float) else str(v)

def attrs(e, keys):
    out = []
    for k, a in keys:
        if k in e and e[k] is not None and e[k] != '':
            out.append(f'{a}="{html.escape(str(e[k]))}"')
    return ' '.join(out)

used_res = {}
def prim(e, sid=None):
    t = e['type']
    if e.get('opacity', 1) == 0: return ''
    op = '' if e.get('opacity', 1) == 1 else f' opacity="{e["opacity"]}"'
    if t == 'Line':
        return f'<line x1="{f(e["x1"])}" y1="{f(e["y1"])}" x2="{f(e["x2"])}" y2="{f(e["y2"])}" stroke="{e["stroke"]}" stroke-width="{f(e["strokeWidth"])}" stroke-linecap="{e.get("strokeLinecap","butt")}"{op}/>'
    if t == 'Path':
        a = [f'd="{e["d"].strip()}"', f'fill="{e.get("fill") or "none"}"']
        if e.get('stroke'): a.append(f'stroke="{e["stroke"]}" stroke-width="{f(e.get("strokeWidth",1))}"')
        for k, n in (('strokeDasharray', 'stroke-dasharray'), ('strokeDashoffset', 'stroke-dashoffset'), ('strokeLinecap', 'stroke-linecap'), ('strokeLinejoin', 'stroke-linejoin')):
            if e.get(k) not in (None, ''): a.append(f'{n}="{e[k]}"')
        return '<path ' + ' '.join(a) + op + '/>'
    if t == 'Circle':
        return f'<circle cx="{f(e["x"]+e.get("cx",0))}" cy="{f(e["y"]+e.get("cy",0))}" r="{f(e["r"])}" fill="{e.get("fill","none")}"{op}/>'
    if t == 'SVGImage':
        r = e['resource']
        if (r.startswith('image-') and r != 'bg-z4.svg') or r in SKIP_IMG or 'preset_icon' in r: return ''
        used_res[r] = 1
        tr = e.get('transform', '')
        return f'<use href="#r-{re.sub(r"[^a-zA-Z0-9]", "-", r)}" transform="translate({f(e["x"])} {f(e["y"])}) {tr}"{op}/>'
    if t == 'Text':
        lines = e['text'].split('\n'); lh = e.get('lineHeight') or e['fontSize']*1.15; fs = e['fontSize']; an = e['textAnchor']
        x, y, h = e['x'], e['y'], e.get('height') or lh*len(lines)
        anchor = {'h': 'start', 'a': 'start', 'f': 'end', 'b': 'end'}[an]
        if e.get('width') and e.get('width') == e.get('height') and e['width'] <= 40: anchor = 'middle'
        top = y - h / 2
        cls = 'ts' if e['id'] == 'textStroke' else 'tx'
        fw = ' font-weight="700"' if e.get('fontWeight') == 'bold' else ''
        stroke = f' stroke="{e["stroke"]}" stroke-width="{f(e["strokeWidth"])}"' if e['id'] == 'textStroke' else ''
        spans = ''.join(f'<tspan x="{f(x)}" y="{f(top + lh*i + lh*0.5 + fs*0.36)}">{html.escape(s)}</tspan>' for i, s in enumerate(lines))
        sk = f' data-s="{sid}"' if sid and e['id'] == 'text' else ''
        return f'<text class="{cls}" font-size="{f(fs)}" text-anchor="{anchor}" fill="{e["color"]}"{fw}{stroke}{sk}>{spans}</text>'
    return ''

# graphics owners
owner = {}
for s in sd['stations']:
    for gid in s.get('graphicsIds', []): owner[gid] = s['id']
layers = {r: [] for r in ROLE}; other = []
dec = set(sd['decorationGraphicIds'])
REF = set()
for s_ in sd['stations']:
    REF.update(s_['graphicsIds'])
    for sp_ in s_['stops']: REF.update(sp_.get('graphicsIds', []))
for h_ in sd['transferHubs']: REF.update(h_['graphicsIds'])
REF |= set(sd['foregroundGraphicsMap'].values()) | dec
def detailed(gid):
    if gid in REF: return True
    fl = [e for e in G[gid] if e.get('id') == 'frontLine']
    return bool(fl) and fl[0].get('strokeWidth') in (8, 5)
order = [k for k in list(sd['decorationGraphicIds']) + [k for k in G if k not in dec] if detailed(k)]
for gid in order:
    for e in G[gid]:
        s = prim(e, owner.get(gid))
        if not s: continue
        layers.get(e.get('id'), other).append(s)

def res_svg(key):
    txt = res.get(key) or ''
    txt = re.sub(r'<\?xml[^>]*>', '', txt)
    return txt

defs = []
for r in used_res:
    body = res_svg(r)
    m = re.search(r'<svg([^>]*)>(.*)</svg>', body, re.S)
    if not m: continue
    wm = re.search(r'width="([\d.]+)', m.group(1)); hm = re.search(r'height="([\d.]+)', m.group(1)); vb = re.search(r'viewBox="([^"]+)"', m.group(1))
    defs.append(f'<symbol id="r-{re.sub(r"[^a-zA-Z0-9]", "-", r)}" overflow="visible"><svg width="{wm.group(1) if wm else 16}" height="{hm.group(1) if hm else 16}"{(" viewBox=%s" % chr(34) + vb.group(1) + chr(34)) if vb else ""}>{m.group(2)}</svg></symbol>')

bg = res_svg('bg-z4.svg')
bgm = re.search(r'<svg[^>]*>(.*)</svg>', bg, re.S)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">', '<defs>' + ''.join(defs) + '</defs>',
       ]
svg.append('<g id="bg">' + ''.join(x for x in other if 'bg-z4' in x) + '</g>'); other = [x for x in other if 'bg-z4' not in x]
for r in ROLE[:-2]:
    svg.append(f'<g id="l-{r}">' + ''.join(layers[r]) + '</g>')
svg.append('<g id="l-other">' + ''.join(other) + '</g>')
svg.append('<g id="labels">' + ''.join(layers['textStroke']) + ''.join(layers['text']) + '</g>')
svg.append('</svg>')
out = ''.join(svg)
open(OUT, 'w').write(out)
print('bytes', len(out.encode()), 'resources', len(used_res), list(used_res)[:40])
# stations: id, name, position (main circle), line ids
st = []
for s in sd['stations']:
    pos = None; pts = []
    for sp in s['stops']:
        for gid in sp.get('graphicsIds', []):
            for e in G.get(gid, []):
                if e['type'] == 'Circle' and e['id'] == 'mainCircle': pts.append((e['x'], e['y']))
    if pts: pos = (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts))
    for gid in s.get('graphicsIds', []):
        for e in G.get(gid, []):
            if pos is None and e['type'] == 'Circle' and e['id'] == 'mainCircle': pos = (e['x'], e['y'])
            if pos is None and e['type'] == 'Path' and e['id'] == 'border': pass
    st.append({'id': s['id'], 'n': s['name'], 'xy': pos, 'lon': s['coordinates'][0], 'lat': s['coordinates'][1], 'lines': [p['lineId'] for p in s['stops']]})
lines = {l['id']: {'n': l['service']['attributes'].get('name'), 'c': l['service']['attributes'].get('color')} for l in sd['lines']}
json.dump({'st': st, 'lines': lines, 'size': [W, H]}, open(OUT + '.json', 'w'), ensure_ascii=False)
print('stations without circle:', [s['n'] for s in st if not s['xy']][:30])
