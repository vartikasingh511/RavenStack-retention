-- RavenStack retention analysis: core business metrics in SQL.
-- These run against an in-memory SQLite database loaded from the five CSV files
-- by analysis.py. The censored retention curve is computed in Python (see analysis.py)
-- because the per-month eligibility logic reads more clearly there.

-- 1. Net churn (permanent loss): the account-level churn flag.
--    name: net_churn
SELECT
    COUNT(*)                                   AS accounts,
    SUM(churn_flag)                            AS churned,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 1) AS net_churn_pct
FROM accounts;

-- 2. Gross vs net: how many accounts ever hit a cancellation moment,
--    versus how many are permanently gone. The gap is reactivation.
--    name: gross_vs_net
SELECT
    (SELECT COUNT(DISTINCT account_id) FROM churn_events)        AS accounts_ever_churned,
    (SELECT SUM(churn_flag) FROM accounts)                       AS accounts_permanently_churned,
    (SELECT COUNT(*) FROM accounts)                              AS total_accounts;

-- 3. Net churn by acquisition channel (the lead segment lens).
--    name: churn_by_channel
SELECT
    referral_source,
    COUNT(*)                                   AS accounts,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 1) AS net_churn_pct
FROM accounts
GROUP BY referral_source
ORDER BY net_churn_pct DESC;

-- 4. Net churn by industry vertical (the supporting segment lens).
--    name: churn_by_industry
SELECT
    industry,
    COUNT(*)                                   AS accounts,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 1) AS net_churn_pct
FROM accounts
GROUP BY industry
ORDER BY net_churn_pct DESC;

-- 5. Net churn by plan tier (expected to be flat, and it is).
--    name: churn_by_plan
SELECT
    plan_tier,
    COUNT(*)                                   AS accounts,
    ROUND(100.0 * SUM(churn_flag) / COUNT(*), 1) AS net_churn_pct
FROM accounts
GROUP BY plan_tier
ORDER BY net_churn_pct DESC;

-- 6. Churn reason mix (diffuse, no dominant cause).
--    name: churn_reasons
SELECT
    reason_code,
    COUNT(*)                                              AS events,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM churn_events), 1) AS share_pct
FROM churn_events
GROUP BY reason_code
ORDER BY events DESC;

-- 7. Support experience: churned vs retained accounts.
--    Tests whether support quality separates the two groups (it does not).
--    name: support_compare
SELECT
    a.churn_flag,
    COUNT(t.ticket_id)                               AS tickets,
    ROUND(AVG(t.first_response_time_minutes), 0)     AS median_first_response_min,
    ROUND(AVG(t.satisfaction_score), 2)              AS avg_satisfaction,
    ROUND(AVG(t.escalation_flag), 3)                 AS escalation_rate
FROM accounts a
JOIN support_tickets t ON t.account_id = a.account_id
GROUP BY a.churn_flag;
