-- AP-05 Negative Control: subquery with aggregation should NOT trigger
-- GROUP BY makes IN subquery legitimate
SELECT id, name
FROM customers
WHERE id IN (
    SELECT customer_id
    FROM orders
    GROUP BY customer_id
    HAVING COUNT(*) > 5
);

-- EXISTS is already the better pattern, should NOT trigger AP-05
SELECT id, name
FROM customers c
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.id AND o.status = 'pending'
);
