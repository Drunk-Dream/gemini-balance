-- SQLite
SELECT
    strftime('%Y-%m-%d', request_time, 'unixepoch', '+01:00') AS period_label,
    model_name,
    COUNT(DISTINCT request_id) as request_count
FROM request_logs
WHERE is_success = 1 AND request_time >= 1758596292.53118 AND request_time <= 1759830613.38712
GROUP BY period_label, model_name