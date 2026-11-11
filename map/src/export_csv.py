"""Export map/data/places.json + metro.json to a human-editable places.csv (UTF-8 with BOM, ';')."""
import csv, json, sys, collections
places, metro, out = sys.argv[1], sys.argv[2], sys.argv[3]
P = json.load(open(places)); M = json.load(open(metro))
lines_of = collections.defaultdict(list)
for l in M['lines']:
    for i in l['st']: lines_of[i].append(l['n'])
name_count = collections.Counter(s['n'] for s in M['allst'].values())
KR = {'Метро': 0, 'МЦК': 1, 'МЦД': 2}
kind_of = {i: next((l['k'] for l in M['lines'] if i in l['st']), 'Метро') for i in M['allst']}
def default_id(name):
    ids = [i for i, s in M['allst'].items() if s['n'] == name]
    return sorted(ids, key=lambda i: KR.get(kind_of[i], 3))[0]
def ref(i):
    """station name, with the line only when the name alone would pick another station"""
    n = M['allst'][i]['n']
    return n if default_id(n) == i else f"{n} ({lines_of[i][0]})"
yn = lambda b: 'да' if b else ''
cols = ['тип', 'название', 'линия', 'мкпп', 'акпп', 'встреча', 'широта', 'долгота', 'станции', 'станция', 'примечание']
rows = []
for s in P['stations']:
    near_only = not s['m']
    if near_only and not s['kpp']: continue          # derived again from addresses
    n = s['n']; line = '' if default_id(n) == s['id'] else lines_of[s['id']][0]
    rows.append({'тип': 'метро', 'название': n, 'линия': line, 'мкпп': yn('mt' in s['kpp']), 'акпп': yn('at' in s['kpp']),
                 'встреча': 'нет' if near_only else ''})
# legacy meeting stations that were only on the old map
for n in ('Долгопрудная', 'Достоевская'):
    i = default_id(n)
    if not any(x['id'] == i for x in P['stations']):
        rows.append({'тип': 'метро', 'название': n, 'мкпп': 'да'})
for p in P['points']:
    st = ', '.join(f"{ref(x['s'])} {x['t']} мин {x['d']} м" for x in p['nb'])
    rows.append({'тип': 'точка' if p.get('pin') else 'адрес', 'название': p['n'], 'широта': p['lat'], 'долгота': p['lon'],
                 'станции': st, 'примечание': p.get('c', '')})
for v in P['svc']:
    t = {'office': 'офис', 'moto_indoor': 'мото (зал)', 'moto_outdoor': 'мото (улица)'}[v['k']]
    note = v['note'].split('\n', 1)[1] if v['k'] == 'office' and '\n' in v['note'] else v['note']
    rows.append({'тип': t, 'станция': ref(v['sid']), 'примечание': note})
with open(out, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols, delimiter=';'); w.writeheader(); w.writerows(rows)
print(len(rows), 'rows')
