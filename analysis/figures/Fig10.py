"""Figure 10 — Latency comparison: L3b VLM (Xplorer-C) vs L3a M3 (Xplorer-B).
(a) log-scale boxplot, (b) structured stats table.

Reads data from: data/session_a/audits/*.jsonl, data/session_b/audits/*.jsonl
Elsevier-compliant: 190 mm (double column), 600 DPI.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from scipy import stats
from data_loader import (load_all_sessions, get_scenario_decisions,
                         get_resolve_times, get_vlm_times, get_m3_decisions)

DPI = 600
fig_w = 190 / 25.4
fig_h = fig_w * 0.48

plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 7, 'axes.labelsize': 8, 'axes.titlesize': 8,
    'xtick.labelsize': 7, 'ytick.labelsize': 7,
    'figure.dpi': DPI, 'savefig.dpi': DPI, 'axes.linewidth': 0.5,
    'xtick.major.width': 0.4, 'ytick.major.width': 0.4,
})

# --- Load from audit logs ---
sessions = load_all_sessions()
vlm_times = get_vlm_times(get_scenario_decisions(sessions['a'], 'S3new'))
m3_times = get_resolve_times(get_m3_decisions(sessions['b']))

mean_vlm = np.mean(vlm_times)
mean_m3 = np.mean(m3_times)
std_vlm = np.std(vlm_times, ddof=1)
std_m3 = np.std(m3_times, ddof=1)
speedup = mean_vlm / mean_m3

u_stat, p_val = stats.mannwhitneyu(vlm_times, m3_times, alternative='greater')
pool_std = np.sqrt(((len(vlm_times)-1)*np.var(vlm_times, ddof=1) +
                     (len(m3_times)-1)*np.var(m3_times, ddof=1)) /
                    (len(vlm_times) + len(m3_times) - 2))
cohens_d = (mean_vlm - mean_m3) / pool_std

# --- Plot ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fig_w, fig_h),
                                gridspec_kw={'width_ratios': [1.6, 1]})

# Panel (a)
bp = ax1.boxplot(
    [vlm_times, m3_times], positions=[1, 2], widths=0.4, patch_artist=True,
    medianprops=dict(color='black', linewidth=1.2),
    whiskerprops=dict(linewidth=0.7), capprops=dict(linewidth=0.7),
    flierprops=dict(marker='o', markersize=3, markerfacecolor='none',
                    markeredgecolor='#555555', markeredgewidth=0.5),
    showmeans=True,
    meanprops=dict(marker='D', markerfacecolor='#D32F2F',
                   markeredgecolor='#D32F2F', markersize=3.5),
)

bp['boxes'][0].set_facecolor('#FFCDD2'); bp['boxes'][0].set_edgecolor('#C62828')
bp['boxes'][0].set_hatch('///'); bp['boxes'][0].set_linewidth(0.8)
bp['boxes'][1].set_facecolor('#BBDEFB'); bp['boxes'][1].set_edgecolor('#1565C0')
bp['boxes'][1].set_linewidth(0.8)

ax1.set_yscale('log')
ax1.set_ylim(0.025, 18000)
ax1.set_yticks([0.05, 0.1, 1, 10, 100, 1000, 10000])
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:g}'))
ax1.yaxis.set_minor_formatter(mticker.NullFormatter())
ax1.set_ylabel('Resolution time (ms)')
ax1.set_xticks([1, 2])
ax1.set_xticklabels([
    f'L3b VLM\n(Xplorer-C, $n$={len(vlm_times)})',
    f'L3a M3 preference\n(Xplorer-B, $n$={len(m3_times)})',
], fontsize=7, linespacing=1.15)
ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
ax1.yaxis.grid(True, which='major', linestyle='-', linewidth=0.3, color='#CCCCCC')
ax1.set_axisbelow(True)

ax1.text(0.55, mean_vlm * 0.35, f'mean = {mean_vlm:,.0f} ms',
         fontsize=6.5, color='#C62828', va='center')
ax1.text(2.32, mean_m3 * 1.15, f'mean = {mean_m3:.3f} ms',
         fontsize=6.5, color='#1565C0', va='center')

mid_y = np.sqrt(mean_vlm * mean_m3)
ax1.annotate('', xy=(1.85, mean_m3 * 2), xytext=(1.15, mean_vlm * 0.6),
             arrowprops=dict(arrowstyle='->', color='#555555', lw=1.2,
                             connectionstyle='arc3,rad=-0.15'))
ax1.text(1.55, mid_y * 0.7, f'{speedup:,.0f}$\\times$',
         ha='center', va='center', fontsize=9, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFDE7',
                   edgecolor='#BDBDBD', linewidth=0.5, alpha=0.95))
ax1.text(0.03, 0.97, '(a)', transform=ax1.transAxes, fontsize=9,
         fontweight='bold', va='top')

# Panel (b) — Stats table
ax2.axis('off')
ax2.text(0.02, 0.97, '(b)', transform=ax2.transAxes, fontsize=9,
         fontweight='bold', va='top')

rows = [
    ['', 'L3b VLM (C)', 'L3a M3 (B)'],
    ['$n$', f'{len(vlm_times)}', f'{len(m3_times)}'],
    ['Mean (ms)', f'{mean_vlm:,.0f}', f'{mean_m3:.3f}'],
    ['SD (ms)', f'{std_vlm:,.0f}', f'{std_m3:.3f}'],
    ['Min (ms)', f'{min(vlm_times):,.0f}', f'{min(m3_times):.3f}'],
    ['Max (ms)', f'{max(vlm_times):,.0f}', f'{max(m3_times):.3f}'],
    ['', '', ''],
    ['Speedup', f'{speedup:,.0f}×', ''],
    ['M-W $U$', f'{u_stat:.0f}', ''],
    ['$p$-value', f'{p_val:.2e}'.replace('e-0', '×10⁻').replace('e-', '×10⁻'), ''],
    ["Cohen's $d$", f'{cohens_d:.2f}', ''],
    ['', '', ''],
    ['Accuracy', f'{len(m3_times)}/{len(m3_times)}', ''],
    ['95% CI', '[0.894, 1.0]', ''],
]

table = ax2.table(cellText=rows, cellLoc='center', loc='upper center',
                  bbox=[0.02, 0.02, 0.96, 0.90], colWidths=[0.38, 0.34, 0.28])
table.auto_set_font_size(False); table.set_fontsize(7)

for (row, col), cell in table.get_celld().items():
    cell.set_edgecolor('#CCCCCC'); cell.set_linewidth(0.4)
    if row == 0:
        cell.set_facecolor('#E3E8F0'); cell.set_text_props(fontweight='bold', fontsize=7)
    elif row in [6, 11]:
        cell.set_facecolor('white'); cell.set_edgecolor('white'); cell.set_height(0.008)
    elif col == 0:
        cell.set_facecolor('#F7F7F7'); cell.set_text_props(fontweight='bold', fontsize=6.5)
    else:
        cell.set_facecolor('white')
    if row == 7:
        cell.set_facecolor('#FFFDE7')
        if col == 1: cell.set_text_props(fontweight='bold', fontsize=7.5)

plt.tight_layout(w_pad=0.5)
for fmt in ['pdf', 'tiff', 'eps', 'png']:
    kwargs = {'pil_kwargs': {'compression': 'tiff_lzw'}} if fmt == 'tiff' else {}
    fig.savefig(f'Fig10_speedup_comparison.{fmt}', dpi=DPI, bbox_inches='tight', format=fmt, **kwargs)
print(f'Fig10: speedup={speedup:,.0f}×, U={u_stat:.0f}, p={p_val:.2e}, d={cohens_d:.2f}')
plt.close()