"""Q3: revenue concentration and valuable customers gone quiet."""
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from data import AS_OF_DATE, FIG_DIR, TABLE_DIR
from style import BLUE, INK_2, INK_MUTED, MUTED_FILL, ORANGE, money, save

# A customer is "at risk" if it has ordered at least MIN_ORDERS times, and the
# time since its last order is more than GAP_MULTIPLE x its own usual gap
# between orders and at least MIN_DAYS. Using each customer's own rhythm
# avoids flagging naturally infrequent buyers.
MIN_ORDERS = 3
GAP_MULTIPLE = 2.0
MIN_DAYS = 60


def customer_table(lines, orders):
    """Build per-customer revenue, ordering rhythm and risk flag.

    A customer is at risk if it has at least ``MIN_ORDERS`` orders and
    has been silent, as of ``AS_OF_DATE``, for at least ``MIN_DAYS``
    days and more than ``GAP_MULTIPLE`` times its median gap between
    orders.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``data.build_order_lines``; supplies revenue and company
            names.
        orders (pandas.DataFrame): Orders from ``data.build_orders``;
            supplies order dates and countries.

    Returns:
        pandas.DataFrame: One row per buying customer (index
            ``CustomerID``), sorted by revenue descending: company,
            country, revenue (USD), orders, last order date, usual
            gap and days since last order, their ratio, rank,
            cumulative revenue share (%) and ``AtRisk``.
            ``UsualGapDays`` is NaN for single-order customers.
    """
    rev = lines.groupby("CustomerID")["Revenue"].sum()
    o = orders.sort_values("OrderDate")
    g = o.groupby("CustomerID")
    c = pd.DataFrame({
        "Company": g["CustomerID"].first().map(
            lines.drop_duplicates("CustomerID").set_index("CustomerID")["CompanyName"]),
        "Country": g["Country"].first(),
        "Revenue": rev,
        "Orders": g["OrderID"].nunique(),
        "LastOrder": g["OrderDate"].max(),
        "UsualGapDays": g["OrderDate"].apply(lambda s: s.diff().dt.days.median()),
    })
    c["DaysSinceLast"] = (AS_OF_DATE - c["LastOrder"]).dt.days
    c["OverdueRatio"] = c["DaysSinceLast"] / c["UsualGapDays"]
    c = c.sort_values("Revenue", ascending=False)
    c["Rank"] = np.arange(1, len(c) + 1)
    c["CumShare_%"] = c["Revenue"].cumsum() / c["Revenue"].sum() * 100
    c["AtRisk"] = ((c["Orders"] >= MIN_ORDERS) & (c["DaysSinceLast"] >= MIN_DAYS)
                   & (c["OverdueRatio"] > GAP_MULTIPLE))
    return c


def plot_pareto(c, path):
    """Plot cumulative revenue share against customer rank.

    Args:
        c (pandas.DataFrame): Customer table from ``customer_table``,
            sorted by revenue descending.
        path (pathlib.Path): Output PNG file.

    Returns:
        None. Writes the chart to ``path``.
    """
    x = c["Rank"] / len(c) * 100
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.plot(np.r_[0, x], np.r_[0, c["CumShare_%"]], color=BLUE)
    ax.plot([0, 100], [0, 100], color=MUTED_FILL, lw=1, ls="--")
    ax.text(62, 55, "if every customer\nbought the same", color=INK_MUTED, fontsize=8.5)
    for k in (10, round(len(c) * 0.2)):
        share = c["CumShare_%"].iloc[k - 1]
        ax.scatter([k / len(c) * 100], [share], color=BLUE, s=40, zorder=3,
                   edgecolor="white", linewidth=1)
        ax.annotate(f"Top {k} customers = {share:.0f}% of revenue",
                    (k / len(c) * 100, share), xytext=(10, -14), textcoords="offset points",
                    fontsize=9, color=INK_2)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 102)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter())
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_xlabel(f"Customers, ranked by revenue (share of {len(c)} buying customers)")
    ax.set_ylabel("Cumulative share of revenue")
    ax.set_title("Revenue concentration across customers (Jul 1996 - May 1998)")
    save(fig, path)


def plot_risk(c, path):
    """Scatter lifetime revenue against days since last order.

    At-risk customers are highlighted and labelled by name.

    Args:
        c (pandas.DataFrame): Customer table from ``customer_table``.
        path (pathlib.Path): Output PNG file.

    Returns:
        None. Writes the chart to ``path``.
    """
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ok = c[~c["AtRisk"]]
    risk = c[c["AtRisk"]]
    ax.scatter(ok["DaysSinceLast"], ok["Revenue"], s=28, color=MUTED_FILL,
               edgecolor="white", linewidth=0.8, label="Ordering on rhythm")
    ax.scatter(risk["DaysSinceLast"], risk["Revenue"], s=48, color=ORANGE,
               edgecolor="white", linewidth=1, label=f"At risk (silent > {GAP_MULTIPLE:.0f}x usual gap)")
    # Labels go to the right of each point, nudged up/down by hand where two
    # at-risk customers sit close together (layout only; no effect on results).
    nudge = {"BERGS": 14, "MEREP": -6, "SEVES": -9, "BLONP": 2}
    for cid, r in risk.iterrows():
        ax.annotate(f"{r['Company']} ({r['Country']})", (r["DaysSinceLast"], r["Revenue"]),
                    xytext=(8, nudge.get(cid, 0)), textcoords="offset points",
                    ha="left", va="center", fontsize=8.5, color=INK_2)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(money))
    ax.set_xlabel("Days since last order (as of 6 May 1998)")
    ax.set_ylabel("Lifetime revenue (USD, log scale)")
    ax.set_title("Customer value vs. time since last order")
    ax.legend(loc="lower right")
    save(fig, path)


def run(lines, orders):
    """Run the Q3 analysis and save its tables and charts.

    Writes two CSVs to ``TABLE_DIR`` and two PNGs to ``FIG_DIR``.

    Args:
        lines (pandas.DataFrame): Order lines from
            ``data.build_order_lines``.
        orders (pandas.DataFrame): Orders from ``data.build_orders``.

    Returns:
        dict: Headline numbers for the webpage: customer count,
            revenue share of the top 10, top 20% and bottom half,
            at-risk count, their lifetime and prior-12-month revenue
            (USD), and one record per at-risk customer.
    """
    c = customer_table(lines, orders)
    c.to_csv(TABLE_DIR / "q3_customers.csv", float_format="%.2f")
    risk = c[c["AtRisk"]].sort_values("Revenue", ascending=False)
    risk.to_csv(TABLE_DIR / "q3_at_risk_customers.csv", float_format="%.2f")
    plot_pareto(c, FIG_DIR / "q3_pareto.png")
    plot_risk(c, FIG_DIR / "q3_at_risk.png")
    n20 = round(len(c) * 0.2)
    last12 = lines[lines["OrderDate"] > AS_OF_DATE - pd.Timedelta(days=365)]
    return {
        "buying_customers": int(len(c)),
        "top10_share_pct": round(c["CumShare_%"].iloc[9], 1),
        "top20pct_n": int(n20),
        "top20pct_share_pct": round(c["CumShare_%"].iloc[n20 - 1], 1),
        "bottom50pct_share_pct": round(100 - c["CumShare_%"].iloc[len(c) // 2 - 1], 1),
        "at_risk_n": int(len(risk)),
        "at_risk_lifetime_revenue": round(risk["Revenue"].sum(), 2),
        "at_risk_prior12m_revenue": round(
            last12[last12["CustomerID"].isin(risk.index)]["Revenue"].sum(), 2),
        "at_risk_all": risk[["Company", "Country", "Revenue", "Orders",
                                     "DaysSinceLast", "UsualGapDays"]]
        .round(1).reset_index().to_dict(orient="records"),
    }
