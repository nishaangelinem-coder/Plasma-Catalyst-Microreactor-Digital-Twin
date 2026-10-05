"""IEEE two-column figure style (3.5 in single / 7.16 in double column, 8 pt labels)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .platforms import PLATFORM_COLORS, PLATFORM_MARKERS, PLATFORM_LS, PLATFORMS, PLATFORM_ORDER

COL1, COL2 = 3.5, 7.16
DEVICE_COLOR = {"gaa_n": "#0072B2", "gaa_p": "#56B4E9", "sige_p": "#009E73", "mos2_n": "#D55E00",
                "wse2_p": "#E69F00", "cnt_n": "#CC79A7", "cnt_p": "#882255", "gan_n": "#E69F00", "gan_p": "#999933"}
DEVICE_LABEL = {"gaa_n": "Si GAA n", "gaa_p": "Si GAA p", "sige_p": "SiGe GAA p", "mos2_n": "MoS$_2$ n",
                "wse2_p": "WSe$_2$ p", "cnt_n": "CNT n", "cnt_p": "CNT p", "gan_n": "GaN n", "gan_p": "p-GaN (proj.)"}
LABEL = {k: PLATFORMS[k]["name"] for k in PLATFORM_ORDER}
COLOR, MARKER, LS = PLATFORM_COLORS, PLATFORM_MARKERS, PLATFORM_LS

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Nimbus Sans", "DejaVu Sans"],
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5, "legend.fontsize": 7, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "axes.linewidth": 0.6, "lines.linewidth": 1.2, "lines.markersize": 4,
    "legend.frameon": False, "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.5,
    "axes.edgecolor": "#898781", "xtick.color": "#52514e", "ytick.color": "#52514e", "axes.labelcolor": "#0b0b0b",
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "figure.dpi": 100,
    "mathtext.default": "regular",
})


def panel_label(ax, s, x=0.02, y=0.97):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=8.5, fontweight="bold", va="top", ha="left")


def save(fig, name):
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(here, "figures", f"{name}.{ext}"))
    plt.close(fig)
    print("saved figures/" + name + ".png/.pdf")
