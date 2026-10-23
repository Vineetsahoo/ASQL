-- Auto-generated ap01 query
SELECT o.*, c.name FROM orders o JOIN customers c ON o.customer_id = c.id WHERE o.total_amount > 500;
