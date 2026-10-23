-- Auto-generated ap02 query
SELECT c.id, c.name FROM customers c JOIN orders o ON c.id = o.customer_id WHERE UPPER(TRIM(SUBSTR(c.name, 1, 5))) = 'BOB' AND o.status = 'pending';
