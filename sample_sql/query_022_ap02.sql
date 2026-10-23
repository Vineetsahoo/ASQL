-- Auto-generated ap02 query
SELECT department, SUM(salary) as total_salary FROM employees GROUP BY department HAVING SUM(salary) > 1000 AND YEAR(MAX(hire_date)) = 2022;
