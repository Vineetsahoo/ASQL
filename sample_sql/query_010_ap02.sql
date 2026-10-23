-- Auto-generated ap02 query
WITH DeptStats AS (SELECT department, count(*) as emp_count FROM employees GROUP BY department) SELECT e.name, d.emp_count FROM employees e JOIN DeptStats d ON e.department = d.department WHERE COALESCE(e.salary, 0) < 5000 OR UPPER(e.name) LIKE '%BOB%';
