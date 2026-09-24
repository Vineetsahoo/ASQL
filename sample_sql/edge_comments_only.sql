-- This comment contains SELECT * FROM orders
-- And WHERE UPPER(name) = 'FOO'
-- And WHERE id IN (SELECT id FROM other)
-- None of these comments should trigger any anti-pattern rule!
SELECT id, name FROM customers WHERE id = 42;
