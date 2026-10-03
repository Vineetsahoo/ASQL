WITH TargetCustomers AS (SELECT id, name FROM customers WHERE city = 'Seattle') SELECT tc.name FROM TargetCustomers tc WHERE tc.id IN (SELECT customer_id FROM orders WHERE total_amount > 500);
