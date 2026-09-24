-- AP-05 Positive: Nested IN subquery
SELECT e.id, e.name
FROM employees e
WHERE e.department IN (
    SELECT d.name FROM departments d WHERE d.budget > 100000
);
