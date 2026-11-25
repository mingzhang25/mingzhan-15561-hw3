"""Q2: Do discounts buy extra volume, or just give away revenue?"""
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from data import FIG_DIR, TABLE_DIR
from style import BLUE, INK_2, INK_MUTED, MUTED_FILL, money, save

# Standard discount tiers are 5/10/15/20/25%. Eight lines carry odd 1-6%
# discounts; they are grouped with the 5% tier ("1-6%").
BINS = [-0.001, 0.0, 0.075, 0.125, 0.175, 0.225, 0.30]
LABELS = ["0%", "1-6%", "10%", "15%", "20%", "25%"]
CAP = 0.10  # what-if: cap all discounts at 10%


def add_band(lines):
    """Add a discount-tier column to order lines.

    Args:
        lines (pandas.DataFrame): Order lines with a ``Discount``
            column as a fraction (0-1).

    Returns:
        pandas.DataFrame: Copy of ``lines`` with a categorical
            ``DiscountBand`` (``"0%"``, ``"1-6%"``, ..., ``"25%"``).
    """
    return lines.assign(DiscountBand=pd.cut(lines["Discount"], BINS, labels=LABELS))


def band_table(lines):
    """Summarise quantity and discount dollars by discount tier.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``data.build_order_lines``.

    Returns:
        pandas.DataFrame: One row per tier: line count, median and
            mean quantity, gross revenue and discount given (USD),
            and share of all discount dollars (%).
    """
    g = add_band(lines).groupby("DiscountBand", observed=True)
    t = g.agg(
        Lines=("OrderID", "size"),
        Median_qty=("Quantity", "median"),
        Mean_qty=("Quantity", "mean"),
        Gross_revenue=("GrossRevenue", "sum"),
        Discount_given=("DiscountAmount", "sum"),
    )
    t["Share_of_discount_$_%"] = t["Discount_given"] / t["Discount_given"].sum() * 100
    return t


def cap_whatif(lines, cap=CAP):
    """Estimate discount dollars kept if discounts were capped.

    Assumes quantities would not change, so the result is an upper
    bound.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``data.build_order_lines``.
        cap (float): Maximum discount as a fraction (0.10 = 10%).

    Returns:
        tuple[float, int]: USD saved by cutting every discount above
            ``cap`` down to ``cap``, and the number of order lines
            affected.
    """
    over = lines[lines["Discount"] > cap]
    saved = (over["GrossRevenue"] * (over["Discount"] - cap)).sum()
    return saved, len(over)


def customer_table(lines, orders):
    """Summarise discounts received by each customer.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``data.build_order_lines``.
        orders (pandas.DataFrame): Orders from ``data.build_orders``;
            unused.

    Returns:
        pandas.DataFrame: One row per ``CustomerID``: gross revenue,
            discount and net revenue (USD), distinct orders, and
            discount as % of gross.
    """
    c = lines.groupby("CustomerID").agg(
        Gross=("GrossRevenue", "sum"), Discount=("DiscountAmount", "sum"),
        Revenue=("Revenue", "sum"), Orders=("OrderID", "nunique"))
    c["Discount_rate_%"] = c["Discount"] / c["Gross"] * 100
    return c


def plot_quantity(lines, path):
    """Box-plot units per order line for each discount tier.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``data.build_order_lines``.
        path (pathlib.Path): Output PNG file.

    Returns:
        None. Writes the chart to ``path``.
    """
    df = add_band(lines)
    data = [df.loc[df["DiscountBand"] == b, "Quantity"] for b in LABELS]
    ticks = [f"{b}\nmedian {d.median():.0f}\nn={len(d)}" for b, d in zip(LABELS, data)]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bp = ax.boxplot(data, tick_labels=ticks, patch_artist=True, widths=0.5,
                    medianprops=dict(color="white", lw=2),
                    whiskerprops=dict(color=INK_MUTED), capprops=dict(color=INK_MUTED),
                    flierprops=dict(marker="o", markersize=3, markerfacecolor=MUTED_FILL,
                                    markeredgecolor="none"))
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(MUTED_FILL if i == 0 else BLUE)
        patch.set_edgecolor("none")
    ax.set_title("Units per order line, by discount given")
    ax.set_xlabel("Discount on the order line")
    ax.set_ylabel("Quantity (units)")
    ax.grid(axis="x", visible=False)
    save(fig, path)


def plot_dollars(t, path):
    """Bar-chart the discount dollars given in each non-zero tier.

    Args:
        t (pandas.DataFrame): Tier table from ``band_table``.
        path (pathlib.Path): Output PNG file.

    Returns:
        None. Writes the chart to ``path``.
    """
    t = t.drop(index="0%")
    fig, ax = plt.subplots(figsize=(8, 3.2))
    bars = ax.bar(t.index.astype(str), t["Discount_given"], color=BLUE, width=0.55)
    for b, v in zip(bars, t["Discount_given"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 600, money(v), ha="center",
                fontsize=9, color=INK_2)
    ax.set_title("Revenue given away through discounts, by tier (Jul 1996 - May 1998)")
    ax.set_ylabel("Discount (USD)")
    ax.set_xlabel("Discount tier")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(money))
    ax.grid(axis="x", visible=False)
    save(fig, path)


def run(lines, orders):
    """Run the Q2 analysis and save its tables and charts.

    Writes two CSVs to ``TABLE_DIR`` and two PNGs to ``FIG_DIR``.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``data.build_order_lines``.
        orders (pandas.DataFrame): Orders from ``data.build_orders``;
            passed to ``customer_table``, which ignores it.

    Returns:
        dict: Headline numbers for the webpage: total discount and its
            share of gross sales, share of lines discounted, median
            and mean quantity per tier, share of discount dollars in
            the 15-25% tiers, and the 10% cap estimate.
    """
    t = band_table(lines)
    t.round(2).to_csv(TABLE_DIR / "q2_discount_tiers.csv")
    customer_table(lines, orders).round(2).to_csv(TABLE_DIR / "q2_customer_discount_rates.csv")
    plot_quantity(lines, FIG_DIR / "q2_quantity_by_discount.png")
    plot_dollars(t, FIG_DIR / "q2_discount_dollars.png")
    saved, n_over = cap_whatif(lines)
    disc = lines[lines["Discount"] > 0]
    deep = lines[lines["Discount"] >= 0.15]
    return {
        "total_discount_given": round(lines["DiscountAmount"].sum(), 2),
        "discount_pct_of_gross": round(lines["DiscountAmount"].sum() / lines["GrossRevenue"].sum() * 100, 2),
        "share_lines_discounted_pct": round(len(disc) / len(lines) * 100, 1),
        "median_qty": {k: float(v) for k, v in t["Median_qty"].items()},
        "mean_qty": {k: round(float(v), 1) for k, v in t["Mean_qty"].items()},
        "deep_tiers_share_of_discount_pct": round(deep["DiscountAmount"].sum() / lines["DiscountAmount"].sum() * 100, 1),
        "cap_10pct_savings": round(saved, 2),
        "cap_10pct_lines_affected": int(n_over),
    }
