-- Auto-generated valid query
SELECT c.name, o.total_amount FROM customers c JOIN orders o ON c.id = o.customer_id WHERE c.city = 'Seattle';
