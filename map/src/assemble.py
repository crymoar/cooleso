import json,sys,os
S,OUT=sys.argv[1],sys.argv[2]
d=json.load(open(S+"/data.min.json")); sc=json.load(open(S+"/scheme_ym.json"))
metro={'lines':d['lines'],'allst':d['allst'],'scheme':sc}
os.makedirs(OUT+"/data",exist_ok=True)
json.dump(metro,open(OUT+"/data/metro.json","w"),ensure_ascii=False,separators=(',',':'))
t=open(S+"/template.html").read()
open(OUT+"/index.html","w").write(t)
print(len(t.encode()))
