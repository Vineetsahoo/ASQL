-- Auto-generated ap01 query
WITH HighValueOrders AS (SELECT o.id, o.customer_id, o.total_amount FROM orders o WHERE o.total_amount > 1000) SELECT * FROM HighValueOrders hvo LEFT JOIN customers c ON hvo.customer_id = c.id WHERE c.city = 'Boston';
