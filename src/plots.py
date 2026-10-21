"""Plot helpers: one simple style for all charts (colors from a validated palette, light surface)."""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "screenshots"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"    # series 1
ORANGE = "#eb6834"  # series 2
# One-hue sequential ramp (light = low, dark = high)
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])


def setup():
    """Set the global matplotlib style."""
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "text.color": INK,
        "xtick.color": INK_2, "ytick.color": INK_2, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.axisbelow": True, "font.size": 10,
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "legend.frameon": False, "figure.dpi": 110,
    })


def finish(fig, title, takeaway, filename=None):
    """Add a title and a one-line takeaway, then save a PNG in screenshots/."""
    fig.suptitle(title, x=0.01, y=0.985, ha="left", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.01, 0.925, takeaway, ha="left", va="top", fontsize=10, color=INK_2)
    fig.tight_layout(rect=[0, 0, 1, 0.89])
    if filename:
        SHOTS.mkdir(exist_ok=True)
        fig.savefig(SHOTS / filename, dpi=150)
    plt.show()


def annotate_heatmap(ax, data, fmt="{:.0f}", threshold=None):
    """Write the value in each heatmap cell. White text on dark cells, dark text on light cells."""
    import numpy as np

    values = np.asarray(data, dtype=float)
    finite = values[np.isfinite(values)]
    threshold = threshold if threshold is not None else (finite.min() + finite.max()) / 2
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            v = values[i, j]
            if np.isfinite(v):
                ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=8,
                        color="white" if v > threshold else INK)
