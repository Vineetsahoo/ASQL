-- Auto-generated ap01 query
SELECT * FROM employees WHERE department = 'Marketing' UNION ALL SELECT * FROM employees WHERE salary > 50000 AND id IN (SELECT id FROM departments);
