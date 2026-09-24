-- AP-01 Negative Control: COUNT(*) should NOT trigger AP-01
-- This is the critical "gotcha" case from PRD v2 §4
SELECT COUNT(*) FROM orders WHERE status = 'pending';

-- Also a GROUP BY with COUNT(*)
SELECT customer_id, COUNT(*) as order_count
FROM orders
GROUP BY customer_id
HAVING COUNT(*) > 5;
