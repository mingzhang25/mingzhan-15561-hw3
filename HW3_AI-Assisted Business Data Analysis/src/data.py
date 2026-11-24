"""Load the Northwind workbook and build cleaned order tables."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "northwind.xlsx"
FIG_DIR = ROOT / "docs" / "figures"
TABLE_DIR = ROOT / "outputs" / "tables"

# Last order in the file is 1998-05-06, so May 1998 is a partial month.
# Analyses that compare periods use only complete months (through April 1998).
LAST_FULL_MONTH = pd.Period("1998-04", freq="M")
AS_OF_DATE = pd.Timestamp("1998-05-06")

# Country -> sales region, used to keep shipping and market charts readable.
REGION = {
    "USA": "North America", "Canada": "North America", "Mexico": "Latin America",
    "Brazil": "Latin America", "Argentina": "Latin America", "Venezuela": "Latin America",
    "UK": "British Isles", "Ireland": "British Isles",
    "Germany": "Western Europe", "France": "Western Europe", "Belgium": "Western Europe",
    "Switzerland": "Western Europe", "Austria": "Western Europe",
    "Sweden": "Nordics", "Denmark": "Nordics", "Finland": "Nordics", "Norway": "Nordics",
    "Italy": "Southern Europe", "Spain": "Southern Europe", "Portugal": "Southern Europe",
    "Poland": "Eastern Europe",
}


def load_tables(path=DATA_PATH):
    """Read every sheet of the Northwind workbook.

    Args:
        path (str | pathlib.Path): Excel workbook; defaults to
            ``data/northwind.xlsx`` in the project root.

    Returns:
        dict[str, pandas.DataFrame]: One DataFrame per sheet, keyed by
            sheet name (e.g. ``"Orders"``, ``"Orders Details"``).
    """
    return pd.read_excel(path, sheet_name=None)


def build_order_lines(tables):
    """Build one row per order line with revenue and order context.

    Revenue uses the unit price charged on the line, not the current
    list price in the Product sheet.

    Args:
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``.

    Returns:
        pandas.DataFrame: Order lines with ``GrossRevenue``,
            ``DiscountAmount`` and ``Revenue`` (USD), plus customer,
            product, category, ``OrderDate``, ``Month`` (monthly
            Period) and ``Region``.
    """
    lines = tables["Orders Details"].copy()
    orders = tables["Orders"]
    customers = tables["Customers"][["CustomerID", "CompanyName", "Country"]]
    products = tables["Product"][["ProductID", "ProductName", "CategoryID"]]
    categories = tables["Categories"][["CategoryID", "CategoryName"]]

    # Revenue uses the price actually charged on the line (Orders Details),
    # not today's list price in the Product sheet.
    lines["GrossRevenue"] = lines["UnitPrice"] * lines["Quantity"]
    lines["DiscountAmount"] = lines["GrossRevenue"] * lines["Discount"]
    lines["Revenue"] = lines["GrossRevenue"] - lines["DiscountAmount"]

    df = (
        lines.merge(orders[["OrderID", "CustomerID", "EmployeeID", "OrderDate"]], on="OrderID")
        .merge(customers, on="CustomerID", how="left")
        .merge(products, on="ProductID", how="left")
        .merge(categories, on="CategoryID", how="left")
    )
    df["Month"] = df["OrderDate"].dt.to_period("M")
    df["Region"] = df["Country"].map(REGION)
    return df


def build_orders(tables):
    """Build one row per order with revenue and shipping timing.

    Args:
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``.

    Returns:
        pandas.DataFrame: Orders with ``Revenue`` (USD after
            discounts), ``Shipper``, customer ``Country`` and
            ``Region``, ``Shipped``, ``DaysToShip``, ``PromisedDays``,
            ``Late`` (shipped after ``RequiredDate``; False if not
            shipped) and ``Month``.
    """
    orders = tables["Orders"].copy()
    lines = build_order_lines(tables)
    revenue = lines.groupby("OrderID")["Revenue"].sum().rename("Revenue")
    shippers = tables["Shippers"].rename(columns={"ShipperID": "ShipVia", "CompanyName": "Shipper"})

    orders = orders.merge(revenue, on="OrderID", how="left")
    orders = orders.merge(shippers[["ShipVia", "Shipper"]], on="ShipVia", how="left")
    orders = orders.merge(tables["Customers"][["CustomerID", "Country"]], on="CustomerID", how="left")
    orders["Region"] = orders["Country"].map(REGION)
    orders["Shipped"] = orders["ShippedDate"].notna()
    orders["DaysToShip"] = (orders["ShippedDate"] - orders["OrderDate"]).dt.days
    orders["PromisedDays"] = (orders["RequiredDate"] - orders["OrderDate"]).dt.days
    orders["Late"] = orders["ShippedDate"] > orders["RequiredDate"]
    orders["Month"] = orders["OrderDate"].dt.to_period("M")
    return orders


def check_data(tables):
    """Check the workbook has the structure the analysis relies on.

    Args:
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``.

    Returns:
        None.

    Raises:
        AssertionError: If order IDs repeat, an order line or customer
            has no match, a discount is outside 0-1, or a customer
            country is missing from ``REGION``.
    """
    orders, lines = tables["Orders"], tables["Orders Details"]
    assert orders["OrderID"].is_unique, "duplicate OrderID"
    assert not lines.duplicated(["OrderID", "ProductID"]).any(), "duplicate order lines"
    assert set(lines["OrderID"]) <= set(orders["OrderID"]), "order lines without an order"
    assert set(orders["CustomerID"]) <= set(tables["Customers"]["CustomerID"]), "unknown customer"
    assert lines["Discount"].between(0, 1).all(), "discount outside 0-1"
    assert set(tables["Customers"]["Country"]) <= set(REGION), "country missing from REGION map"
