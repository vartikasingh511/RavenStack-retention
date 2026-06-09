# RavenStack retention: where accounts leak and what to do about it

A retention and lifecycle case study on a Software as a Service (SaaS) product. I take a
multi table SaaS dataset of 500 accounts, find where and when customers leak, test the
usual explanations, and write a product recommendation grounded only in what the data
actually supports.

The full case study, including the Product Requirements Document (PRD), the recommendation,
and the reasoning, lives in my product portfolio. This repository is the evidence layer:
the data, the Structured Query Language (SQL), and the Python that produce every number.

## The question

Where and why do RavenStack accounts churn, and what should the product team do about it?

## Headline finding

Churn is front loaded. Retention falls off a shelf right after signup and then flattens.
The first month is the single largest loss window, and more than half of the first year's
lost retention is gone by month three. This is an early life problem, not a loyalty problem.

![Retention by tenure](./charts/retention_curve.png)

| Metric | Value |
| --- | --- |
| Net churn (permanent) | approximately 22 percent (110 of 500 accounts) |
| Accounts that churned at least once | approximately 70 percent (352 of 500) |
| Retained at month 1 | approximately 83 percent |
| Retained at month 3 | approximately 68 percent |

The gap between 70 percent ever churning and 22 percent staying gone is reactivation.
Many accounts wobble and come back, which is a lever in its own right.

## Who leaks

Net churn varies about twofold by acquisition channel and by industry. Plan tier is flat,
so this is not a pricing or packaging problem.

| Segment | Net churn |
| --- | --- |
| Event channel | approximately 30 percent |
| Ads channel | approximately 24 percent |
| Organic channel | approximately 18 percent |
| Partner channel | approximately 15 percent |
| DevTools vertical | approximately 31 percent |
| Cybersecurity vertical | approximately 16 percent |

## What does not explain it

I tested three common explanations for early churn, and all three failed. This is the most
important part of the analysis, because it kept the recommendation honest.

- Activation gap. Early churners and retained accounts adopt the same number of features
  and log similar usage in the first 30 days. No gap.
- Support experience. Churned and retained accounts see near identical first response times,
  satisfaction scores, and escalation rates. No signal.
- Churn reason. Reasons are diffuse, with no dominant cause. Features leads only slightly,
  at about 19 percent.

The conclusion the data supports is that the leak is driven by who the product acquires,
channel and vertical, far more than by how those users onboard or how they are supported.
The data shows clearly when accounts leave, but not a measured why for the early cliff,
so the recommendation acts where evidence is strong and runs an experiment where it is thin.

## Method notes

- Two churn signals, reconciled. The account churn flag marks permanent loss. The churn
  events table records every cancellation moment. The difference is reactivation.
- The retention curve corrects for the observation window, so late signups are not counted
  as retained for months they never had the chance to reach.
- Monthly signup groups hold only about 21 accounts, too thin for clean month by month
  cohort grids, so accounts are pooled for the headline curve and cut by segments that hold
  80 to 115 accounts each. That is a deliberate choice for the sample size, not an accident.

## Reproduce it

```bash
pip install -r requirements.txt
python analysis.py
```

This loads the five Comma Separated Values (CSV) files into an in memory SQLite database,
runs the business metrics in SQL, computes the censored retention curve in pandas, prints
every number above, and writes the chart to `charts/retention_curve.png`.

## Repository structure

```
data/                  the five RavenStack CSV files, plus the dataset source notes
queries.sql            the analytical SQL: net churn, segment cuts, reconciliation, support
analysis.py            loads data, runs the SQL, builds the retention curve, saves the chart
charts/                the generated retention curve
requirements.txt       pandas, numpy, matplotlib
```

## Data source and credit

The RavenStack synthetic SaaS dataset was created by River at Rivalytics and is fully
synthetic with no personal data. It is used here for educational and portfolio purposes
with credit to the original author, as the licence requires. Source notes are kept in
`data/DATASET_SOURCE.md`.
