-- Auto-generated valid query
SELECT d.name, d.budget FROM departments d WHERE EXISTS (SELECT 1 FROM employees e WHERE e.department = d.id GROUP BY e.department HAVING AVG(e.salary) > 75000);
