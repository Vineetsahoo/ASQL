-- Auto-generated ap05 query
SELECT c.name, c.email FROM customers c WHERE c.id IN (SELECT o.customer_id FROM orders o WHERE o.id IN (SELECT oi.order_id FROM order_items oi WHERE oi.product_id IN (SELECT p.id FROM products p WHERE p.category = 'Books')));
