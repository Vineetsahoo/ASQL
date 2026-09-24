-- AP-05 Positive: IN subquery in a more complex query
SELECT c.name, c.email
FROM customers c
WHERE c.id IN (
    SELECT o.customer_id
    FROM orders o
    JOIN shipments s ON o.id = s.order_id
    WHERE s.carrier = 'FedEx'
);
