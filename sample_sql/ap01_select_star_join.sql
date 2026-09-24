-- AP-01 Positive: SELECT * with JOIN
SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id
WHERE c.city = 'New York';
