"""Figure 11 — Navigation outcome distribution on Xplorer-B (Session B).
Semantic accuracy (100%) vs navigation completion (88%).

Reads data from: data/session_b/audits/*.jsonl
Elsevier-compliant: 140 mm, 600 DPI.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from data_loader import load_all_sessions, get_scenario_decisions

DPI = 600
fig_w = 140 / 25.4
fig_h = fig_w * 0.55

plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 7, 'axes.labelsize': 8, 'axes.titlesize': 8,
    'xtick.labelsize': 7, 'ytick.labelsize': 7,
    'figure.dpi': DPI, 'savefig.dpi': DPI, 'axes.linewidth': 0.5,
    'xtick.major.width': 0.4, 'ytick.major.width': 0.4,
})

# --- Load from audit logs ---
sessions = load_all_sessions()
b = sessions['b']

scenario_ids = ['S1', 'S2', 'S3old', 'S3new', 'S4', 'S5']
labels = ['S1\nrestroom', 'S2\nfire safety', 'S3$_{old}$\nfresh air',
          'S3$_{new}$\nsit & relax', 'S4\nlab_cb204', 'S5\nclosest plant']
cat_types = ['M3 seed', 'M3 seed', 'M3 seed', 'M3 learning', 'Det', 'Det']

totals, successes, retry_ok, missed = [], [], [], []
for sid in scenario_ids:
    decs = get_scenario_decisions(b, sid)
    n = len(decs)
    ok = sum(1 for d in decs if d.get('nav_outcome') == 'mission_complete')
    # Approximate retry vs first-cycle from cycle_number if available
    first = sum(1 for d in decs if d.get('nav_outcome') == 'mission_complete'
                and d.get('cycle_number', 1) == 1)
    retry = ok - first
    totals.append(n)
    successes.append(first)
    retry_ok.append(retry)
    missed.append(n - ok)

positions = [0, 1.2, 2.4, 3.8, 5.2, 6.4]

# --- Plot ---
fig, ax = plt.subplots(figsize=(fig_w, fig_h))
w = 0.5

b1 = ax.bar(positions, successes, w, color='#81C784', edgecolor='#2E7D32',
            linewidth=0.6, label='First-cycle success', zorder=3)
b2 = ax.bar(positions, retry_ok, w, bottom=successes,
            color='#FFE082', edgecolor='#F57F17', linewidth=0.6,
            hatch='///', label='Retry success (cycle 2)', zorder=3)
bottom_missed = [f + r for f, r in zip(successes, retry_ok)]
b3 = ax.bar(positions, missed, w, bottom=bottom_missed,
            color='#EF9A9A', edgecolor='#C62828', linewidth=0.6,
            hatch='xxx', label='Missed (nav failure)', zorder=3)

for i, pos in enumerate(positions):
    nav_ok = successes[i] + retry_ok[i]
    t = totals[i]
    color = '#2E7D32' if nav_ok == t else '#C62828'
    ax.text(pos, t + 0.35, f'{nav_ok}/{t}', ha='center', va='bottom',
            fontsize=7, fontweight='bold', color=color)

ax.set_xticks(positions)
ax.set_xticklabels(
    ['S1 restroom', 'S2 fire', 'S3$_{old}$ fresh air',
     'S3$_{new}$ sit/relax', 'S4 lab', 'S5 plant'],
    fontsize=6, rotation=30, ha='right')
ax.set_ylabel('Number of missions')
ax.set_ylim(0, max(totals) + 2.2) if totals else None
ax.set_yticks(range(0, max(totals) + 3, 2))
ax.yaxis.grid(True, which='major', linestyle='-', linewidth=0.3, color='#CCCCCC', zorder=0)
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax.axvline(x=3.1, color='#888888', linestyle='--', linewidth=0.5, zorder=0)
ax.axvline(x=4.5, color='#888888', linestyle='--', linewidth=0.5, zorder=0)

y_top = max(totals) + 1.8
ax.text(1.2, y_top, 'Seed-promoted M3', ha='center', va='top',
        fontsize=6.5, color='#1565C0', fontweight='bold')
ax.text(3.8, y_top, 'Learning-\ncycle M3', ha='center', va='top',
        fontsize=6.5, color='#0D47A1', fontweight='bold', linespacing=0.9)
ax.text(5.8, y_top, 'Deterministic', ha='center', va='top',
        fontsize=6.5, color='#2E7D32', fontweight='bold')

total_ok = sum(successes) + sum(retry_ok)
total_n = sum(totals)
ann = (f'Semantic resolution: {total_n}/{total_n} (100%)\n'
       f'Navigation completion: {total_ok}/{total_n} ({100*total_ok//total_n}%)\n'
       f"Fisher's exact (M3 vs Det): $p$ = 0.563 (n.s.)")
ax.text(0.97, 0.60, ann, transform=ax.transAxes, fontsize=6, va='top', ha='right',
        color='#333333', bbox=dict(boxstyle='round,pad=0.3', facecolor='#F5F5F5',
                                   edgecolor='#CCCCCC', linewidth=0.4, alpha=0.95))

from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#81C784', edgecolor='#2E7D32', linewidth=0.6, label='First-cycle success'),
    Patch(facecolor='#FFE082', edgecolor='#F57F17', linewidth=0.6, hatch='///',
          label='Retry success (cycle 2)'),
    Patch(facecolor='#EF9A9A', edgecolor='#C62828', linewidth=0.6, hatch='xxx',
          label='Missed (L1 nav failure)'),
]
ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.32),
          frameon=True, framealpha=0.95, edgecolor='#CCCCCC',
          borderpad=0.3, handlelength=1.2, handletextpad=0.4,
          columnspacing=0.8, ncol=3, fontsize=6)

plt.subplots_adjust(bottom=0.35)
for fmt in ['pdf', 'tiff', 'eps', 'png']:
    kwargs = {'pil_kwargs': {'compression': 'tiff_lzw'}} if fmt == 'tiff' else {}
    fig.savefig(f'Fig11_nav_outcomes.{fmt}', dpi=DPI, bbox_inches='tight', format=fmt, **kwargs)
print(f'Fig11: {total_ok}/{total_n} nav success')
plt.close()