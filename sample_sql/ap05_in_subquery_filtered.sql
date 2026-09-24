-- AP-05 Positive: WHERE col IN (SELECT ...) with additional WHERE in subquery
SELECT p.id, p.name, p.price
FROM products p
WHERE p.id IN (
    SELECT oi.product_id
    FROM order_items oi
    WHERE oi.quantity > 10
);
