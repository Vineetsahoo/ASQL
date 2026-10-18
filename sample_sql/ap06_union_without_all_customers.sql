-- Anti-Pattern AP-06: Cross-table UNION without ALL
SELECT customer_id, email, city FROM active_customers WHERE city = 'New York'
UNION
SELECT customer_id, email, city FROM prospective_leads WHERE city = 'New York';
