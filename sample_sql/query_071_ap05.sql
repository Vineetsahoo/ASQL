-- Auto-generated ap05 query
SELECT p.name, p.price FROM products p WHERE p.category = 'Electronics' AND p.id IN (SELECT product_id FROM order_items oi JOIN orders o ON oi.order_id = o.id WHERE o.status = 'cancelled');
