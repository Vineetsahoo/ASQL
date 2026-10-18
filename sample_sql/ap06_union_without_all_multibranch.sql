-- Anti-Pattern AP-06: Multi-branch UNION without ALL
SELECT order_id, amount, status FROM domestic_orders WHERE amount > 500
UNION
SELECT order_id, amount, status FROM international_orders WHERE amount > 500
UNION
SELECT order_id, amount, status FROM wholesale_orders WHERE amount > 500;
