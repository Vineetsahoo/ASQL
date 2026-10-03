SELECT e.name, d.name, d.location FROM employees e INNER JOIN departments d WHERE e.salary > 75000 AND d.budget > 50;
