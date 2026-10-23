-- Auto-generated ap03 query
SELECT o.id, c.name, p.name FROM orders o JOIN customers c ON o.customer_id = c.id, products p WHERE o.total_amount > 5000;
