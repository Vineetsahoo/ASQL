-- Query 076: Demonstrating AP-06 UNION without ALL
SELECT employee_id, first_name, last_name FROM sales_team WHERE region = 'EMEA'
UNION
SELECT employee_id, first_name, last_name FROM support_team WHERE region = 'EMEA';
