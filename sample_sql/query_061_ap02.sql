-- Auto-generated ap02 query
SELECT o.id, c.name FROM orders o INNER JOIN customers c ON UPPER(o.status) = UPPER(c.city) WHERE o.total_amount > 100;
