"""
Generate summary charts for the project README.
Reads only safe aggregate data (no drug names).
Outputs: results/charts/pipeline_overview.png
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

BASE = Path(__file__).parent.parent

C_TEAL    = "#0a9396"
C_LIGHT   = "#94d2bd"
C_ORANGE  = "#ca6702"
C_RED     = "#ae2012"
C_GRAY    = "#adb5bd"
C_BG      = "#f8f9fa"
C_DARK    = "#212529"

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.patch.set_facecolor(C_BG)

# ─── LEFT: Drug Processing Funnel ─────────────────────────────────────────────
ax = axes[0]
ax.set_facecolor(C_BG)

cov_df = pd.read_csv(BASE / "results/substitution_research/01_preparation/coverage_analysis.csv",
                     index_col="METRIC")["VALUE"]
filt_df = pd.read_csv(BASE / "results/substitution_research/02_statistics_and_filter/"
                              "02_02_valid_data_filter/filter_summary.csv",
                       index_col="METRIC")["VALUE"]

raw        = int(float(cov_df["TOTAL_DRUGS_RAW"]))
researched = int(float(cov_df["TOTAL_DRUGS_RESEARCHED"]))
valid      = int(float(filt_df["VALID_DRUGS"]))
rej_cov    = int(float(filt_df["REJECTED_COVERAGE_ONLY"]))
rej_rel    = int(float(filt_df["REJECTED_RELIABILITY_ONLY"]))
rej_both   = int(float(filt_df["REJECTED_BOTH"]))

stages = [
    (raw,        "Raw drugs\nin data",         C_GRAY,  None,       None),
    (researched, "DiD analysis\ncompleted",     C_LIGHT, raw,        "of raw"),
    (valid,      "Passed quality\nfilter",      C_TEAL,  researched, "of researched"),
]

bar_h   = 0.55
y_pos   = [2.4, 1.4, 0.4]
max_val = raw

for (val, label, color, denom, denom_label), y in zip(stages, y_pos):
    width = val / max_val
    ax.barh(y, width, height=bar_h, color=color, linewidth=0,
            left=(1 - width) / 2, zorder=3)
    ax.text(0.5, y, f"{val:,}", ha="center", va="center",
            fontsize=18, fontweight="bold", color=C_DARK, zorder=4)
    ax.text(1.05, y, label, ha="left", va="center",
            fontsize=11, color=C_DARK, linespacing=1.4)
    if denom is not None:
        pct = val / denom * 100
        ax.text(-0.06, y, f"{pct:.0f}%\n{denom_label}", ha="right", va="center",
                fontsize=10, color=C_DARK, fontstyle="italic", linespacing=1.3)
    else:
        ax.text(-0.06, y, "input", ha="right", va="center",
                fontsize=10, color=C_DARK, fontstyle="italic")

ax.set_xlim(-0.15, 1.6)
ax.set_ylim(-0.3, 3.2)
ax.axis("off")

ax.text(0.5, 3.0, "Data Processing Funnel", ha="center", va="center",
        fontsize=14, fontweight="bold", color=C_DARK, transform=ax.transData)

# Rejection breakdown
ax.text(0.5, -0.15, "Rejected drugs:", ha="center", fontsize=10,
        color=C_DARK, fontstyle="italic", transform=ax.transData)
legend_items = [
    mpatches.Patch(color="#e76f51", label=f"Coverage too low — {rej_cov} drugs"),
    mpatches.Patch(color="#f4a261", label=f"Reliability too low — {rej_rel} drugs"),
    mpatches.Patch(color="#264653", label=f"Both criteria failed — {rej_both} drugs"),
]
ax.legend(handles=legend_items, loc="lower center", fontsize=9,
          frameon=False, ncol=1, bbox_to_anchor=(0.5, -0.28))

# ─── RIGHT: Parallel Speedup ──────────────────────────────────────────────────
ax2 = axes[1]
ax2.set_facecolor(C_BG)

times   = [23.0, 7.0833]
labels  = ["Sequential\n(1 process)", "Parallel\n(4 workers)"]
colors  = [C_GRAY, C_TEAL]
bars    = ax2.bar(labels, times, color=colors, width=0.45, zorder=3,
                  linewidth=0)

for bar, val in zip(bars, times):
    mins = int(val)
    secs = round((val - mins) * 60)
    if secs:
        txt = f"{mins} min {secs} sec"
    else:
        txt = f"~{mins} min"
    ax2.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() + 0.3,
             txt, ha="center", va="bottom",
             fontsize=13, fontweight="bold", color=C_DARK)

ax2.annotate("", xy=(1, 7.5), xytext=(0, 21.5),
             arrowprops=dict(arrowstyle="->", color=C_ORANGE, lw=2.5))
ax2.text(0.58, 14.5, "3.3×\nspeedup", ha="center", fontsize=15,
         fontweight="bold", color=C_ORANGE)

ax2.set_ylabel("Runtime (minutes)", fontsize=12, color=C_DARK, labelpad=10)
ax2.set_ylim(0, 27)
ax2.set_facecolor(C_BG)
ax2.spines[["top", "right"]].set_visible(False)
ax2.spines[["left", "bottom"]].set_color(C_GRAY)
ax2.tick_params(colors=C_DARK, labelsize=12)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)} min"))
ax2.set_title("Parallel Processing Speedup\n(ProcessPoolExecutor × 4 workers)",
              fontsize=14, fontweight="bold", color=C_DARK, pad=14)

for spine in ax2.spines.values():
    spine.set_linewidth(0.8)

plt.tight_layout(pad=2.5)

out = BASE / "results/charts/pipeline_overview.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=C_BG)
print(f"Saved: {out}")
