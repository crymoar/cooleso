"""Take the scheme exactly as yandex.ru/metro renders it (its two SVG layers), drop decorative icons only."""
import re,sys
L0=open(sys.argv[1]).read(); L1=open(sys.argv[2]).read(); OUT=sys.argv[3]
inner=lambda s:re.sub(r'^<svg[^>]*>|</svg>$','',s.strip())
b0=inner(L0); b1=inner(L1)
# decorations group: keep the first nested <svg> (river background) and non-image shapes, drop other nested svgs (icons)
m=re.search(r'<g class="scheme-objects-view__decorations[^"]*">',b0)
start=m.end()
# walk nested svg blocks inside decorations
out=[];i=start;depth=0;kept_bg=False;dec_end=None
pos=start
res=b0[:start]
tok=re.compile(r'<(/?)(svg|g)\b[^>]*>')
stack=[]
cur=start
while True:
    t=tok.search(b0,cur)
    if not t: break
    closing,tag=t.group(1),t.group(2)
    if not stack and closing and tag=='g':   # end of decorations group
        res+=b0[cur:t.end()]; dec_end=t.end(); break
    if not closing and tag=='svg' and not stack:
        # find matching end of this nested svg
        d=0;k=t.start()
        for u in re.finditer(r'<(/?)svg\b[^>]*>',b0[t.start():]):
            d+= -1 if u.group(1) else 1
            if d==0: end=t.start()+u.end(); break
        res+=b0[cur:t.start()]
        blk=b0[t.start():end]
        pass  # decorations (river, icons, line badges) dropped
        cur=end; continue
    if not closing: stack.append(tag)
    elif stack: stack.pop()
    res+=b0[cur:t.end()]; cur=t.end()
res+=b0[dec_end:]
res=re.sub(r'<circle[^>]*\br="16"[^>]*>(</circle>)?','',res)
css='<style>text{font-family:"YS Text",Inter,Arial,Helvetica,sans-serif}.scheme-objects-view__label circle{visibility:hidden;opacity:0}</style>'
svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3000 3500">{css}<g id="objects">{res}</g><g id="labels">{b1}</g></svg>'
open(OUT,'w').write(svg); print(len(svg), 'nested svgs left:', svg.count('<svg')-1)
