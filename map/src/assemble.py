import json,sys
S,OUT=sys.argv[1],sys.argv[2]
d=json.load(open(S+"/data.min.json")); sc=json.load(open(S+"/scheme.json"))
for l in sc['labels']: l.pop('c',None); l.pop('bw',None)
d['scheme']=sc
s=json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
t=open(S+"/template.html").read().replace('__DATA__',s)
open(OUT+"/index.html","w").write(t)
print(len(t.encode()))
