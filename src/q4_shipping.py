"""Q4: Are orders shipped on time, and what drives late shipments?"""
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from data import AS_OF_DATE, FIG_DIR, TABLE_DIR
from style import BLUE, CRITICAL, INK_MUTED, MUTED_FILL, save

MIN_N = 20  # minimum orders for a group to appear on the late-rate chart


def wilson(k, n, z=1.96):
    """Compute a Wilson score confidence interval for a proportion.

    Args:
        k (int): Number of successes (e.g. late orders).
        n (int): Number of trials (e.g. orders).
        z (float): Normal critical value; 1.96 gives a 95% interval.

    Returns:
        tuple[float, float]: Lower and upper bounds as fractions
            (0-1), or ``(nan, nan)`` when ``n`` is 0.
    """
    if n == 0:
        return np.nan, np.nan
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return centre - half, centre + half


def late_table(shipped, by):
    """Summarise late-shipment rates for each group.

    Args:
        shipped (pandas.DataFrame): Shipped orders from
            ``data.build_orders``.
        by (str): Column to group by, e.g. ``"Shipper"``.

    Returns:
        pandas.DataFrame: One row per group: orders, late orders,
            median and mean days to ship, late rate (%) and its 95%
            Wilson interval (``CI_low_%``, ``CI_high_%``).
    """
    g = shipped.groupby(by)
    t = g.agg(Orders=("OrderID", "size"), Late=("Late", "sum"),
              Median_days_to_ship=("DaysToShip", "median"),
              Mean_days_to_ship=("DaysToShip", "mean"))
    t["Late_rate_%"] = t["Late"] / t["Orders"] * 100
    ci = [wilson(k, n) for k, n in zip(t["Late"], t["Orders"])]
    t["CI_low_%"] = [a * 100 for a, _ in ci]
    t["CI_high_%"] = [b * 100 for _, b in ci]
    return t


def shipper_table(shipped):
    """Summarise late rates and freight cost for each shipper.

    Args:
        shipped (pandas.DataFrame): Shipped orders from
            ``data.build_orders``.

    Returns:
        pandas.DataFrame: ``late_table`` columns plus mean freight per
            order (USD), freight per $100 of revenue, and mean order
            revenue (USD).
    """
    t = late_table(shipped, "Shipper")
    g = shipped.groupby("Shipper")
    t["Mean_freight_$"] = g["Freight"].mean()
    t["Freight_per_$100_revenue"] = g["Freight"].sum() / g["Revenue"].sum() * 100
    t["Mean_order_revenue_$"] = g["Revenue"].mean()
    return t


def plot_days_vs_promise(shipped, path):
    """Box-plot days to ship for each promised delivery window.

    Each window's deadline is marked along with its late rate.

    Args:
        shipped (pandas.DataFrame): Shipped orders from
            ``data.build_orders``.
        path (pathlib.Path): Output PNG file.

    Returns:
        None. Writes the chart to ``path``.
    """
    windows = sorted(shipped["PromisedDays"].unique())
    data = [shipped.loc[shipped["PromisedDays"] == w, "DaysToShip"] for w in windows]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    bp = ax.boxplot(data, vert=False, patch_artist=True, widths=0.45,
                    tick_labels=[f"{w}-day promise\n(n={len(d)})" for w, d in zip(windows, data)],
                    medianprops=dict(color="white", lw=2),
                    whiskerprops=dict(color=INK_MUTED), capprops=dict(color=INK_MUTED),
                    flierprops=dict(marker="o", markersize=3, markerfacecolor=MUTED_FILL,
                                    markeredgecolor="none"))
    for patch in bp["boxes"]:
        patch.set_facecolor(BLUE)
        patch.set_edgecolor("none")
    for i, (w, d) in enumerate(zip(windows, data), start=1):
        ax.vlines(w, i - 0.35, i + 0.35, color=CRITICAL, lw=2)
        late = (d > w).mean() * 100
        ax.text(w + 0.6, i + 0.28, f"deadline: {late:.0f}% late", color=CRITICAL,
                fontsize=8.5, va="center")
    ax.set_xlabel("Days from order date to ship date")
    ax.set_title("Rush orders are not shipped any faster than standard ones")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(windows) + 8)
    save(fig, path)


def plot_late(panels, overall, path):
    """Plot late rates with 95% intervals, one panel per breakdown.

    Args:
        panels (dict[str, pandas.DataFrame]): Panel title mapped to a
            ``late_table`` result, drawn top to bottom in order. Needs
            at least two entries.
        overall (float): Company-wide late rate in percent, drawn as a
            dashed reference line.
        path (pathlib.Path): Output PNG file.

    Returns:
        None. Writes the chart to ``path``.
    """
    heights = [len(t) for t in panels.values()]
    fig, axes = plt.subplots(len(panels), 1, figsize=(8, 1.4 + 0.38 * sum(heights)),
                             gridspec_kw={"height_ratios": heights}, sharex=True)
    for ax, (title, t) in zip(axes, panels.items()):
        y = np.arange(len(t))
        ax.hlines(y, t["CI_low_%"], t["CI_high_%"], color=MUTED_FILL, lw=3)
        ax.scatter(t["Late_rate_%"], y, color=BLUE, s=40, zorder=3, edgecolor="white")
        ax.set_yticks(y, [f"{i}  (n={n})" for i, n in zip(t.index, t["Orders"])])
        ax.axvline(overall, color=INK_MUTED, ls="--", lw=1)
        ax.set_title(title, fontsize=10.5)
        ax.grid(axis="y", visible=False)
        ax.set_ylim(-0.7, len(t) - 0.3)
    axes[-1].set_xlabel("Share of orders shipped after the required date, with 95% interval "
                        f"(dashed line = company average {overall:.1f}%)")
    axes[-1].xaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    axes[-1].set_xlim(0, None)
    fig.suptitle("Late-shipment rate by promised window, shipper and customer region",
                 x=0.02, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    save(fig, path)


def run(lines, orders, employees):
    """Run the Q4 analysis and save its tables and charts.

    Writes six CSVs to ``TABLE_DIR`` and two PNGs to ``FIG_DIR``.
    Unshipped orders are left out of all late-rate figures.

    Args:
        lines (pandas.DataFrame): Order lines; unused, accepted so
            every ``run`` has the same first inputs.
        orders (pandas.DataFrame): Orders from ``data.build_orders``.
        employees (pandas.DataFrame): Employees sheet; supplies
            salesperson names.

    Returns:
        dict: Headline numbers for the webpage: shipped and late
            counts, late rate, median days late and to ship, rush
            (14-day) order counts and share of late orders, checks on
            unshipped orders, and per-group tables as record lists.
    """
    shipped = orders[orders["Shipped"]].copy()
    names = employees.set_index("EmployeeID")
    shipped["Salesperson"] = shipped["EmployeeID"].map(names["FirstName"] + " " + names["LastName"])
    shipped["Promise"] = shipped["PromisedDays"].astype(str) + " days"
    overall = shipped["Late"].mean() * 100

    by_promise = late_table(shipped, "Promise").sort_index(key=lambda s: s.str.len() * 100 + s.str[:2].astype(int))
    by_shipper = shipper_table(shipped)
    by_region = late_table(shipped, "Region").sort_values("Late_rate_%")
    by_rep = late_table(shipped, "Salesperson")
    standard = shipped[shipped["PromisedDays"] == 28]
    by_region_std = late_table(standard, "Region")
    by_shipper_rush = late_table(shipped[shipped["PromisedDays"] == 14], "Shipper")
    for name, t in [("promised_window", by_promise), ("shipper", by_shipper),
                    ("region", by_region), ("salesperson", by_rep),
                    ("region_28day_only", by_region_std), ("shipper_14day_only", by_shipper_rush)]:
        t.to_csv(TABLE_DIR / f"q4_late_by_{name}.csv", float_format="%.2f")

    plot_days_vs_promise(shipped, FIG_DIR / "q4_days_vs_promise.png")
    # Regions with fewer than MIN_N orders (Eastern Europe = Poland, 7 orders)
    # are left off the chart: their intervals are too wide to read. They stay in the CSV.
    plot_late({"Promised delivery window": by_promise, "Shipper": by_shipper,
               "Customer region": by_region[by_region["Orders"] >= MIN_N]},
              overall, FIG_DIR / "q4_late_rates.png")

    unshipped = orders[~orders["Shipped"]]
    late_days = (shipped["ShippedDate"] - shipped["RequiredDate"]).dt.days[shipped["Late"]]
    rush = shipped[shipped["PromisedDays"] == 14]
    return {
        "shipped_orders": int(len(shipped)),
        "late_orders": int(shipped["Late"].sum()),
        "late_rate_pct": round(overall, 1),
        "median_days_late": float(late_days.median()),
        "median_days_to_ship": float(shipped["DaysToShip"].median()),
        "rush_orders": int(len(rush)),
        "rush_late_orders": int(rush["Late"].sum()),
        "rush_share_of_late_pct": round(rush["Late"].sum() / shipped["Late"].sum() * 100, 1),
        "unshipped_orders": int(len(unshipped)),
        "unshipped_overdue_as_of": int((unshipped["RequiredDate"] < AS_OF_DATE).sum()),
        "unshipped_earliest_order": str(unshipped["OrderDate"].min().date()),
        "by_promised_window": by_promise.round(2).reset_index().to_dict(orient="records"),
        "by_shipper": by_shipper.round(2).reset_index().to_dict(orient="records"),
        "by_region": by_region.round(2).reset_index().to_dict(orient="records"),
        "by_region_28day_only": by_region_std.round(2).reset_index().to_dict(orient="records"),
    }
