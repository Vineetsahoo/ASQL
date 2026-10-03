-- Auto-generated ap01 query
SELECT * FROM employees WHERE department = 'Engineering' UNION ALL SELECT * FROM employees WHERE salary > 75000 AND id IN (SELECT id FROM departments);
