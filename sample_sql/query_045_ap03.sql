-- Auto-generated ap03 query
SELECT e.name, d.name, d.location FROM employees e INNER JOIN departments d WHERE e.salary > 50000 AND d.budget > 5000;
