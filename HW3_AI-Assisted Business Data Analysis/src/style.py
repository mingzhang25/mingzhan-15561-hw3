"""Shared matplotlib style, colour palette and chart helpers."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Validated categorical palette (fixed order) and chart chrome.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE, ORANGE, AQUA = SERIES[0], SERIES[1], SERIES[2]
MUTED_FILL = "#c3c2b7"
CRITICAL = "#d03b3b"
INK, INK_2, INK_MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def apply_style():
    """Set global matplotlib defaults for all project charts.

    Args:
        None.

    Returns:
        None. Updates ``matplotlib.pyplot.rcParams`` in place.
    """
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "axes.edgecolor": AXIS,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelcolor": INK_2,
        "ytick.labelcolor": INK_2,
        "legend.frameon": False,
        "lines.linewidth": 2,
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
    })


def money(x, _pos=None):
    """Format a dollar amount as a short axis label.

    Args:
        x (float): Amount in USD.
        _pos (int | None): Tick position passed by ``FuncFormatter``;
            unused.

    Returns:
        str: ``"$12k"`` style when ``abs(x)`` is 1,000 or more,
            otherwise ``"$950"`` style.
    """
    if abs(x) >= 1000:
        return f"${x / 1000:,.0f}k"
    return f"${x:,.0f}"


def save(fig, path):
    """Save a figure to disk and close it.

    Args:
        fig (matplotlib.figure.Figure): Figure to save.
        path (pathlib.Path): Output image file; overwritten if present.

    Returns:
        None. Writes ``path`` and closes ``fig``.
    """
    fig.savefig(path)
    plt.close(fig)
