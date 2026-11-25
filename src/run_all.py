"""Run all four analyses and save their figures, tables and numbers.

Entry point: ``python src/run_all.py`` from the project root.
"""
import json

import q1_markets
import q2_discounts
import q3_customers
import q4_shipping
from data import FIG_DIR, ROOT, TABLE_DIR, build_order_lines, build_orders, check_data, load_tables
from style import apply_style


def main():
    """Load the data, run every analysis and save the results.

    Args:
        None.

    Returns:
        None. Writes figures to ``docs/figures``, tables to
            ``outputs/tables`` and headline numbers to
            ``outputs/results.json``, and prints them as JSON.
    """
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    apply_style()

    tables = load_tables()
    check_data(tables)
    lines = build_order_lines(tables)
    orders = build_orders(tables)

    results = {
        "dataset": {
            "orders": int(len(orders)),
            "order_lines": int(len(lines)),
            "first_order": str(orders["OrderDate"].min().date()),
            "last_order": str(orders["OrderDate"].max().date()),
            "total_revenue": round(lines["Revenue"].sum(), 2),
        },
        "q1_markets": q1_markets.run(lines, orders),
        "q2_discounts": q2_discounts.run(lines, orders),
        "q3_customers": q3_customers.run(lines, orders),
        "q4_shipping": q4_shipping.run(lines, orders, tables["Employees"]),
    }
    out = ROOT / "outputs" / "results.json"
    out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
