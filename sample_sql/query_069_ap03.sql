WITH Matrix AS (SELECT c.id as cid, p.id as pid FROM customers c CROSS JOIN products p) SELECT m.*, o.total_amount FROM Matrix m LEFT JOIN orders o ON o.customer_id = m.cid AND o.total_amount > 5000;
