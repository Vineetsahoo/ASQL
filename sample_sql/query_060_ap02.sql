-- Auto-generated ap02 query
SELECT o.id, c.name FROM orders o JOIN customers c ON COALESCE(o.customer_id, 0) = c.id WHERE o.total_amount > 1000;
