"""Figure 9 — L3a resolve times on Xplorer-B grouped by category.
Seed-promoted M3 | Learning-cycle M3 | Deterministic control.

Reads data from: data/session_b/audits/*.jsonl
Elsevier-compliant: 140 mm, 600 DPI.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from data_loader import load_all_sessions, get_scenario_decisions, get_resolve_times

DPI = 600
fig_w = 140 / 25.4
fig_h = fig_w * 0.55

plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 7, 'axes.labelsize': 8, 'axes.titlesize': 8,
    'xtick.labelsize': 7, 'ytick.labelsize': 7, 'legend.fontsize': 6.5,
    'figure.dpi': DPI, 'savefig.dpi': DPI, 'axes.linewidth': 0.5,
    'xtick.major.width': 0.4, 'ytick.major.width': 0.4,
    'xtick.minor.width': 0.3, 'ytick.minor.width': 0.3,
})

# --- Load from audit logs ---
sessions = load_all_sessions()
b = sessions['b']

seed_s1 = get_resolve_times(get_scenario_decisions(b, 'S1'))
seed_s2 = get_resolve_times(get_scenario_decisions(b, 'S2'))
seed_s3old = get_resolve_times(get_scenario_decisions(b, 'S3old'))
s3new_b = get_resolve_times(get_scenario_decisions(b, 'S3new'))
s4 = get_resolve_times(get_scenario_decisions(b, 'S4'))
s5 = get_resolve_times(get_scenario_decisions(b, 'S5'))

m3_all = seed_s1 + seed_s2 + seed_s3old + s3new_b
det_all = s4 + s5

# --- Plot ---
fig, ax = plt.subplots(figsize=(fig_w, fig_h))
data = [seed_s1, seed_s2, seed_s3old, s3new_b, s4, s5]
positions = [1, 2, 3, 4.5, 6, 7]

bp = ax.boxplot(
    data, positions=positions, widths=0.45, patch_artist=True,
    medianprops=dict(color='black', linewidth=1.2),
    whiskerprops=dict(linewidth=0.7), capprops=dict(linewidth=0.7),
    flierprops=dict(marker='o', markersize=3, markerfacecolor='none',
                    markeredgecolor='#555555', markeredgewidth=0.5),
    showmeans=True,
    meanprops=dict(marker='D', markerfacecolor='#D32F2F',
                   markeredgecolor='#D32F2F', markersize=3.5),
)

face_colors = ['#BBDEFB', '#BBDEFB', '#BBDEFB', '#64B5F6', '#C8E6C9', '#C8E6C9']
edge_colors = ['#1565C0', '#1565C0', '#1565C0', '#0D47A1', '#2E7D32', '#2E7D32']
hatch_styles = ['', '', '', '///', 'xxx', 'xxx']
for patch, fc, ec, h in zip(bp['boxes'], face_colors, edge_colors, hatch_styles):
    patch.set_facecolor(fc); patch.set_edgecolor(ec); patch.set_linewidth(0.8)
    if h: patch.set_hatch(h)

ax.set_yscale('log')
ax.set_yticks([0.04, 0.05, 0.06, 0.08, 0.10, 0.20, 0.40, 0.60])
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.2f}'))
ax.yaxis.set_minor_formatter(mticker.NullFormatter())
ax.set_ylim(0.035, 0.65)
ax.set_ylabel('Resolution time (ms)')
ax.yaxis.grid(True, which='major', linestyle='-', linewidth=0.3, color='#CCCCCC')
ax.set_axisbelow(True)

labels = [
    f'S1\nrestroom\n($n$={len(seed_s1)})',
    f'S2\nfire safety\n($n$={len(seed_s2)})',
    f'S3$_{{old}}$\nfresh air\n($n$={len(seed_s3old)})',
    f'S3$_{{new}}$\nsit & relax\n($n$={len(s3new_b)})',
    f'S4\nlab_cb204\n($n$={len(s4)})',
    f'S5\nclosest plant\n($n$={len(s5)})',
]
ax.set_xticks(positions)
ax.set_xticklabels(labels, fontsize=6.5, linespacing=1.15)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax.axvline(x=3.75, color='#888888', linestyle='--', linewidth=0.5, zorder=0)
ax.axvline(x=5.25, color='#888888', linestyle='--', linewidth=0.5, zorder=0)

y_label = 0.58
ax.text(2.0, y_label, 'Seed-promoted M3 (Step 0)', ha='center', va='bottom',
        fontsize=6.5, color='#1565C0', fontweight='bold')
ax.text(4.5, y_label, 'Learning-\ncycle M3', ha='center', va='bottom',
        fontsize=6.5, color='#0D47A1', fontweight='bold', linespacing=0.9)
ax.text(6.5, y_label, 'Deterministic\n(Steps 2, 6)', ha='center', va='bottom',
        fontsize=6.5, color='#2E7D32', fontweight='bold', linespacing=0.9)

ann = (f'M3 accuracy: {len(m3_all)}/{len(m3_all)} (100%)    '
       f'mean$_{{M3}}$ = {np.mean(m3_all):.3f} ms    '
       f'mean$_{{det}}$ = {np.mean(det_all):.3f} ms')
ax.text(0.02, 0.02, ann, transform=ax.transAxes, fontsize=6, va='bottom',
        color='#333333', bbox=dict(boxstyle='round,pad=0.3', facecolor='#F5F5F5',
                                   edgecolor='#CCCCCC', linewidth=0.4, alpha=0.95))

legend_elements = [
    Patch(facecolor='#BBDEFB', edgecolor='#1565C0', linewidth=0.7,
          label='Seed-promoted M3 (S1, S2, S3$_{old}$)'),
    Patch(facecolor='#64B5F6', edgecolor='#0D47A1', linewidth=0.7,
          hatch='///', label='Learning-cycle M3 (S3$_{new}$)'),
    Patch(facecolor='#C8E6C9', edgecolor='#2E7D32', linewidth=0.7,
          hatch='xxx', label='Deterministic control (S4, S5)'),
    Line2D([0], [0], marker='D', color='#D32F2F', linestyle='None',
           markersize=3.5, label='Mean'),
]
ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.18),
          frameon=True, framealpha=0.95, edgecolor='#CCCCCC',
          borderpad=0.3, handlelength=1.2, handletextpad=0.4,
          columnspacing=0.8, ncol=4, fontsize=6)

plt.subplots_adjust(bottom=0.25)
for fmt in ['pdf', 'tiff', 'eps', 'png']:
    kwargs = {'pil_kwargs': {'compression': 'tiff_lzw'}} if fmt == 'tiff' else {}
    fig.savefig(f'Fig9_resolve_times.{fmt}', dpi=DPI, bbox_inches='tight', format=fmt, **kwargs)
print(f'Fig9: M3={len(m3_all)}, Det={len(det_all)}, mean_M3={np.mean(m3_all):.3f}, mean_Det={np.mean(det_all):.3f}')
plt.close()
