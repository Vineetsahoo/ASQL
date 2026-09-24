-- AP-01 Positive: SELECT * in a subquery
SELECT o.id, o.total_amount
FROM (SELECT * FROM orders WHERE status = 'shipped') o
WHERE o.total_amount > 100;
