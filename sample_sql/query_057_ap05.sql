-- Auto-generated ap05 query
SELECT id, name FROM customers WHERE id IN (SELECT customer_id FROM orders WHERE status = 'delivered');
