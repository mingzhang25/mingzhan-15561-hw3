"""Q1: which country markets are growing or shrinking.

Compares revenue by customer country for Jan-Apr 1997 vs Jan-Apr 1998.
"""
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from data import FIG_DIR, LAST_FULL_MONTH, TABLE_DIR
from style import BLUE, CRITICAL, INK_2, INK_MUTED, MUTED_FILL, money, save

# Same four calendar months in both years, so seasonality and the partial
# years (data starts July 1996, ends 6 May 1998) do not distort growth.
P1 = ("1997-01", "1997-04")
P2 = ("1998-01", "1998-04")
SMALL_BASE = 5000  # USD; below this, % change is not shown on the chart


def period_label(month):
    """Map a month to its comparison window.

    Args:
        month (pandas.Period): Calendar month; its string form must be
            ``"YYYY-MM"``.

    Returns:
        str | None: ``"Jan-Apr 1997"``, ``"Jan-Apr 1998"``, or None if
            the month is in neither window.
    """
    m = str(month)
    if P1[0] <= m <= P1[1]:
        return "Jan-Apr 1997"
    if P2[0] <= m <= P2[1]:
        return "Jan-Apr 1998"
    return None


def market_table(lines):
    """Summarise revenue and customers by country for both windows.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``data.build_order_lines``.

    Returns:
        pandas.DataFrame: One row per country with orders in either
            window, sorted by Jan-Apr 1998 revenue: revenue (USD) and
            distinct customers per window, change in USD and %,
            share of total growth (%), and revenue in the last 12
            complete months. ``Change_%`` is NaN when 1997 revenue
            is zero.
    """
    df = lines.assign(Period=lines["Month"].map(period_label)).dropna(subset=["Period"])
    rev = df.pivot_table(index="Country", columns="Period", values="Revenue",
                         aggfunc="sum", fill_value=0)
    cust = df.pivot_table(index="Country", columns="Period", values="CustomerID",
                          aggfunc="nunique", fill_value=0)
    t = pd.DataFrame({
        "Revenue_JanApr1997": rev["Jan-Apr 1997"],
        "Revenue_JanApr1998": rev["Jan-Apr 1998"],
        "Customers_JanApr1997": cust["Jan-Apr 1997"],
        "Customers_JanApr1998": cust["Jan-Apr 1998"],
    })
    t["Change_$"] = t["Revenue_JanApr1998"] - t["Revenue_JanApr1997"]
    t["Change_%"] = (t["Change_$"] / t["Revenue_JanApr1997"].replace(0, pd.NA)) * 100
    t["Share_of_growth_%"] = t["Change_$"] / t["Change_$"].sum() * 100
    # Revenue over the full last 12 complete months shows market size.
    last12 = lines[(lines["Month"] > LAST_FULL_MONTH - 12) & (lines["Month"] <= LAST_FULL_MONTH)]
    t["Revenue_last12m"] = last12.groupby("Country")["Revenue"].sum()
    return t.sort_values("Revenue_JanApr1998", ascending=False)


def plot_monthly(lines, path):
    """Plot monthly revenue through April 1998 with windows shaded.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``data.build_order_lines``.
        path (pathlib.Path): Output PNG file.

    Returns:
        None. Writes the chart to ``path``.
    """
    m = lines[lines["Month"] <= LAST_FULL_MONTH].groupby("Month")["Revenue"].sum()
    x = m.index.to_timestamp()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(x, m.values, color=BLUE, marker="o", markersize=4)
    for period in (P1, P2):
        ax.axvspan(pd.Timestamp(period[0]), pd.Timestamp(period[1]) + pd.offsets.MonthEnd(0),
                   color=MUTED_FILL, alpha=0.25, lw=0)
    ax.set_title("Monthly revenue, Jul 1996 - Apr 1998")
    ax.set_ylabel("Revenue after discounts (USD)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(money))
    ax.set_ylim(0, None)
    ax.grid(axis="x", visible=False)
    ax.text(pd.Timestamp("1997-01-05"), m.max() * 0.97, "Compared periods shaded",
            color=INK_MUTED, fontsize=9, va="top")
    save(fig, path)


def plot_dumbbell(t, path):
    """Plot each country's revenue in both windows as a dumbbell chart.

    Args:
        t (pandas.DataFrame): Country table from ``market_table``.
        path (pathlib.Path): Output PNG file.

    Returns:
        None. Writes the chart to ``path``.
    """
    t = t.sort_values("Revenue_JanApr1998")
    y = range(len(t))
    fig, ax = plt.subplots(figsize=(8, 7))
    for i, (_, r) in enumerate(t.iterrows()):
        declined = r["Change_$"] < 0
        ax.plot([r["Revenue_JanApr1997"], r["Revenue_JanApr1998"]], [i, i],
                color=CRITICAL if declined else MUTED_FILL, lw=2, zorder=1)
        # Percent change is misleading on tiny bases, so show it only when
        # the 1997 base is at least $5k; always show the dollar change.
        sign = "-" if declined else "+"
        label = f"{sign}${abs(r['Change_$']) / 1000:,.1f}k"
        if r["Revenue_JanApr1997"] >= SMALL_BASE:
            label += f" ({r['Change_%']:+.0f}%)"
        ax.text(max(r["Revenue_JanApr1997"], r["Revenue_JanApr1998"]) + 1500, i, label,
                va="center", fontsize=8.5, color=CRITICAL if declined else INK_2,
                fontweight="bold" if declined else "normal")
    ax.scatter(t["Revenue_JanApr1997"], y, s=40, color=MUTED_FILL, edgecolor="white",
               linewidth=1, zorder=2, label="Jan-Apr 1997")
    ax.scatter(t["Revenue_JanApr1998"], y, s=40, color=BLUE, edgecolor="white",
               linewidth=1, zorder=3, label="Jan-Apr 1998")
    ax.set_yticks(list(y), t.index)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(money))
    ax.set_xlabel("Revenue after discounts (USD). Labels: change in USD (and %, where 1997 base >= $5k)")
    ax.set_xlim(0, t[["Revenue_JanApr1997", "Revenue_JanApr1998"]].max().max() * 1.2)
    ax.set_title("Revenue by customer country, Jan-Apr 1997 vs Jan-Apr 1998")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    save(fig, path)


def run(lines, orders):
    """Run the Q1 analysis and save its table and charts.

    Writes ``q1_markets.csv`` to ``TABLE_DIR`` and two PNGs to
    ``FIG_DIR``.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``data.build_order_lines``.
        orders (pandas.DataFrame): Orders from ``data.build_orders``;
            unused, accepted so every ``run`` has the same inputs.

    Returns:
        dict: Headline numbers for the webpage: revenue per window,
            growth %, top 3 growth countries and their share of
            growth, declining countries, and France's change and
            customer counts.
    """
    t = market_table(lines)
    t.round(2).to_csv(TABLE_DIR / "q1_markets.csv")
    plot_monthly(lines, FIG_DIR / "q1_monthly_revenue.png")
    plot_dumbbell(t, FIG_DIR / "q1_country_change.png")
    total97, total98 = t["Revenue_JanApr1997"].sum(), t["Revenue_JanApr1998"].sum()
    top3 = t.sort_values("Change_$", ascending=False).head(3)
    return {
        "revenue_janapr_1997": round(total97, 2),
        "revenue_janapr_1998": round(total98, 2),
        "growth_pct": round((total98 / total97 - 1) * 100, 1),
        "top3_growth_countries": top3.index.tolist(),
        "top3_share_of_growth_pct": round(top3["Share_of_growth_%"].sum(), 1),
        "declining_countries": t[t["Change_$"] < 0].index.tolist(),
        "france_change_pct": round(t.loc["France", "Change_%"], 1),
        "france_customers": [int(t.loc["France", "Customers_JanApr1997"]),
                             int(t.loc["France", "Customers_JanApr1998"])],
    }
