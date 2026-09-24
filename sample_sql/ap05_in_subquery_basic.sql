-- AP-05 Positive: WHERE col IN (SELECT ...) non-aggregated subquery
SELECT id, name, email
FROM customers
WHERE id IN (SELECT customer_id FROM orders WHERE status = 'pending');
