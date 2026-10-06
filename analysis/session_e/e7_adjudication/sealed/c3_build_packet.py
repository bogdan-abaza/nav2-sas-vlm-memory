#!/usr/bin/env python3
"""
c3_build_packet.py -- builds the blind E7 adjudication packet (post-hoc sensitivity analysis).

INTERNAL. Reads only RC1.1 public files (pinned by sha256). Writes:
  packets_blind/E7_adjudication_packet_v1/   what the evaluator receives (and a zip of it)
  internal/CODE_MAP.csv                      neutral code -> sealed cell id (never sent)
  internal/BUILD_RECORD.json                 inputs, seed, packet file hashes, leak-check result
Refuses to overwrite an existing packet. Fails if any forbidden content reaches the packet.

The evaluator sees: the 28 instructions (English v2 wording, as executed), the route graph
(node ids, names, coordinates, connections), the static semantic objects (id, class, node,
position), and a plotted map of the same content. The evaluator does NOT see: sealed acceptable
or wrong sets, referent_real, original_ro, v1 wording, provenance, category or level, cell ids,
any system choice, outcome or score, nor any dynamic (YOLO) object.
"""
import csv, hashlib, json, os, random, re, shutil, sys, zipfile
from collections import OrderedDict

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))                        # 07_adjudication
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))                   # ROBOT-D-26-01090
SE = os.path.join(ROOT, 'Review_14.05.2026', 'Outputs', 'PUBLIC_REPO_WORK', 'RC1', 'data', 'session_e', 'day2_20260821')
PINNED = OrderedDict([
    ('session/E7_sealed_set_v2.csv', '587e7b3644de731b1c4d0e3392002ea27e65a66dbcd559a3d02df768f4ab8704'),
    ('config/route_graph_fiir.geojson', 'e769d1e8bb72502ffeb88d8a875a3041ac22775db1fdbf9a62fbb13a30de50b5'),
    ('config/semantic_objects_static_v2.geojson', '963f81c6c6a2c0eda4e7e99486c00e124136367a7e9f725b8e6e773c022ab4fd'),
])
SEED = 20261004                     # order and code assignment; recorded in BUILD_RECORD.json
PACKET = 'E7_adjudication_packet_v1'
PK = os.path.join(HERE, 'packets_blind', PACKET)
INTERNAL = os.path.join(HERE, 'internal')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def fail(m):
    sys.exit('C3 BUILD FAILED: ' + m)


INSTRUCTIONS_MD = """# Destination judgement task

Thank you for helping. This task takes about 30-45 minutes. Please work alone and do not discuss
the items with anyone involved in the project until you have returned the form.

## The setting

A mobile robot operates on one floor of a university building (corridor, laboratories, restrooms,
plants, windows). A person standing in the corridor gives the robot a short spoken request in
English. The robot can only drive to one of the 24 numbered **nodes** of its route map.

You receive:

- `map.png` - a plot of the floor: nodes (numbered), connections, and the fixed objects known to
  the robot;
- `environment_nodes.csv` - every node: number, name, coordinates (metres);
- `environment_objects.csv` - every fixed object known to the robot: identifier, class, the node
  it is attached to, coordinates;
- `items.csv` - 28 requests, each with a neutral code (Q01-Q28). The order is random.

Node and object labels are reproduced exactly from the historical configuration used at the time.
Judge each request using the map and tables as provided. If the available information appears
ambiguous, reflect that in the acceptable-node set, confidence, and optional comment.

## What to decide, for each request

Imagine you are a reasonable person who knows this floor exactly as the map shows it.

1. **Acceptable nodes.** Which node or nodes would be an acceptable place to take the person?
   List every node you consider acceptable (one or more), separated by `|`, e.g. `13|15|20`.
2. **Or: no node is appropriate.** If no node on the map is an acceptable answer, or the request
   is too unclear to act on, write `yes` in `no_node_appropriate` and leave `acceptable_nodes`
   empty. This is a legitimate answer, not a failure: it means the robot should ask for
   clarification instead of driving somewhere.
3. **Clearly wrong nodes (optional).** Nodes that would be a clear mistake, if any stand out.
4. **Confidence**: `high`, `medium` or `low`.
5. **Comment (optional)**: anything that made the item hard or ambiguous.

There are no trick items and no expected number of "no node" answers. Do not try to guess what
the robot did; you are not told, on purpose.

## Returning

Fill in `response_form.csv` (one row per code, all 28 rows) and send it back unchanged in name.
Do not edit the `code` or `request` columns. Every row needs a confidence (`high`, `medium` or `low`).

Before returning the form, please complete `evaluator.txt` (name, affiliation/role, date) and the
confirmation in it, and send both files back together.
"""


EVALUATOR_TXT = """name:
affiliation/role:
date:

I confirm that, before completing this task, I was not shown the original
acceptable-node key or any annotation of the intended destinations, the robot's
selections or outcomes for these requests, or any score obtained on them, and that
I completed the judgement independently.

confirmed (yes/no):
"""


def main():
    for rel, h in PINNED.items():
        if sha(os.path.join(SE, rel)) != h:
            fail('%s is not the RC1.1 file' % rel)
    if os.path.exists(PK):
        fail('packet %s already exists; never overwritten' % PACKET)
    sealed = list(csv.DictReader(open(os.path.join(SE, 'session/E7_sealed_set_v2.csv'), encoding='utf-8')))
    if len(sealed) != 28:
        fail('expected 28 sealed cells')
    graph = json.load(open(os.path.join(SE, 'config/route_graph_fiir.geojson'), encoding='utf-8'))
    objs = json.load(open(os.path.join(SE, 'config/semantic_objects_static_v2.geojson'), encoding='utf-8'))
    nodes = sorted(((f['properties']['id'], f['properties']['name'], f['geometry']['coordinates'])
                    for f in graph['features'] if f['geometry']['type'] == 'Point'), key=lambda x: x[0])
    edges = sorted({tuple(sorted((f['properties']['startid'], f['properties']['endid'])))
                    for f in graph['features'] if f['geometry']['type'] != 'Point'})
    objects = [(f['properties']['obj_id'], f['properties']['class_name'], f['properties']['nearest_node_id'],
                f['geometry']['coordinates']) for f in objs['features']]

    rng = random.Random(SEED)
    order = list(range(28)); rng.shuffle(order)
    items = [('Q%02d' % (k + 1), sealed[i]) for k, i in enumerate(order)]

    os.makedirs(PK); os.makedirs(INTERNAL, exist_ok=True)
    w = lambda name: open(os.path.join(PK, name), 'w', newline='', encoding='utf-8')
    with w('items.csv') as f:
        c = csv.writer(f); c.writerow(['code', 'request'])
        for code, r in items:
            c.writerow([code, r['instructiune_en_v2']])
    with w('response_form.csv') as f:
        c = csv.writer(f); c.writerow(['code', 'request', 'acceptable_nodes', 'no_node_appropriate', 'clearly_wrong_nodes', 'confidence', 'comment'])
        for code, r in items:
            c.writerow([code, r['instructiune_en_v2'], '', '', '', '', ''])
    with w('environment_nodes.csv') as f:
        c = csv.writer(f); c.writerow(['node', 'name', 'x_m', 'y_m'])
        for i, n, xy in nodes:
            c.writerow([i, n, '%.2f' % xy[0], '%.2f' % xy[1]])
    with w('environment_edges.csv') as f:
        c = csv.writer(f); c.writerow(['node_a', 'node_b'])
        c.writerows(edges)
    with w('environment_objects.csv') as f:
        c = csv.writer(f); c.writerow(['object', 'class', 'attached_node', 'x_m', 'y_m'])
        for o, cl, nn, xy in objects:
            c.writerow([o, cl, nn, '%.2f' % xy[0], '%.2f' % xy[1]])
    open(os.path.join(PK, 'README_EVALUATOR.md'), 'w', encoding='utf-8').write(INSTRUCTIONS_MD)
    open(os.path.join(PK, 'evaluator.txt'), 'w', encoding='utf-8').write(EVALUATOR_TXT)

    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    pos = {i: xy for i, n, xy in nodes}
    fig = plt.figure(figsize=(14, 8.5), dpi=150)
    ax = fig.add_axes([0.05, 0.07, 0.62, 0.86]); side = fig.add_axes([0.70, 0.07, 0.29, 0.86]); side.axis('off')
    for a, b in edges:
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color='#b0b0b0', lw=1.2, zorder=1)
    for o, cl, nn, xy in objects:
        ax.scatter(*xy, marker='s', s=28, color='#c0602a', zorder=2)
    for i, n, xy in nodes:
        ax.scatter(*xy, s=300, color='#2f5d8a', zorder=3)
        ax.text(xy[0], xy[1], str(i), color='white', ha='center', va='center', fontsize=8, weight='bold', zorder=4)
        ax.text(xy[0] + 0.2, xy[1] + 0.2, n, fontsize=7, color='#1a1a1a', zorder=4, rotation=20)
    ax.set_aspect('equal'); ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)'); ax.grid(alpha=0.2)
    ax.set_title('Route map: nodes (blue, numbered) and fixed objects (orange squares)', fontsize=10)
    by_node = {}
    for o, cl, nn, xy in objects:
        by_node.setdefault(nn, []).append('%s (%s)' % (o, cl))
    lines = ['Fixed objects, by the node they are attached to', '']
    for i, n, xy in nodes:
        if i in by_node:
            lines.append('node %d  %s' % (i, n))
            lines += ['    ' + s for s in by_node[i]]
    side.text(0, 1, '\n'.join(lines), va='top', ha='left', fontsize=8, family='monospace', color='#1a1a1a')
    fig.savefig(os.path.join(PK, 'map.png'), metadata={'Software': None}); plt.close(fig)

    with open(os.path.join(INTERNAL, 'CODE_MAP.csv'), 'w', newline='', encoding='utf-8') as f:
        c = csv.writer(f); c.writerow(['code', 'cell_id'])
        for code, r in items:
            c.writerow([code, r['cell_id']])

    # leak check over every packet file
    # A candidate string is a leak only if it is not already legitimate packet content (instruction texts,
    # node names, object ids and classes): the key is the cell-to-referent association, not the word.
    legit = ' '.join([r['instructiune_en_v2'] for r in sealed] + [n for _, n, _ in nodes] +
                     [o for o, _, _, _ in objects] + [cl for _, cl, _, _ in objects]).lower()
    forbidden = set()
    for r in sealed:
        forbidden.add(r['cell_id'])
        forbidden.add(r['categorie'])
        for k in ('original_ro', 'referent_real'):
            s = r[k].strip()
            if len(s) >= 4 and s.lower() not in legit:
                forbidden.add(s)
    forbidden |= {'acceptabil', 'incorect', 'referent', 'provenien', 'RO-first', 'EN-direct', '17/28', 'sealed', 'yolo', 'YOLO',
                  'stop sign', 'mission_complete', 'L3a', 'L3b', 'VLM'}
    leaks = []
    for name in sorted(os.listdir(PK)):
        if name.endswith('.png'):
            continue
        txt = open(os.path.join(PK, name), encoding='utf-8').read()
        for s in forbidden:
            pat = r'(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])' % re.escape(s)          # whole-token match
            if re.search(pat, txt, flags=0 if re.fullmatch(r'[A-Z]-P?\d', s) else re.I):
                leaks.append((name, s))
    if leaks:
        fail('forbidden content in packet: %s' % leaks[:10])
    expect = {'items.csv': ['code', 'request'],
              'response_form.csv': ['code', 'request', 'acceptable_nodes', 'no_node_appropriate', 'clearly_wrong_nodes', 'confidence', 'comment'],
              'environment_nodes.csv': ['node', 'name', 'x_m', 'y_m'], 'environment_edges.csv': ['node_a', 'node_b'],
              'environment_objects.csv': ['object', 'class', 'attached_node', 'x_m', 'y_m']}
    for name, cols in expect.items():
        if next(csv.reader(open(os.path.join(PK, name), encoding='utf-8'))) != cols:
            fail('unexpected columns in %s' % name)
    if sorted(os.listdir(PK)) != sorted(list(expect) + ['README_EVALUATOR.md', 'evaluator.txt', 'map.png']):
        fail('unexpected file set in packet')

    zpath = os.path.join(HERE, 'packets_blind', PACKET + '.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(PK)):
            zi = zipfile.ZipInfo('%s/%s' % (PACKET, name), date_time=(2026, 10, 4, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, open(os.path.join(PK, name), 'rb').read())
    rec = OrderedDict(script_sha256=sha(os.path.abspath(__file__)), inputs=PINNED, seed=SEED,
                      packet=PACKET, packet_files={n: sha(os.path.join(PK, n)) for n in sorted(os.listdir(PK))},
                      packet_zip_sha256=sha(zpath), code_map_sha256=sha(os.path.join(INTERNAL, 'CODE_MAP.csv')),
                      leak_check=dict(patterns=len(forbidden), hits=0, rule='cell ids, categories, and original_ro / referent_real strings not already legitimate content; column and file-set check'),
                      map_label_decision=('node and object labels given exactly as served on day 2, including node 14 '
                                          'named plant_5 while hosting window_north (plant_5 attached to node 15)'))
    json.dump(rec, open(os.path.join(INTERNAL, 'BUILD_RECORD.json'), 'w', encoding='utf-8'), indent=1)
    print('C3 PACKET BUILT: %d items, %d nodes, %d edges, %d objects; leak check 0/%d; zip %s' % (
        len(items), len(nodes), len(edges), len(objects), len(forbidden), rec['packet_zip_sha256'][:16]))


if __name__ == '__main__':
    main()
