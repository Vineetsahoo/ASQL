SELECT department, SUM(salary) as total_salary FROM employees GROUP BY department HAVING SUM(salary) > 500 AND YEAR(MAX(hire_date)) = 2023;
