import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from download_datasets import ROOT, update, validate


def run_retail():
    source = ROOT / "data/raw/online_retail/online_retail.zip"
    validate(source, "online_retail")
    with ZipFile(source) as archive, archive.open("Online Retail.xlsx") as excel:
        raw = pd.read_excel(excel, dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": "Int64"})
    missing = {column: int(value) for column, value in raw.isna().sum().items()}
    dtypes = raw.dtypes.astype(str).to_dict()
    update("online_retail", records=len(raw), columns=len(raw.columns), dtypes=dtypes, missing=missing)
    duplicate_lines = int(raw.duplicated().sum())
    lines = raw.drop_duplicates().copy()
    lines["InvoiceDate"] = pd.to_datetime(lines["InvoiceDate"], errors="coerce")
    lines["Country"] = lines["Country"].str.strip()
    lines["Description"] = lines["Description"].str.strip()
    lines["is_cancelled"] = lines.InvoiceNo.str.startswith("C", na=False)
    lines["gross_line_gbp"] = lines.Quantity * lines.UnitPrice
    purchases = lines.loc[
        ~lines.is_cancelled & lines.Quantity.gt(0) & lines.UnitPrice.gt(0)
        & lines.CustomerID.notna() & lines.InvoiceDate.notna() & lines.Country.eq("United Kingdom")
        & lines.StockCode.str.match(r"^\d{5}[A-Z]*$", na=False)
    ].copy()
    processed = ROOT / "data/processed"
    processed.mkdir(parents=True, exist_ok=True)
    purchases.to_parquet(processed / "uk_retail_purchases.parquet", index=False)
    monthly = purchases.groupby(purchases.InvoiceDate.dt.to_period("M")).gross_line_gbp.sum()
    repeated = purchases.groupby("CustomerID").InvoiceNo.nunique()
    stats = {
        "raw_records": len(raw), "columns": len(raw.columns), "duplicate_lines": duplicate_lines,
        "missing": missing, "cancellation_lines_after_deduplication": int(lines.is_cancelled.sum()),
        "retained_purchase_lines": len(purchases), "retained_customers": int(purchases.CustomerID.nunique()),
        "retained_invoices": int(purchases.InvoiceNo.nunique()), "retained_stock_codes": int(purchases.StockCode.nunique()),
        "retained_customers_with_multiple_invoices": int(repeated.gt(1).sum()),
        "gross_retained_line_value_gbp": round(purchases.gross_line_gbp.sum(), 2),
        "price_gbp_quantiles": {str(p): round(v, 2) for p, v in purchases.UnitPrice.quantile([0.01, 0.5, 0.95, 0.99]).items()},
        "monthly_gross_gbp": {str(k): round(v, 2) for k, v in monthly.items()},
        "coverage_start": str(purchases.InvoiceDate.min()), "coverage_end": str(purchases.InvoiceDate.max()),
    }
    eda = ROOT / "research/results/eda"
    eda.mkdir(parents=True, exist_ok=True)
    (eda / "online_retail.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        pass
    else:
        fig, axis = plt.subplots(figsize=(9, 4), layout="constrained")
        monthly.plot.bar(ax=axis, color="#267461")
        axis.set(title="UCI Online Retail · retained UK purchase lines", xlabel="Invoice month", ylabel="Gross line value (GBP)")
        fig.savefig(eda / "online_retail_monthly.png", dpi=160)
        plt.close(fig)
    print(json.dumps(stats, indent=2))


def run_products():
    path = ROOT / "data/raw/off_india/india_snacks.json"
    if path.exists():
        products = pd.json_normalize(json.loads(path.read_text(encoding="utf-8"))["products"])
        products = products.drop_duplicates("code")
        products.to_parquet(ROOT / "data/processed/off_india_products.parquet", index=False)
        update("off_india", records=len(products), columns=len(products.columns),
               dtypes=products.dtypes.astype(str).to_dict(), missing=products.isna().sum().to_dict())


if __name__ == "__main__":
    run_retail()
    run_products()
