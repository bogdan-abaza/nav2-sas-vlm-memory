"""Schedule for the controlled semantic-resolution evaluation (protocol a4_semantic_comparison_20261005, section 7).
Writes schedule/SCHEDULE_<cond>.csv and schedule/SCHEDULE.sha256. No model calls.  python3 -B sc_schedule.py"""
import os, csv, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BASES = [1, 2, 3]
ORD_EVEN = {1: 'ABC', 2: 'BCA', 3: 'CAB'}; ORD_ODD = {1: 'ACB', 2: 'CBA', 3: 'BAC'}
def item_seed(base, item_id, condition):
    h = int(hashlib.md5(('%s|%s' % (item_id, condition)).encode()).hexdigest()[:8], 16)
    return (base * 1_000_003 + h) % (2 ** 31 - 1)
def items_for(cond):
    return sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, 'bundles', cond)) if f.endswith('.json'))
def schedule(cond):
    its = items_for(cond); blocks = []
    for idx, iid in enumerate(its):
        for base in BASES:
            order = (ORD_EVEN if idx % 2 == 0 else ORD_ODD)[base]
            key = hashlib.sha256(('20261005|%s|%s|%d' % (cond, iid, base)).encode()).hexdigest()
            blocks.append((key, cond, iid, base, order))
    blocks.sort(key=lambda b: (b[0], b[1], b[2], b[3]))
    rows, n = [], 0
    for bi, (key, c, iid, base, order) in enumerate(blocks):
        for pos, arm in enumerate(order):
            rows.append(dict(seq=n, block=bi, block_key=key, condition=c, item_id=iid, item_index=its.index(iid), seed_base=base,
                             arm=arm, position=pos, order=order, seed=item_seed(base, iid, c))); n += 1
    return rows
if __name__ == '__main__':
    d = os.path.join(ROOT, 'schedule'); os.makedirs(d, exist_ok=True); out = []
    for c in ('S', 'H'):
        rows = schedule(c); p = os.path.join(d, 'SCHEDULE_%s.csv' % c)
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        out.append(p); print(c, len(rows), 'observations,', len({(r['item_id'], r['seed_base']) for r in rows}), 'blocks')
    with open(os.path.join(d, 'SCHEDULE.sha256'), 'w') as f:
        for p in out: f.write('%s  %s\n' % (hashlib.sha256(open(p, 'rb').read()).hexdigest(), os.path.basename(p)))
    print(open(os.path.join(d, 'SCHEDULE.sha256')).read().strip())
