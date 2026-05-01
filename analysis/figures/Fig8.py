"""Figure 8 — Learning cycle: L3b VLM inference times for S3new on Xplorer-C.
7 decisions with correct/incorrect nodes and M3 promotion threshold.

Reads data from: data/session_a/audits/*.jsonl
Elsevier-compliant: 140 mm, 600 DPI, Times New Roman.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
from matplotlib.patches import Patch
from data_loader import load_all_sessions, get_scenario_decisions

DPI = 600
fig_w = 140 / 25.4
fig_h = fig_w * 0.55

plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 7, 'axes.labelsize': 8, 'axes.titlesize': 8,
    'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 6.5,
    'figure.dpi': DPI, 'savefig.dpi': DPI, 'axes.linewidth': 0.5,
    'xtick.major.width': 0.4, 'ytick.major.width': 0.4,
})

# --- Load from audit logs ---
sessions = load_all_sessions()
s3new_vlm = [d for d in get_scenario_decisions(sessions['a'], 'S3new')
             if d.get('resolution_method') == 'L3b_vlm']

decisions = list(range(1, len(s3new_vlm) + 1))
vlm_ms = [d['timing']['vlm_ms'] for d in s3new_vlm]
nodes = [d['node_id'] for d in s3new_vlm]
dominant_node = Counter(nodes).most_common(1)[0][0]
correct = [n == dominant_node for n in nodes]
consistency = sum(correct) / len(correct)

# --- Plot ---
fig, ax = plt.subplots(figsize=(fig_w, fig_h))

c_correct = '#3B7DD8'
c_incorrect = '#D44B3F'

colors = [c_correct if c else c_incorrect for c in correct]
bars = ax.bar(decisions, [t / 1000 for t in vlm_ms], width=0.55,
              color=colors,
              edgecolor=[c if c == c_incorrect else '#1A5276' for c in colors],
              linewidth=0.5, zorder=3)

for i, bar in enumerate(bars):
    if not correct[i]:
        bar.set_hatch('xxx')

mean_s = np.mean(vlm_ms) / 1000
ax.axhline(y=mean_s, color='#333333', linestyle='--', linewidth=0.7, zorder=2)
ax.text(len(decisions) + 0.6, mean_s + 0.15, f'mean = {mean_s:.1f} s',
        fontsize=6.5, va='bottom', ha='right', color='#333333')

for i, (d, n, t) in enumerate(zip(decisions, nodes, vlm_ms)):
    color = c_incorrect if n != dominant_node else '#1A5276'
    ax.text(d, t / 1000 + 0.25, f'n{n}', ha='center', va='bottom',
            fontsize=6, color=color, fontweight='bold' if n != dominant_node else 'normal')

ax.set_xlabel('L3b decision (chronological)')
ax.set_ylabel('VLM inference time (s)')
ax.set_xticks(decisions)
ax.set_xlim(0.3, len(decisions) + 1.0)
ax.set_ylim(0, max(vlm_ms) / 1000 + 1.5)
ax.yaxis.grid(True, which='major', linestyle='-', linewidth=0.25, color='#CCCCCC')
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ann = (f'Consistency: {sum(correct)}/{len(correct)} = {consistency:.2f} '
       f'(threshold $\\geq$ 0.80)\nResult: promoted to M3 digest')
ax.text(0.03, 0.03, ann, transform=ax.transAxes, fontsize=6, va='bottom',
        ha='left', color='#333333',
        bbox=dict(boxstyle='round,pad=0.25', facecolor='#F0F7F0',
                  edgecolor='#AAAAAA', linewidth=0.4, alpha=0.95))

incorrect_nodes = set(n for n, c in zip(nodes, correct) if not c)
legend_elements = [
    Patch(facecolor=c_correct, edgecolor='#1A5276', linewidth=0.5,
          label=f'Correct (node {dominant_node})'),
    Patch(facecolor=c_incorrect, edgecolor=c_incorrect, linewidth=0.5,
          hatch='xxx', label=f'Incorrect (node {", ".join(str(n) for n in incorrect_nodes)})'),
]
ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.14),
          frameon=True, framealpha=0.95, edgecolor='#CCCCCC',
          borderpad=0.3, handlelength=1.2, handletextpad=0.4,
          columnspacing=1.0, ncol=2)

plt.subplots_adjust(bottom=0.22)
for fmt in ['pdf', 'tiff', 'eps', 'png']:
    kwargs = {'pil_kwargs': {'compression': 'tiff_lzw'}} if fmt == 'tiff' else {}
    fig.savefig(f'Fig8_learning_cycle.{fmt}', dpi=DPI, bbox_inches='tight', format=fmt, **kwargs)
print(f'Fig8: {len(s3new_vlm)} L3b decisions, consistency={consistency:.2f}, mean={mean_s:.1f}s')
plt.close()
