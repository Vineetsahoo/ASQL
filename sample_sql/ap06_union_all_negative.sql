-- Negative Control: UNION ALL (Optimal concatenation without deduplication sort)
SELECT id, name, sku FROM current_catalog WHERE is_active = 1
UNION ALL
SELECT id, name, sku FROM archive_catalog WHERE is_active = 1;
