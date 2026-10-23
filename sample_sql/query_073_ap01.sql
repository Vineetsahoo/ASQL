-- Auto-generated ap01 query
SELECT * FROM employees WHERE department = 'Sales' UNION ALL SELECT * FROM employees WHERE salary > 100000 AND id IN (SELECT id FROM departments);
