import json,re,math,sys
S=sys.argv[1]
Y=json.load(open(S+'/ym.svg.json')); D=json.load(open(S+'/data.json'))
fold=lambda x:re.sub(r'[\s\-\.—«»"]','',re.sub(r'\s*\(.*?\)','',x).lower().replace('ё','е'))
geo=lambda a,b:math.hypot((a[0]-b[0])*63,(a[1]-b[1])*111)
y2h={}; pos={}
hh=[(s['id'],s['name'],s['lat'],s['lon']) for l in D['network'] for s in l['stations']]
for hid,n,lat,lon in hh:
    best=None
    for s in Y['st']:
        if not s['xy']: continue
        dkm=geo((s['lon'],s['lat']),(lon,lat)); same=fold(s['n'])==fold(n)
        score=dkm-(5 if same else 0)
        if (same and dkm<4 or dkm<0.35) and (best is None or score<best[0]): best=(score,s)
    if best:
        s=best[1]; pos[hid]=[round(s['xy'][0],1),round(s['xy'][1],1)]; y2h.setdefault(s['id'],hid)
meet=[s for s in D['stations'] if any(r['basis']=='explicit' for r in s['refs'])]
print('hh matched',len(pos),'of',len(hh)); print('meeting not placed',[s['name'] for s in meet if s['id'] not in pos])
LC={k:(v['c'] or '').lower() for k,v in Y['lines'].items()}
st=[{'id':y2h.get(s['id'],'y'+s['id']),'n':s['n'],'x':round(s['xy'][0],1),'y':round(s['xy'][1],1),'c':sorted({LC[l] for l in s['lines'] if l in LC})} for s in Y['st'] if s['xy']]
json.dump({'pos':pos,'st':st,'y2h':y2h,'vb':[0,0]+Y['size']},open(S+'/scheme_ym.json','w'),ensure_ascii=False,separators=(',',':'))
