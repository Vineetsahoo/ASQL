-- Auto-generated ap05 query
SELECT name FROM employees WHERE department IN (SELECT name FROM departments WHERE budget > 5000);
