"""
RavenStack retention analysis.

Reproduces every number in the case study:
  - net churn and the gross-versus-net reconciliation
  - the window-censored retention curve by tenure
  - net churn by acquisition channel, industry, and plan tier
  - the three rejected hypotheses (activation, support, churn reason)

Run:  python analysis.py
Output: prints all metrics to the console and writes charts/retention_curve.png

The headline business metrics are computed in SQL (see queries.sql) by loading the
five CSV files into an in-memory SQLite database. The retention curve and activation
test are computed in pandas, where the per-month eligibility logic reads more clearly.
"""

import sqlite3
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path(__file__).parent / "data"
CHARTS = Path(__file__).parent / "charts"
END = pd.Timestamp("2024-12-31")  # last date observed in the dataset

TABLES = {
    "accounts": "ravenstack_accounts.csv",
    "subscriptions": "ravenstack_subscriptions.csv",
    "feature_usage": "ravenstack_feature_usage.csv",
    "support_tickets": "ravenstack_support_tickets.csv",
    "churn_events": "ravenstack_churn_events.csv",
}


def load():
    """Load every CSV into a dict of DataFrames and an in-memory SQLite database."""
    frames = {name: pd.read_csv(DATA / f) for name, f in TABLES.items()}
    con = sqlite3.connect(":memory:")
    for name, df in frames.items():
        df.to_sql(name, con, index=False, if_exists="replace")
    return frames, con


def run_named_queries(con):
    """Run each named block in queries.sql and print the result."""
    sql = (Path(__file__).parent / "queries.sql").read_text()
    blocks = re.findall(r"--\s*name:\s*(\w+).*?\n(SELECT.*?;)", sql, flags=re.S)
    for name, query in blocks:
        print(f"\n--- {name} ---")
        print(pd.read_sql_query(query, con).to_string(index=False))


def retention_curve(accounts, churn_events):
    """
    Window-censored retention by months since signup.

    An account is 'retained at month N' if it had no first churn event by month N.
    The denominator at month N only includes accounts old enough to have reached
    month N before the dataset ended, so late signups are not counted as retained
    for time they never had the chance to live through.
    """
    acc = accounts.copy()
    acc["signup_date"] = pd.to_datetime(acc["signup_date"])
    ce = churn_events.copy()
    ce["churn_date"] = pd.to_datetime(ce["churn_date"])

    first_churn = ce.sort_values("churn_date").groupby("account_id", as_index=False)["churn_date"].first()
    acc = acc.merge(first_churn, on="account_id", how="left")
    acc["obs_months"] = (END - acc["signup_date"]).dt.days / 30.44
    acc["churn_months"] = (acc["churn_date"] - acc["signup_date"]).dt.days / 30.44
    acc.loc[acc["churn_months"] < 0, "churn_months"] = np.nan

    months = [0, 1, 2, 3, 4, 6, 9, 12]
    rows = []
    for n in months:
        eligible = acc[acc["obs_months"] >= n]
        alive = eligible[(eligible["churn_months"].isna()) | (eligible["churn_months"] > n)]
        rows.append({"month": n, "retained_pct": round(100 * len(alive) / len(eligible), 1),
                     "eligible": len(eligible)})
    return pd.DataFrame(rows)


def activation_test(frames):
    """Distinct features and usage events in the first 30 days: early churners vs retained."""
    acc = frames["accounts"].copy()
    acc["signup_date"] = pd.to_datetime(acc["signup_date"])
    sub = frames["subscriptions"][["subscription_id", "account_id"]]
    fu = frames["feature_usage"].copy()
    fu["usage_date"] = pd.to_datetime(fu["usage_date"])

    ce = frames["churn_events"].copy()
    ce["churn_date"] = pd.to_datetime(ce["churn_date"])
    first_churn = ce.sort_values("churn_date").groupby("account_id", as_index=False)["churn_date"].first()
    acc = acc.merge(first_churn, on="account_id", how="left")
    acc["churn_months"] = (acc["churn_date"] - acc["signup_date"]).dt.days / 30.44

    fu = fu.merge(sub, on="subscription_id", how="left").merge(
        acc[["account_id", "signup_date"]], on="account_id", how="left")
    fu["days"] = (fu["usage_date"] - fu["signup_date"]).dt.days
    early = fu[(fu["days"] >= 0) & (fu["days"] <= 30)]
    adopt = early.groupby("account_id").agg(
        feats=("feature_name", "nunique"), events=("usage_count", "sum")).reset_index()

    acc = acc.merge(adopt, on="account_id", how="left").fillna({"feats": 0, "events": 0})
    early_churn = acc[(acc["churn_months"].notna()) & (acc["churn_months"] <= 2)]
    retained = acc[acc["churn_months"].isna()]
    return pd.DataFrame([
        {"group": "early churners (<=2 months)", "n": len(early_churn),
         "avg_distinct_features_30d": round(early_churn["feats"].mean(), 1),
         "avg_usage_events_30d": round(early_churn["events"].mean(), 0)},
        {"group": "retained accounts", "n": len(retained),
         "avg_distinct_features_30d": round(retained["feats"].mean(), 1),
         "avg_usage_events_30d": round(retained["events"].mean(), 0)},
    ])


def plot_curve(curve):
    CHARTS.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(range(len(curve)), curve["retained_pct"], marker="o", color="#1D9E75", linewidth=2)
    ax.fill_between(range(len(curve)), curve["retained_pct"], color="#1D9E75", alpha=0.10)
    for i, row in curve.iterrows():
        ax.annotate(f"{row['retained_pct']:.0f}%", (i, row["retained_pct"]),
                    textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)
    ax.set_xticks(range(len(curve)))
    ax.set_xticklabels(curve["month"])
    ax.set_xlabel("months since signup")
    ax.set_ylabel("% of accounts retained")
    ax.set_title("RavenStack retention by tenure: the early-life cliff")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(CHARTS / "retention_curve.png", dpi=130)
    print(f"\nSaved chart to {CHARTS / 'retention_curve.png'}")


def main():
    frames, con = load()
    print("Loaded tables:", {k: len(v) for k, v in frames.items()})

    run_named_queries(con)

    curve = retention_curve(frames["accounts"], frames["churn_events"])
    print("\n--- retention_curve (window-censored) ---")
    print(curve.to_string(index=False))

    print("\n--- activation_test (first 30 days) ---")
    print(activation_test(frames).to_string(index=False))

    plot_curve(curve)


if __name__ == "__main__":
    main()
