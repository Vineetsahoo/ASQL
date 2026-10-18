-- Query 077: Demonstrating AP-06 UNION without ALL with ordering
SELECT product_id, product_name, price FROM electronics WHERE in_stock = 1
UNION
SELECT product_id, product_name, price FROM appliances WHERE in_stock = 1;
