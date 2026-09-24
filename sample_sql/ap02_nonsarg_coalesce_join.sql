-- AP-02 Positive: COALESCE() wrapping column in a JOIN ON condition
SELECT o.id, o.total_amount, c.name
FROM orders o
JOIN customers c ON COALESCE(o.customer_id, 0) = c.id
WHERE o.status = 'active';
