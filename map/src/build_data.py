import json,sys
d=json.load(open(sys.argv[1]))
fold=lambda s:s.lower().replace('ё','е').replace(' ','').replace('-','')
leg={}
for x in d['legacyStations']:
    k=fold(x['name']); leg.setdefault(k,set()).update(x['kinds'])
r5=lambda v:round(v,5)
linecolor={l['name']:l['color'] for l in d['network']}
stations=[]
for s in d['stations']:
    meet=any(r['basis']=='explicit' for r in s['refs'])
    k=leg.get(fold(s['name']),set())
    kpp=[t for t,c in (('mt','manual'),('at','automatic')) if c in k]
    stations.append({'id':s['id'],'n':s['name'],'lat':r5(s['lat']),'lon':r5(s['lon']),'k':s['kind'],'l':s['lines'],'m':int(meet),'kpp':kpp})
points=[]
for p in d['points']:
    nb=sorted(({'s':n['station_id'],'t':round(n['seconds']/60),'d':round(n['km']*1000)} for n in p['nearby']),key=lambda x:x['t'])
    name=p['address'].replace('Точка из ссылки: ','')
    points.append({'id':p['id'],'n':name,'pin':int(p['address'].startswith('Точка из ссылки')),'lat':r5(p['lat']),'lon':r5(p['lon']),'nb':nb,'c':p['caution']})
import math
rings={'5','95','97'}
bad=lambda s:not(36.5<s['lon']<39.2 and 55.0<s['lat']<56.6) or s['lon']==s['lat'] or s['name'] in BADNAMES
BADNAMES={'Лобня'}  # lon 37.29 in source, real ~37.48
km=lambda a,b:math.hypot((a[1]-b[1])*111,(a[0]-b[0])*111*0.563)
lines=[];dropped=[]
for l in d['network']:
    ok=[s for s in l['stations'] if not bad(s)]
    dropped+= [f"{s['name']} ({l['name']}): {s['lat']}, {s['lon']}" for s in l['stations'] if bad(s)]
    c=[[r5(s['lon']),r5(s['lat'])] for s in ok]
    if l['id'] in rings: c.append(c[0])
    parts=[[c[0]]]
    for a,b2 in zip(c,c[1:]):
        if km(a,b2)>9: parts.append([b2])
        else: parts[-1].append(b2)
    parts=[p for p in parts if len(p)>1]
    lines.append({'id':l['id'],'n':l['name'],'c':l['color'],'k':l['kind'],'g':parts,'st':[s['id'] for s in l['stations']]})
allst={s['id']:{'n':s['name'],'lat':r5(s['lat']),'lon':r5(s['lon'])} for l in d['network'] for s in l['stations'] if not bad(s)}
print('dropped',dropped,file=sys.stderr)
svc=[]
byname={}
for l in d['network']:
    for st in l['stations']: byname.setdefault(fold(st['name']),st['id'])
for x in d['legacyStations']:
    k=x['kinds']
    if not any(c in k for c in ('office','moto_indoor','moto_outdoor')): continue
    sid=byname.get(fold(x['name']))
    st=next((s0 for l in d['network'] for s0 in l['stations'] if s0['id']==sid),None)
    svc.append({'id':x['id'],'k':k[0],'n':x['name'],'sid':sid,'note':x.get('note',''),'lat':r5(st['lat']) if st else None,'lon':r5(st['lon']) if st else None})
out={'svc':svc,'date':d['meta']['date'],'stations':stations,'points':points,'lines':lines,'allst':allst,'issues':d['issues']}
s=json.dumps(out,ensure_ascii=False,separators=(',',':'))
print(len(s.encode()),file=sys.stderr)
print(s)
