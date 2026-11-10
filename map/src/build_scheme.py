import re,json,sys,collections
S=sys.argv[1]
s=open(S+"/schem.svg").read()
d=json.load(open(S+"/data.json")); A=json.load(open(S+"/anchors.json"))
T=lambda x,y:(round(-14.94656226+2.47358478*x,1),round(-46.29066555+2.47358478*y,1))
PDFC={'1':['#ed1b2e'],'2':['#46b85e'],'3':['#0077bf','#0078bf'],'4':['#00c1f3'],'5':['#894f35'],'6':['#f5821f'],'7':['#8e479b'],'8':['#ffdd00'],'9':['#a0a2a3'],'10':['#b4d444'],'12':['#acbfe3'],'133':['#ffdd00'],'95':['#ed1b2e'],'97':['#78cdcd'],'98':['#f287b6','#f288b7'],'131':['#faa619'],'132':['#ef4c89'],'135':['#f26522'],'136':['#3cba8d'],'137':['#0e866d']}
# ---- labels
L=[]
for m in re.finditer(r'<text([^>]*)>(.*?)</text>',s):
    a=dict(re.findall(r'([\w-]+)="([^"]*)"',m.group(1)))
    L.append({'x':float(a['x']),'y':float(a['y']),'fs':float(a['font-size']),'w':float(a['textLength']),'t':m.group(2).replace('&amp;','&')})
fold=lambda x:re.sub(r'[\s\-\.]','',re.sub(r'\s*\(.*?\)|\s+I+$','',x).lower().replace('ё','е'))
FIX=[('Шоссе',483.75,299.3545-5.1,4.3,14.2,'before'),('вокзалов',343.625,271.3801+5.1,4.3,19.0,'after')]
restored=[]
for t,x,y,fs,w,_ in FIX: L.append({'x':x,'y':y,'fs':fs,'w':w,'t':t,'fix':1}); restored.append(t)
byname=collections.defaultdict(list); line_of=collections.defaultdict(list)
for l in d['network']:
    for st in l['stations']:
        if st['id'] not in byname[fold(st['name'])]: byname[fold(st['name'])].append(st['id'])
        line_of[st['id']].append(l['id'])
alias={fold('Матвеевская'):fold('Матвеевское'),fold('Лермонтовский просп.'):fold('Лермонтовский проспект'),fold('Зеленоград-Крюково'):fold('Крюково')}
used=set(); groups=[]
order=sorted(range(len(L)),key=lambda i:(L[i]['y']))
for i in order:
    if i in used: continue
    g=[i]; used.add(i)
    while True:
        last=L[g[-1]]; nxt=None
        for j in order:
            if j in used: continue
            c=L[j]; dy=c['y']-last['y']
            if 0<dy<last['fs']*1.45 and (abs(c['x']-last['x'])<1.2 or abs(c['x']+c['w']-last['x']-last['w'])<1.2 or abs(c['x']+c['w']/2-last['x']-last['w']/2)<1.2):
                nxt=j;break
        if nxt is None: break
        # only merge if merged text matches better
        cand=fold(' '.join(L[k]['t'] for k in g+[nxt]))
        cand=alias.get(cand,cand)
        if cand in byname or any(n.startswith(cand) for n in byname): g.append(nxt);used.add(nxt)
        else: break
    groups.append(g)
labels=[];unmatched=[];found=set()
for g in groups:
    text=' '.join(L[k]['t'] for k in g); key=alias.get(fold(text),fold(text))
    ids=byname.get(key,[])
    if not ids: unmatched.append(text)
    found.update(ids)
    first=L[g[0]]; x,y=T(first['x'],first['y'])
    xs=[L[k]['x'] for k in g]; al='start' if max(xs)-min(xs)<1.2 else ('end' if all(abs(L[k]['x']+L[k]['w']-first['x']-first['w'])<1.2 for k in g) else 'middle')
    if al=='end': x=T(first['x']+first['w'],0)[0]
    if al=='middle': x=T(first['x']+first['w']/2,0)[0]
    bw=round(max(L[k]['w'] for k in g)*2.47358478,1)
    labels.append({'x':x,'y':y,'a':al[0],'t':[L[k]['t'] for k in g],'ids':ids,'bw':bw,**({'fix':1} if any(L[k].get('fix') for k in g) else {})})
# station positions on scheme: anchors, else label centre
pos={}
for sid,a in A.items(): pos[sid]=[round(a['x'],1),round(a['y'],1)]
for lb in labels:
    cx=lb['x']-7 if lb['a']=='s' else lb['x']+7 if lb['a']=='e' else lb['x']; cy=lb['y']-3.5 if lb['a']!='m' else lb['y']-13
    for sid in lb['ids']: pos.setdefault(sid,[round(cx,1),round(cy,1)]); lb['c']=[round(cx,1),round(cy,1)]
# ---- checks
rep=[('Подписи, потерянные при переносе из PDF и восстановленные',restored)]
net_ids={st['id']:(st['name'],l['name']) for l in d['network'] for st in l['stations']}
missing=[f"{n} ({ln})" for sid,(n,ln) in net_ids.items() if sid not in found]
rep.append(('Станции из справочника, которых нет на схеме (подписи не найдены)',sorted(set(missing))))
rep.append(('Подписи на схеме, не сопоставленные со справочником станций',sorted(set(unmatched))))
bad=[]
for sid,a in A.items():
    if 'color' in a:
        h='#%02x%02x%02x'%tuple(round(c*255) for c in a['color'])
        exp=sum((PDFC.get(l,[]) for l in line_of.get(sid,[])),[])
        if exp and h not in exp: bad.append(f"{net_ids.get(sid,(sid,''))[0]}: привязка к линии цвета {h}, а станция на {', '.join(net_ids.get(sid,('',''))[1:])}")

far=[]
for lb in labels:
    for sid in lb['ids']:
        if sid in A:
            dx=A[sid]['x']-lb['c'][0]; dy=A[sid]['y']-lb['c'][1]
            if (dx*dx+dy*dy)**.5>90 and len(lb['ids'])==1: far.append(f"{net_ids[sid][0]}: метка в {int((dx*dx+dy*dy)**.5)} px от своей подписи")
rep.append(('Метки далеко от собственной подписи',far))
lines={}
for l in d['network']:
    lines[l['id']]={'n':l['name'],'c':l['color'],'pdf':PDFC.get(l['id'],[]),'st':[st['id'] for st in l['stations']]}
json.dump({'labels':labels,'pos':pos,'lines':lines},open(S+"/scheme.json","w"),ensure_ascii=False,separators=(',',':'))
json.dump(rep,open(S+"/report.json","w"),ensure_ascii=False,indent=1)
for t,v in rep: print('##',t,len(v)); print('  '+'\n  '.join(v[:60]))
# ---- geometry without text
g=re.sub(r'<g class="pdf-text-layer">.*?</g>(?=</g></g></svg>)','',s,flags=re.S)
g=re.sub(r'<title>.*?</title><desc>.*?</desc>','',g,flags=re.S)
g=re.sub(r'<style>.*?</style>','',g,flags=re.S)
open(S+"/geo.svg","w").write(g)
