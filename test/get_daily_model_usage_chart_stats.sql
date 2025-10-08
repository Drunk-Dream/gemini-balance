-- SQLite
WITH KeyUsage AS (
    SELECT
        key_identifier,
        key_brief,
        model_name,
        COUNT(*) as usage_count
    FROM request_logs
    WHERE is_success = 1 AND request_time >= 1759239435.56611 AND request_time <= 1759936903.8471
    GROUP BY key_identifier, model_name
),
KeyTotalUsage AS (
    SELECT
        key_identifier,
        SUM(usage_count) as total_usage
    FROM KeyUsage
    GROUP BY key_identifier
)
SELECT
    ku.key_identifier,
    ku.key_brief,
    ku.model_name,
    ku.usage_count
FROM KeyUsage ku
JOIN KeyTotalUsage ktu ON ku.key_identifier = ktu.key_identifier
ORDER BY
    ktu.total_usage DESC,
    ku.key_identifier ASC,
    ku.model_name DESC